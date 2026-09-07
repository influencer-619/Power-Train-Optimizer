"""Simulation / optimization / sensitivity run orchestration."""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from datetime import datetime
from typing import Any

import numpy as np

from backend.compliance.engine import evaluate_compliance
from backend.database.session import SessionLocal
from backend.financial.engine import evaluate_financial, incremental_vs_discom
from backend.models import db_models as m
from backend.optimization.engine import run_optimization
from backend.paths import data_dir
from backend.services.project_service import get_project
from backend.simulation.engine import cfe_heatmap, run_simulation, series_window
from config.defaults import MODEL_VERSION, has_default_assumptions, v

_OPT_LOCK = threading.Lock()
_OPT_STATE: dict[int, dict[str, Any]] = {}
_LAST_DISPATCH: dict[int, Any] = {}  # simulation_run_id -> DispatchResult (memory cache)


def _save_hourly(run_id: int, bundle) -> str:
    path = data_dir() / "runs" / f"sim_{run_id}.npz"
    d = bundle.dispatch
    np.savez_compressed(
        path,
        load_mw=d.load_mw,
        solar_mw=d.solar_mw,
        wind_mw=d.wind_mw,
        charge_mw=d.charge_mw,
        discharge_mw=d.discharge_mw,
        grid_mw=d.grid_mw,
        curtailment_mw=d.curtailment_mw,
        unserved_mw=d.unserved_mw,
        soc_mwh=d.soc_mwh,
        re_origin_soc_mwh=d.re_origin_soc_mwh,
        grid_origin_soc_mwh=d.grid_origin_soc_mwh,
        direct_re_mw=d.direct_re_mw,
        re_from_bess_mw=d.re_from_bess_mw,
        re_serving_load_mw=d.re_serving_load_mw,
        hourly_cfe_pct=d.hourly_cfe_pct,
        charge_from_re_mw=d.charge_from_re_mw,
        charge_from_grid_mw=d.charge_from_grid_mw,
        balance_error_mw=d.balance_error_mw,
        solar_to_load_mw=getattr(d, "solar_to_load_mw", np.zeros(0)),
        wind_to_load_mw=getattr(d, "wind_to_load_mw", np.zeros(0)),
        solar_to_bess_mw=getattr(d, "solar_to_bess_mw", np.zeros(0)),
        wind_to_bess_mw=getattr(d, "wind_to_bess_mw", np.zeros(0)),
        solar_curtailment_mw=getattr(d, "solar_curtailment_mw", np.zeros(0)),
        wind_curtailment_mw=getattr(d, "wind_curtailment_mw", np.zeros(0)),
        solar_from_bess_mw=getattr(d, "solar_from_bess_mw", np.zeros(0)),
        wind_from_bess_mw=getattr(d, "wind_from_bess_mw", np.zeros(0)),
        grid_from_bess_mw=getattr(d, "grid_from_bess_mw", np.zeros(0)),
        tariff=d.meta["tariff_inr_per_kwh"],
        config_hash=np.array([bundle.config_hash or ""]),
    )
    return str(path)


def run_project_simulation(project_id: int, structure: str | None = None, scenario_id: int | None = None) -> dict:
    project = get_project(project_id)
    config = deepcopy(project["config"])
    if structure:
        config["commercial"]["structure"]["value"] = structure

    # DISCOM baseline for incremental metrics
    discom = run_simulation(config, structure="DISCOM", project_id=project_id)
    discom_comp = evaluate_compliance(discom.config, discom.kpis)
    discom_fin = evaluate_financial(discom.config, discom.kpis, discom_comp, discom.dispatch)

    bundle = run_simulation(config, structure=structure, project_id=project_id)
    compliance = evaluate_compliance(bundle.config, bundle.kpis)
    financial = evaluate_financial(bundle.config, bundle.kpis, compliance, bundle.dispatch)
    financial["incremental"] = incremental_vs_discom(financial, discom_fin)
    financial["discom_baseline"] = {
        "label": "GRID-ONLY BASELINE (DISCOM)",
        "cost_per_kwh": discom_fin["cost_per_kwh"],
        "total_annual_cost_inr": discom_fin["total_annual_cost_inr"],
        "annual_re_pct": discom.kpis["annual_re_pct"],
        "hourly_cfe_min_pct": discom.kpis["hourly_cfe_min_pct"],
        "reason": "Grid-only comparator — solar/wind/BESS forced to 0 MW.",
    }
    disc = float(v(config, "financial.discount_rate_pct")) / 100.0
    cfs = financial["incremental"]["cashflows_inr"]
    financial["incremental"]["npv_inr"] = float(sum(cf / ((1 + disc) ** t) for t, cf in enumerate(cfs)))
    if bundle.commercial_structure != "DISCOM":
        financial["npv_inr"] = financial["incremental"]["npv_inr"]
        financial["npv_cr"] = financial["npv_inr"] / 1e7
        financial["irr_pct"] = financial["incremental"]["irr_pct"]
        financial["payback_years"] = financial["incremental"]["payback_years"]
        financial["economics_basis"] = "incremental_vs_discom"
    else:
        financial["economics_basis"] = "standalone_cost_stack"

    from backend.compliance.feasibility import evaluate_feasibility
    from config.defaults import count_default_assumptions, critical_default_assumptions

    feasibility = evaluate_feasibility(bundle.config, bundle.kpis, compliance, bundle.validation)
    data_quality = {
        "load": bundle.profiles.get("load_source", "SYNTHETIC"),
        "solar": bundle.profiles.get("solar_source", "SYNTHETIC"),
        "wind": bundle.profiles.get("wind_source", "SYNTHETIC"),
        "tariff": "USER_INPUT" if not has_default_assumptions(project["config"]) else "DEFAULT / MIXED",
        "overall": (
            "PROJECT DATA ANALYSIS"
            if all(
                bundle.profiles.get(k) == "PROJECT DATA"
                for k in ("load_source", "solar_source", "wind_source")
            )
            else "PRELIMINARY"
        ),
        "default_assumptions_remaining": count_default_assumptions(project["config"]),
        "critical_defaults": critical_default_assumptions(project["config"]),
    }

    session = SessionLocal()
    try:
        run = m.SimulationRun(
            project_id=project_id,
            scenario_id=scenario_id,
            model_version=MODEL_VERSION,
            input_version=project["input_version"],
            structure=bundle.commercial_structure,
            status="completed",
            kpis_json=json.dumps(bundle.kpis),
            monthly_json=json.dumps(bundle.monthly),
            compliance_json=json.dumps(compliance),
            financial_json=json.dumps(financial),
            validation_json=json.dumps({**bundle.validation, "feasibility": feasibility, "data_quality": data_quality}),
        )
        session.add(run)
        session.flush()
        hourly_path = _save_hourly(run.id, bundle)
        run.hourly_path = hourly_path
        if bundle.energy_ledger is not None:
            ledger_path = data_dir() / "runs" / f"sim_{run.id}_ledger.json"
            ledger_path.write_text(json.dumps(bundle.energy_ledger), encoding="utf-8")
        session.add(m.HourlyResult(simulation_run_id=run.id, file_path=hourly_path, hours=int(bundle.validation["hours"])))
        session.add(m.FinancialResult(simulation_run_id=run.id, payload_json=json.dumps(financial)))
        session.add(m.ComplianceResult(simulation_run_id=run.id, payload_json=json.dumps(compliance)))
        session.commit()
        run_id = run.id
    finally:
        session.close()

    _LAST_DISPATCH[run_id] = bundle.dispatch
    can_rec = bool(feasibility.get("can_recommend"))
    recommendation = {
        "architecture": bundle.commercial_structure,
        "solar_mw": bundle.kpis["solar_mw"],
        "wind_mw": bundle.kpis["wind_mw"],
        "bess_mw": bundle.kpis["bess_mw"],
        "bess_mwh": bundle.kpis["bess_mwh"],
        "grid_mw": bundle.kpis["grid_mw"],
        "annual_re_pct": bundle.kpis["annual_re_pct"],
        "hourly_cfe_pct": bundle.kpis["hourly_cfe_min_pct"],
        "cost_per_kwh": financial["cost_per_kwh"],
        "label": "RECOMMENDED" if can_rec else feasibility.get("status", "NOT FEASIBLE"),
        "feasible": can_rec,
        "why": (
            "Configuration passes enabled technical constraints."
            if can_rec
            else (
                feasibility.get("primary_issue")
                or "Configuration does not meet RE/CFE/unserved targets — not labelled Recommended."
            )
        ),
    }
    return {
        "id": run_id,
        "project_id": project_id,
        "model_version": MODEL_VERSION,
        "structure": bundle.commercial_structure,
        "kpis": bundle.kpis,
        "monthly": bundle.monthly,
        "compliance": compliance,
        "financial": financial,
        "validation": bundle.validation,
        "feasibility": feasibility,
        "data_quality": data_quality,
        "cfe_analytics": bundle.kpis.get("cfe_analytics"),
        "heatmap_cfe": cfe_heatmap(bundle.dispatch),
        "has_default_assumptions": has_default_assumptions(project["config"]),
        "recommendation": recommendation,
        "created_at": datetime.utcnow().isoformat(),
        "energy_ledger": bundle.energy_ledger,
        "config_hash": bundle.config_hash,
        "input_version": project["input_version"],
        "profile_sources": bundle.profiles,
        "results_stale": False,
    }


def get_simulation(run_id: int) -> dict:
    session = SessionLocal()
    try:
        run = session.get(m.SimulationRun, run_id)
        if not run:
            raise KeyError("Simulation run not found")
        validation = json.loads(run.validation_json)
        kpis = json.loads(run.kpis_json)
        out = {
            "id": run.id,
            "project_id": run.project_id,
            "model_version": run.model_version,
            "structure": run.structure,
            "kpis": kpis,
            "monthly": json.loads(run.monthly_json),
            "compliance": json.loads(run.compliance_json),
            "financial": json.loads(run.financial_json),
            "validation": validation,
            "feasibility": validation.get("feasibility"),
            "data_quality": validation.get("data_quality"),
            "cfe_analytics": kpis.get("cfe_analytics"),
            "hourly_path": run.hourly_path,
            "created_at": run.created_at.isoformat(),
            "input_version": run.input_version,
            "config_hash": kpis.get("config_hash"),
        }
        ledger_path = data_dir() / "runs" / f"sim_{run_id}_ledger.json"
        if ledger_path.exists():
            out["energy_ledger"] = json.loads(ledger_path.read_text(encoding="utf-8"))
        # Stale if project inputs changed after this run
        try:
            project = get_project(run.project_id)
            out["results_stale"] = int(run.input_version or 0) != int(project.get("input_version") or 0)
            out["current_input_version"] = project.get("input_version")
            if out["results_stale"]:
                out["stale_message"] = (
                    "Results are STALE — project inputs changed after this run. Re-run 8760 simulation."
                )
            # Rebuild recommendation label from stored feasibility when present
            feas = out.get("feasibility") or {}
            can_rec = bool(feas.get("can_recommend"))
            out["recommendation"] = {
                "architecture": run.structure,
                "solar_mw": kpis.get("solar_mw"),
                "wind_mw": kpis.get("wind_mw"),
                "bess_mw": kpis.get("bess_mw"),
                "bess_mwh": kpis.get("bess_mwh"),
                "grid_mw": kpis.get("grid_mw"),
                "annual_re_pct": kpis.get("annual_re_pct"),
                "hourly_cfe_pct": kpis.get("hourly_cfe_min_pct"),
                "cost_per_kwh": out["financial"].get("cost_per_kwh"),
                "label": "RECOMMENDED" if can_rec else feas.get("status", "NOT FEASIBLE"),
                "feasible": can_rec,
                "why": feas.get("primary_issue")
                or ("Passes enabled technical constraints." if can_rec else "Not labelled Recommended."),
            }
        except Exception:  # noqa: BLE001
            out["results_stale"] = False
        return out
    finally:
        session.close()


def get_energy_ledger(run_id: int) -> dict:
    sim = get_simulation(run_id)
    if "energy_ledger" in sim:
        return sim["energy_ledger"]
    if run_id in _LAST_DISPATCH:
        from backend.simulation.energy_ledger import build_energy_ledger

        return build_energy_ledger(_LAST_DISPATCH[run_id])
    raise FileNotFoundError("Energy ledger not available for this run — re-run simulation.")


def list_profiles(project_id: int) -> dict:
    from backend.simulation.profiles_project import list_project_profiles

    get_project(project_id)  # ensure exists
    return list_project_profiles(project_id)


def upload_profile(project_id: int, kind: str, csv_text: str, value_column: str | None = None) -> dict:
    from backend.simulation.profiles_project import parse_csv_hourly, save_project_profile
    from config.defaults import get_default_config, set_param

    get_project(project_id)
    values, stamps = parse_csv_hourly(csv_text, value_column=value_column)
    result = save_project_profile(project_id, kind, values, timestamps=stamps)
    if not result.get("ok"):
        return result
    project = get_project(project_id)
    cfg = deepcopy(project["config"])
    defaults = get_default_config()
    if kind not in cfg:
        cfg[kind] = deepcopy(defaults.get(kind, {}))
    if "profile_source" not in cfg[kind]:
        cfg[kind]["profile_source"] = deepcopy(defaults[kind]["profile_source"])
    set_param(cfg, f"{kind}.profile_source", "PROJECT DATA", as_user=True)
    from backend.services.project_service import update_inputs

    update_inputs(project_id, cfg)
    result["profile_source_set"] = "PROJECT DATA"
    return result


def clear_profile(project_id: int, kind: str) -> dict:
    from backend.simulation.profiles_project import clear_project_profile
    from config.defaults import get_default_config, set_param

    get_project(project_id)
    removed = clear_project_profile(project_id, kind)
    project = get_project(project_id)
    cfg = deepcopy(project["config"])
    defaults = get_default_config()
    if kind in cfg and "profile_source" not in cfg[kind] and kind in defaults:
        cfg[kind]["profile_source"] = deepcopy(defaults[kind]["profile_source"])
    if kind in cfg and "profile_source" in cfg[kind]:
        set_param(cfg, f"{kind}.profile_source", "SYNTHETIC", as_user=True)
        from backend.services.project_service import update_inputs

        update_inputs(project_id, cfg)
    return {"ok": True, "removed": removed, "profile_source_set": "SYNTHETIC"}


def run_marginal_analysis(project_id: int) -> dict:
    """Small capacity steps around current sizing for explainability."""
    from backend.optimization.engine import evaluate_candidate
    from backend.optimization.explain import marginal_capacity_analysis

    project = get_project(project_id)
    cfg = project["config"]
    structure = str(v(cfg, "commercial.structure"))
    base_cand = {
        "solar_mw": float(v(cfg, "solar.capacity_mw")),
        "wind_mw": float(v(cfg, "wind.capacity_mw")),
        "bess_mw": float(v(cfg, "bess.power_mw")),
        "bess_mwh": float(v(cfg, "bess.energy_mwh")),
        "grid_mw": float(v(cfg, "grid.max_import_mw")),
    }
    discom = run_simulation(cfg, structure="DISCOM", project_id=project_id, skip_validation=True)
    discom_comp = evaluate_compliance(discom.config, discom.kpis)
    discom_fin = evaluate_financial(discom.config, discom.kpis, discom_comp, discom.dispatch)
    base = evaluate_candidate(cfg, base_cand, structure, discom_fin, project_id=project_id)
    variants = []
    steps = [
        ("+50 MW solar", {**base_cand, "solar_mw": base_cand["solar_mw"] + 50}),
        ("+50 MW wind", {**base_cand, "wind_mw": base_cand["wind_mw"] + 50}),
        ("+100 MWh BESS", {**base_cand, "bess_mwh": base_cand["bess_mwh"] + 100}),
        ("+25 MW BESS power", {**base_cand, "bess_mw": base_cand["bess_mw"] + 25}),
    ]
    for label, cand in steps:
        row = evaluate_candidate(cfg, cand, structure, discom_fin, project_id=project_id)
        row["label"] = label
        variants.append(row)
    return marginal_capacity_analysis(base, variants)

def get_series(run_id: int, view: str = "year", month: int = 1, day: int = 1) -> dict:
    if run_id in _LAST_DISPATCH:
        return series_window(_LAST_DISPATCH[run_id], view=view, month=month, day=day)
    sim = get_simulation(run_id)
    path = sim["hourly_path"]
    if not path:
        raise FileNotFoundError("Hourly results not stored for this run")
    data = np.load(path)
    # Rebuild a minimal dispatch-like object
    from backend.simulation.dispatch import DispatchResult

    d = DispatchResult(
        load_mw=data["load_mw"],
        solar_mw=data["solar_mw"],
        wind_mw=data["wind_mw"],
        charge_mw=data["charge_mw"],
        discharge_mw=data["discharge_mw"],
        grid_mw=data["grid_mw"],
        curtailment_mw=data["curtailment_mw"],
        unserved_mw=data["unserved_mw"],
        soc_mwh=data["soc_mwh"],
        re_origin_soc_mwh=np.zeros_like(data["soc_mwh"]),
        grid_origin_soc_mwh=np.zeros_like(data["soc_mwh"]),
        direct_re_mw=np.zeros_like(data["load_mw"]),
        re_from_bess_mw=np.zeros_like(data["load_mw"]),
        re_serving_load_mw=data["re_serving_load_mw"],
        hourly_cfe_pct=data["hourly_cfe_pct"],
        charge_from_re_mw=data["charge_from_re_mw"],
        charge_from_grid_mw=data["charge_from_grid_mw"],
        balance_error_mw=np.zeros_like(data["load_mw"]),
        meta={},
    )
    return series_window(d, view=view, month=month, day=day)


def start_optimization(project_id: int) -> int:
    project = get_project(project_id)
    session = SessionLocal()
    try:
        run = m.OptimizationRun(
            project_id=project_id,
            model_version=MODEL_VERSION,
            status="running",
            progress_json=json.dumps({"status": "running", "iteration": 0}),
            result_json="{}",
        )
        session.add(run)
        session.commit()
        run_id = run.id
    finally:
        session.close()

    cancel_flag = {"cancel": False}
    with _OPT_LOCK:
        _OPT_STATE[run_id] = {"cancel": cancel_flag, "progress": {"status": "running"}}

    def worker():
        def progress_cb(p):
            with _OPT_LOCK:
                _OPT_STATE[run_id]["progress"] = p
            s = SessionLocal()
            try:
                row = s.get(m.OptimizationRun, run_id)
                if row:
                    row.progress_json = json.dumps(p)
                    s.commit()
            finally:
                s.close()

        def cancel_cb():
            return bool(cancel_flag["cancel"])

        try:
            result = run_optimization(
                project["config"],
                progress_cb=progress_cb,
                cancel_cb=cancel_cb,
                project_id=project_id,
            )
            status = result.get("status", "completed")
        except Exception as exc:  # noqa: BLE001
            result = {"status": "error", "error": str(exc)}
            status = "error"
        s = SessionLocal()
        try:
            row = s.get(m.OptimizationRun, run_id)
            if row:
                row.status = status
                row.result_json = json.dumps(result)
                row.progress_json = json.dumps(result if status != "running" else {"status": status})
                row.finished_at = datetime.utcnow()
                s.add(m.OptimizationResult(optimization_run_id=run_id, payload_json=json.dumps(result)))
                s.commit()
        finally:
            s.close()

    threading.Thread(target=worker, daemon=True).start()
    return run_id


def get_optimization(run_id: int) -> dict:
    session = SessionLocal()
    try:
        run = session.get(m.OptimizationRun, run_id)
        if not run:
            raise KeyError("Optimization run not found")
        progress = json.loads(run.progress_json or "{}")
        result = json.loads(run.result_json or "{}")
        return {
            "id": run.id,
            "project_id": run.project_id,
            "status": run.status,
            "progress": progress,
            "result": result,
            "model_version": run.model_version,
            "created_at": run.created_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        }
    finally:
        session.close()


def cancel_optimization(run_id: int) -> None:
    with _OPT_LOCK:
        if run_id in _OPT_STATE:
            _OPT_STATE[run_id]["cancel"]["cancel"] = True


def run_sensitivity(project_id: int, parameters: list[str] | None = None) -> dict:
    project = get_project(project_id)
    base = run_project_simulation(project_id)
    base_cost = float(base["financial"]["cost_per_kwh"])
    params = parameters or [
        "financial.discount_rate_pct",
        "solar.capacity_mw",
        "bess.energy_mwh",
        "wind.capacity_mw",
        "load.load_factor_pct",
        "grid.tod_peak_tariff",
        "grid.energy_tariff_inr_per_kwh",
        "bess.capex_inr_per_mwh",
        "solar.energy_cost_inr_per_kwh",
        "wind.energy_cost_inr_per_kwh",
        "financial.electricity_escalation_pct",
    ]
    tornado = []
    from copy import deepcopy as dc

    from backend.compliance.engine import evaluate_compliance as ec
    from backend.financial.engine import evaluate_financial as ef
    from backend.simulation.engine import run_simulation as sim_once
    from config.defaults import set_param

    for path in params:
        row = {"parameter": path, "low": None, "high": None, "base": base_cost}
        for label, factor in (("low", 0.8), ("high", 1.2)):
            cfg = dc(project["config"])
            # navigate
            node = cfg
            parts = path.split(".")
            cur = node
            for p in parts[:-1]:
                cur = cur[p]
            old = cur[parts[-1]]["value"]
            if isinstance(old, bool):
                continue
            set_param(cfg, path, float(old) * factor, as_user=True)
            try:
                b = sim_once(cfg)
                c = ec(b.config, b.kpis)
                f = ef(b.config, b.kpis, c, b.dispatch)
                row[label] = float(f["cost_per_kwh"])
            except Exception:  # noqa: BLE001
                row[label] = base_cost
        if row["low"] is not None and row["high"] is not None:
            row["swing"] = abs(row["high"] - row["low"])
            tornado.append(row)
    tornado.sort(key=lambda r: r.get("swing", 0), reverse=True)

    # Two-variable matrix: solar capacity vs BESS duration proxy (energy)
    matrix = {"x": "solar.capacity_mw", "y": "bess.energy_mwh", "values": []}
    xs = [0.8, 1.0, 1.2]
    ys = [0.8, 1.0, 1.2]
    base_s = float(project["config"]["solar"]["capacity_mw"]["value"])
    base_e = float(project["config"]["bess"]["energy_mwh"]["value"])
    for fy in ys:
        rowv = []
        for fx in xs:
            cfg = dc(project["config"])
            set_param(cfg, "solar.capacity_mw", base_s * fx)
            set_param(cfg, "bess.energy_mwh", base_e * fy)
            try:
                b = sim_once(cfg)
                c = ec(b.config, b.kpis)
                f = ef(b.config, b.kpis, c, b.dispatch)
                rowv.append(float(f["cost_per_kwh"]))
            except Exception:  # noqa: BLE001
                rowv.append(None)
        matrix["values"].append(rowv)
    matrix["x_factors"] = xs
    matrix["y_factors"] = ys

    return {"base_cost_per_kwh": base_cost, "tornado": tornado, "matrix": matrix, "base_run_id": base["id"]}


def compare_architectures(project_id: int) -> dict:
    rows = {}
    for structure in ("DISCOM", "CAPTIVE", "HYBRID", "OPEN_ACCESS"):
        rows[structure] = run_project_simulation(project_id, structure=structure)
    best = None
    best_cost = None
    for structure, res in rows.items():
        feas = res.get("feasibility") or {}
        can = bool(feas.get("can_recommend"))
        # DISCOM is a baseline comparator — never auto-recommended when RE/CFE targets exist
        if structure == "DISCOM":
            can = False
        cost = float(res["financial"]["cost_per_kwh"])
        if can and (best_cost is None or cost < best_cost):
            best_cost = cost
            best = structure
    recommended = best
    if best is None:
        # Lowest cost among technically feasible (or all) — labelled separately
        best = min(rows.keys(), key=lambda k: float(rows[k]["financial"]["cost_per_kwh"]))
    return {
        "architectures": rows,
        "best": best,
        "recommended": recommended,
        "recommended_label": (
            f"RECOMMENDED: {recommended}" if recommended else "NO FEASIBLE RECOMMENDATION"
        ),
    }
