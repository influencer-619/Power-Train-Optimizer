"""End-to-end 8,760-hour simulation orchestration."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

import numpy as np

from backend.simulation.calendar import MONTH_NAMES, get_calendar, month_slices
from backend.simulation.dispatch import DispatchResult, run_dispatch
from backend.simulation.energy_ledger import build_energy_ledger
from backend.simulation.fingerprint import config_fingerprint
from backend.simulation.profiles import generate_load, generate_solar, generate_wind
from backend.simulation.validation import validate_config, validate_dispatch
from config.defaults import merge_missing_defaults, recompute_calculated, v


@dataclass
class SimulationBundle:
    config: dict
    kpis: dict
    monthly: list[dict]
    dispatch: DispatchResult
    profiles: dict
    validation: dict
    commercial_structure: str
    energy_ledger: dict | None = None
    config_hash: str | None = None


def _flag(config: dict, dotted: str, default: bool = True) -> bool:
    try:
        return bool(v(config, dotted))
    except Exception:
        return default


def apply_architecture_asset_flags(config: dict) -> dict:
    """Zero excluded assets, then scale included assets by architecture mix %."""
    structure = str(v(config, "commercial.structure"))
    if structure == "DISCOM":
        config["commercial"]["include_discom"]["value"] = True
        config["commercial"]["include_solar"]["value"] = False
        config["commercial"]["include_wind"]["value"] = False
        config["commercial"]["include_bess"]["value"] = False
    elif structure == "CAPTIVE":
        # Captive mix is Solar / Wind / BESS only (no DISCOM option)
        config["commercial"]["include_discom"]["value"] = False

    if structure == "DISCOM" or not _flag(config, "commercial.include_solar", True):
        config["solar"]["capacity_mw"]["value"] = 0.0
    if structure == "DISCOM" or not _flag(config, "commercial.include_wind", True):
        config["wind"]["capacity_mw"]["value"] = 0.0
    if structure == "DISCOM" or not _flag(config, "commercial.include_bess", True):
        config["bess"]["power_mw"]["value"] = 0.0
        config["bess"]["energy_mwh"]["value"] = 0.0
    if not _flag(config, "commercial.include_discom", True):
        config["grid"]["max_import_mw"]["value"] = 0.0

    # Mix %: how much of each included asset's configured capacity is used
    if structure != "DISCOM":
        if float(config["solar"]["capacity_mw"]["value"]) > 0:
            config["solar"]["capacity_mw"]["value"] = round(
                float(config["solar"]["capacity_mw"]["value"]) * _mix_scale(config, "mix_solar_pct"),
                6,
            )
        if float(config["wind"]["capacity_mw"]["value"]) > 0:
            config["wind"]["capacity_mw"]["value"] = round(
                float(config["wind"]["capacity_mw"]["value"]) * _mix_scale(config, "mix_wind_pct"),
                6,
            )
        if float(config["bess"]["power_mw"]["value"]) > 0 or float(config["bess"]["energy_mwh"]["value"]) > 0:
            scale_b = _mix_scale(config, "mix_bess_pct")
            config["bess"]["power_mw"]["value"] = round(float(config["bess"]["power_mw"]["value"]) * scale_b, 6)
            config["bess"]["energy_mwh"]["value"] = round(float(config["bess"]["energy_mwh"]["value"]) * scale_b, 6)
        if structure in ("HYBRID", "OPEN_ACCESS") and float(config["grid"]["max_import_mw"]["value"]) > 0:
            config["grid"]["max_import_mw"]["value"] = round(
                float(config["grid"]["max_import_mw"]["value"]) * _mix_scale(config, "mix_discom_pct"),
                6,
            )
    return config


def _mix_scale(config: dict, key: str) -> float:
    """Return 0–1 scale from commercial.mix_*_pct (default 100%)."""
    try:
        pct = float(v(config, f"commercial.{key}"))
    except Exception:
        pct = 100.0
    return max(0.0, min(100.0, pct)) / 100.0


def _apply_structure_capacities(config: dict, structure: str | None = None) -> dict:
    cfg = deepcopy(config)
    recompute_calculated(cfg)
    structure = structure or str(v(cfg, "commercial.structure"))
    cfg["commercial"]["structure"]["value"] = structure
    return apply_architecture_asset_flags(cfg)


def _capacity_overrides(config: dict, overrides: dict | None) -> dict:
    cfg = deepcopy(config)
    if not overrides:
        return cfg
    if "solar_mw" in overrides:
        cfg["solar"]["capacity_mw"]["value"] = float(overrides["solar_mw"])
    if "wind_mw" in overrides:
        cfg["wind"]["capacity_mw"]["value"] = float(overrides["wind_mw"])
    if "bess_mw" in overrides:
        cfg["bess"]["power_mw"]["value"] = float(overrides["bess_mw"])
    if "bess_mwh" in overrides:
        cfg["bess"]["energy_mwh"]["value"] = float(overrides["bess_mwh"])
    if "grid_mw" in overrides:
        cfg["grid"]["max_import_mw"]["value"] = float(overrides["grid_mw"])
    return cfg


def summarize_dispatch(config: dict, d: DispatchResult) -> dict[str, Any]:
    load = float(d.load_mw.sum())
    re_serve = float(d.re_serving_load_mw.sum())
    annual_re = (re_serve / load * 100.0) if load > 0 else 0.0
    target = float(v(config, "compliance.hourly_cfe_target_pct"))
    hours_meet = float(np.mean(d.hourly_cfe_pct >= target) * 100.0)
    mean_cfe = float(np.mean(d.hourly_cfe_pct))
    min_cfe = float(np.min(d.hourly_cfe_pct)) if len(d.hourly_cfe_pct) else 0.0

    re_charged = float(d.charge_from_re_mw.sum())
    grid_charged = float(d.charge_from_grid_mw.sum())
    total_charged = re_charged + grid_charged
    re_origin_share = (re_charged / total_charged * 100.0) if total_charged > 0 else 100.0

    throughput = float(d.discharge_mw.sum())
    bess_power = float(d.meta.get("bess_power_mw") or 0.0)
    bess_energy = float(d.meta.get("bess_energy_mwh") or 0.0)
    cycles = (throughput / bess_energy) if bess_energy > 0 else 0.0
    util = min(100.0, cycles / 365.0 * 100.0) if bess_energy > 0 else 0.0
    duration_h = (bess_energy / bess_power) if bess_power > 0 else 0.0

    # Ideal BESS: conversion losses are zero (η_c = η_d = 1)
    bess_losses = 0.0
    charge_total = float(d.charge_mw.sum())

    solar_from_bess = float(getattr(d, "solar_from_bess_mw", np.zeros(0)).sum()) if len(getattr(d, "solar_from_bess_mw", [])) else 0.0
    wind_from_bess = float(getattr(d, "wind_from_bess_mw", np.zeros(0)).sum()) if len(getattr(d, "wind_from_bess_mw", [])) else 0.0
    grid_from_bess = float(getattr(d, "grid_from_bess_mw", np.zeros(0)).sum()) if len(getattr(d, "grid_from_bess_mw", [])) else max(0.0, throughput - float(d.re_from_bess_mw.sum()))

    return {
        "solar_mw": float(v(config, "solar.capacity_mw")),
        "wind_mw": float(v(config, "wind.capacity_mw")),
        "bess_mw": bess_power,
        "bess_mwh": bess_energy,
        "bess_duration_h": duration_h,
        "grid_mw": float(d.meta.get("grid_cap_mw") or 0.0),
        "annual_load_mwh": load,
        "annual_solar_mwh": float(d.solar_mw.sum()),
        "annual_wind_mwh": float(d.wind_mw.sum()),
        "annual_re_generation_mwh": float(d.solar_mw.sum() + d.wind_mw.sum()),
        "direct_re_mwh": float(d.direct_re_mw.sum()),
        "re_from_bess_mwh": float(d.re_from_bess_mw.sum()),
        "re_serving_load_mwh": re_serve,
        "annual_re_pct": annual_re,
        "hourly_cfe_mean_pct": mean_cfe,
        "hourly_cfe_min_pct": min_cfe,
        "hourly_cfe_median_pct": float(np.median(d.hourly_cfe_pct)) if len(d.hourly_cfe_pct) else 0.0,
        "hourly_cfe_p95_pct": float(np.percentile(d.hourly_cfe_pct, 95)) if len(d.hourly_cfe_pct) else 0.0,
        "hourly_cfe_energy_weighted_pct": annual_re,
        "hours_meeting_cfe_target_pct": hours_meet,
        "hours_meeting_cfe_target": int(np.sum(d.hourly_cfe_pct >= target)),
        "hours_below_cfe_target": int(np.sum(d.hourly_cfe_pct < target)),
        "grid_mwh": float(d.grid_mw.sum()),
        "grid_gwh": float(d.grid_mw.sum()) / 1000.0,
        "curtailment_mwh": float(d.curtailment_mw.sum()),
        "curtailment_pct": float(
            d.curtailment_mw.sum() / max(d.solar_mw.sum() + d.wind_mw.sum(), 1e-9) * 100.0
        ),
        "bess_charge_mwh": charge_total,
        "bess_discharge_mwh": throughput,
        "bess_throughput_mwh": throughput,
        "bess_cycles": cycles,
        "bess_utilization_pct": util,
        "bess_utilization_definition": (
            "min(100, (Σ discharge_mwh / bess_energy_mwh) / 365 × 100) — equivalent full cycles/year vs 1 cycle/day"
        ),
        "bess_avg_soc_pct": float(np.mean(d.soc_mwh) / bess_energy * 100.0) if bess_energy > 0 else 0.0,
        "bess_min_soc_pct_observed": float(np.min(d.soc_mwh) / bess_energy * 100.0) if bess_energy > 0 and len(d.soc_mwh) else 0.0,
        "bess_max_soc_pct_observed": float(np.max(d.soc_mwh) / bess_energy * 100.0) if bess_energy > 0 and len(d.soc_mwh) else 0.0,
        "bess_losses_mwh": bess_losses,
        "bess_re_origin_discharge_mwh": float(d.re_from_bess_mw.sum()),
        "bess_solar_origin_discharge_mwh": solar_from_bess,
        "bess_wind_origin_discharge_mwh": wind_from_bess,
        "bess_grid_origin_discharge_mwh": grid_from_bess,
        "bess_renewable_charging_pct": re_origin_share,
        "bess_grid_charging_pct": (100.0 - re_origin_share) if total_charged > 0 else 0.0,
        "unserved_mwh": float(d.unserved_mw.sum()),
        "re_origin_stored_share_pct": re_origin_share,
        "re_charge_mwh": re_charged,
        "grid_charge_mwh": grid_charged,
        "max_grid_import_mw": float(d.grid_mw.max()) if len(d.grid_mw) else 0.0,
        "max_abs_balance_error_mw": float(d.meta.get("max_abs_balance_error_mw") or 0.0),
        "dispatch_mode": d.meta.get("dispatch_mode"),
    }


def monthly_balance(d: DispatchResult, config: dict) -> list[dict]:
    hours = len(d.load_mw)
    rows = []
    for i, (a, b) in enumerate(month_slices(hours)):
        load = float(d.load_mw[a:b].sum())
        re_serve = float(d.re_serving_load_mw[a:b].sum())
        cfe = float(np.mean(d.hourly_cfe_pct[a:b])) if b > a else 0.0
        rows.append(
            {
                "month": MONTH_NAMES[i],
                "month_index": i + 1,
                "load_mwh": load,
                "solar_mwh": float(d.solar_mw[a:b].sum()),
                "wind_mwh": float(d.wind_mw[a:b].sum()),
                "direct_re_mwh": float(d.direct_re_mw[a:b].sum()),
                "bess_charge_mwh": float(d.charge_mw[a:b].sum()),
                "bess_discharge_mwh": float(d.discharge_mw[a:b].sum()),
                "grid_mwh": float(d.grid_mw[a:b].sum()),
                "curtailment_mwh": float(d.curtailment_mw[a:b].sum()),
                "re_pct": (re_serve / load * 100.0) if load > 0 else 0.0,
                "cfe_mean_pct": cfe,
            }
        )
    return rows


def run_simulation(
    config: dict,
    structure: str | None = None,
    capacity_overrides: dict | None = None,
    skip_validation: bool = False,
    project_id: int | None = None,
) -> SimulationBundle:
    cfg = _apply_structure_capacities(config, structure)
    cfg = _capacity_overrides(cfg, capacity_overrides)
    cfg = merge_missing_defaults(cfg)
    recompute_calculated(cfg)

    if not skip_validation:
        issues = validate_config(cfg)
        hard = [i for i in issues if i["level"] == "error"]
        if hard:
            raise ValueError("; ".join(i["message"] for i in hard))

    hours = int(v(cfg, "general.model_hours"))
    cal = get_calendar(hours)

    load_src = "SYNTHETIC"
    solar_src = "SYNTHETIC"
    wind_src = "SYNTHETIC"
    try:
        load_src = str(v(cfg, "load.profile_source"))
    except Exception:
        pass
    try:
        solar_src = str(v(cfg, "solar.profile_source"))
    except Exception:
        pass
    try:
        wind_src = str(v(cfg, "wind.profile_source"))
    except Exception:
        pass

    load = generate_load(cfg, hours)
    solar = generate_solar(cfg, hours)
    wind = generate_wind(cfg, hours)

    # Optional project-data override (never silent — errors if selected but missing/invalid)
    if project_id is not None:
        from backend.simulation.profiles_project import load_project_profile, validate_hourly_series

        for kind, src, gen_key, arr_key in (
            ("load", load_src, load, "load_mw"),
            ("solar", solar_src, solar, "solar_mw"),
            ("wind", wind_src, wind, "wind_mw"),
        ):
            if src == "PROJECT DATA":
                stored = load_project_profile(project_id, kind)
                if stored is None:
                    raise ValueError(
                        f"MODEL ERROR: {kind} profile_source is PROJECT DATA but no profile is imported. "
                        f"Import 8,760 hourly values or switch to SYNTHETIC."
                    )
                report = validate_hourly_series(stored["values"], name=kind, timestamps=stored.get("timestamps"), expected_hours=hours)
                if not report["ok"]:
                    raise ValueError("MODEL ERROR: " + "; ".join(report["errors"]))
                gen_key[arr_key] = np.asarray(stored["values"], dtype=float)
                gen_key["annual_mwh"] = float(gen_key[arr_key].sum())
                if kind == "load":
                    peak = float(v(cfg, "load.peak_load_mw"))
                    gen_key["actual_load_factor_pct"] = float(gen_key[arr_key].mean() / peak * 100.0) if peak > 0 else 0.0
                if kind == "solar":
                    cap = float(v(cfg, "solar.capacity_mw"))
                    gen_key["actual_cf_pct"] = float(gen_key[arr_key].mean() / cap * 100.0) if cap > 0 else 0.0
                if kind == "wind":
                    cap = float(v(cfg, "wind.capacity_mw"))
                    gen_key["actual_cf_pct"] = float(gen_key[arr_key].mean() / cap * 100.0) if cap > 0 else 0.0

    d = run_dispatch(
        cfg,
        load["load_mw"],
        solar["solar_mw"],
        wind["wind_mw"],
        cal.hour_of_day,
        bess_power_mw=float(v(cfg, "bess.power_mw")),
        bess_energy_mwh=float(v(cfg, "bess.energy_mwh")),
        grid_cap_mw=float(v(cfg, "grid.max_import_mw")),
    )

    kpis = summarize_dispatch(cfg, d)
    kpis["actual_load_factor_pct"] = load["actual_load_factor_pct"]
    kpis["solar_cf_pct"] = solar["actual_cf_pct"]
    kpis["wind_cf_pct"] = wind["actual_cf_pct"]
    kpis["structure"] = str(v(cfg, "commercial.structure"))

    from backend.compliance.cfe_analytics import analyze_cfe

    cfe_analytics = analyze_cfe(cfg, d.hourly_cfe_pct, kpis["annual_re_pct"])
    kpis["annual_cfe_pct"] = cfe_analytics["annual_cfe_pct"]
    kpis["cfe_analytics"] = cfe_analytics

    ledger = build_energy_ledger(d)
    validation = validate_dispatch(d, cfg)
    cfg_hash = config_fingerprint(
        cfg,
        extra={
            "structure": str(v(cfg, "commercial.structure")),
            "capacity_overrides": capacity_overrides or {},
            "profile_source": {"load": load_src, "solar": solar_src, "wind": wind_src},
        },
    )
    kpis["config_hash"] = cfg_hash

    if validation.get("power_balance_ok") is False:
        hour = validation.get("first_balance_fail_hour")
        err = validation.get("model_error") or {}
        raise RuntimeError(
            err.get("message")
            or f"MODEL ERROR: Hourly power balance failed at hour {hour}."
        )
    if validation.get("energy_balance_ok") is False:
        raise RuntimeError("MODEL ERROR: ENERGY BALANCE")
    if validation.get("soc_ok") is False:
        raise RuntimeError("MODEL ERROR: BESS SOC outside limits.")
    if validation.get("finite_ok") is False:
        raise RuntimeError("MODEL ERROR: Non-finite values in dispatch arrays.")

    return SimulationBundle(
        config=cfg,
        kpis=kpis,
        monthly=monthly_balance(d, cfg),
        dispatch=d,
        profiles={
            "load_annual_mwh": load["annual_mwh"],
            "solar_annual_mwh": solar["annual_mwh"],
            "wind_annual_mwh": wind["annual_mwh"],
            "load_source": load_src,
            "solar_source": solar_src,
            "wind_source": wind_src,
        },
        validation=validation,
        commercial_structure=str(v(cfg, "commercial.structure")),
        energy_ledger=ledger,
        config_hash=cfg_hash,
    )


def series_window(d: DispatchResult, view: str = "year", month: int = 1, day: int = 1) -> dict:
    n = len(d.load_mw)
    cal = get_calendar(n)
    if view == "day":
        doy = max(1, min(365 if n == 8760 else 366, day)) - 1
        idx = np.where(cal.day_of_year == doy)[0]
    elif view == "week":
        doy = max(1, min(365 if n == 8760 else 366, day)) - 1
        start = int(np.where(cal.day_of_year == doy)[0][0])
        idx = np.arange(start, min(n, start + 24 * 7))
    elif view == "month":
        m = max(1, min(12, month)) - 1
        a, b = month_slices(n)[m]
        idx = np.arange(a, b)
    else:
        idx = np.arange(0, n, 6)

    def take(arr):
        return arr[idx].tolist()

    return {
        "view": view,
        "index": idx.tolist(),
        "hour_of_day": cal.hour_of_day[idx].tolist(),
        "load_mw": take(d.load_mw),
        "solar_mw": take(d.solar_mw),
        "wind_mw": take(d.wind_mw),
        "charge_mw": take(d.charge_mw),
        "discharge_mw": take(d.discharge_mw),
        "soc_mwh": take(d.soc_mwh),
        "grid_mw": take(d.grid_mw),
        "curtailment_mw": take(d.curtailment_mw),
        "hourly_cfe_pct": take(d.hourly_cfe_pct),
    }


def cfe_heatmap(d: DispatchResult) -> list[list[float]]:
    n = len(d.load_mw)
    cal = get_calendar(n)
    heat = np.zeros((12, 24))
    counts = np.zeros((12, 24))
    for t in range(n):
        m = int(cal.month[t])
        h = int(cal.hour_of_day[t])
        heat[m, h] += float(d.hourly_cfe_pct[t])
        counts[m, h] += 1
    counts = np.maximum(counts, 1.0)
    return (heat / counts).tolist()
