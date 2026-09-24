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
    """Apply include_* flags for the active structure (no plant MW zeroing — buyer path)."""
    structure = str(v(config, "commercial.structure"))
    if structure == "DISCOM":
        config["commercial"]["include_discom"]["value"] = True
        config["commercial"]["include_solar"]["value"] = False
        config["commercial"]["include_wind"]["value"] = False
        config["commercial"]["include_bess"]["value"] = False
    elif structure == "CAPTIVE":
        # CAPTIVE = Solar / Wind / BESS only (no DISCOM)
        config["commercial"]["include_discom"]["value"] = False

    return config


def _architecture_mix_pcts(config: dict) -> dict[str, float]:
    """Architecture Percentage of power from Project Setup (respect include_* flags)."""

    def _mix(key: str, included: bool) -> float:
        if not included:
            return 0.0
        try:
            return max(0.0, min(100.0, float(v(config, f"commercial.{key}"))))
        except Exception:
            return 0.0

    return {
        "discom": _mix("mix_discom_pct", _flag(config, "commercial.include_discom", False)),
        "solar": _mix("mix_solar_pct", _flag(config, "commercial.include_solar", True)),
        "wind": _mix("mix_wind_pct", _flag(config, "commercial.include_wind", True)),
        "bess": _mix("mix_bess_pct", _flag(config, "commercial.include_bess", True)),
    }


def _scale_shape_to_annual_mwh(shape_mw: np.ndarray | None, target_mwh: float, n: int) -> np.ndarray:
    """Preserve TOD/diurnal shape; scale so Σ MW = target annual MWh. Night stays ~0 if shape is."""
    out = np.zeros(n, dtype=float)
    if target_mwh <= 1e-12 or n <= 0:
        return out
    if shape_mw is None:
        return out
    shape = np.asarray(shape_mw, dtype=float)
    if len(shape) != n:
        m = min(n, len(shape))
        out[:m] = np.maximum(0.0, shape[:m])
        shape = out
    else:
        shape = np.maximum(0.0, shape)
    total = float(shape.sum())
    if total <= 1e-12:
        return np.zeros(n, dtype=float)
    return shape * (target_mwh / total)


def apply_setup_energy_contracts(
    config: dict,
    load_mw: np.ndarray,
    solar_mw: np.ndarray,
    wind_mw: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float, float, float]:
    """Apply Architecture mix % as annual energy contracts with TOD/availability shapes.

    Bill keeps Architecture mix %. Hourly delivery:
      • Solar / Wind shapes (synthetic or PROJECT DATA) scaled so
        annual MWh = Load_annual × mix%/100 — solar night stays ~0 from the shape.
      • BESS mix > 0 → derived storage (power/energy) so RE can shift to night hours.
      • DISCOM included → grid import cap ≈ peak (procurement backup); else 0.
    """
    mixes = _architecture_mix_pcts(config)
    load = np.asarray(load_mw, dtype=float)
    n = len(load)
    peak = float(np.max(load)) if n else 0.0
    load_annual = float(load.sum())

    solar_out = _scale_shape_to_annual_mwh(solar_mw, load_annual * (mixes["solar"] / 100.0), n)
    wind_out = _scale_shape_to_annual_mwh(wind_mw, load_annual * (mixes["wind"] / 100.0), n)

    # Derived BESS for hourly shifting (Storage tariff × BESS% still bills Architecture mix)
    bess_power = 0.0
    bess_energy = 0.0
    if mixes["bess"] > 0.0 and peak > 0.0:
        bess_power = peak * (mixes["bess"] / 100.0)
        annual_bess_mwh = load_annual * (mixes["bess"] / 100.0)
        # ~4 h duration at rated power, at least one equivalent daily cycle of contracted BESS energy
        bess_energy = max(bess_power * 4.0, annual_bess_mwh / max(n / 24.0, 1.0))

    if _flag(config, "commercial.include_discom", False):
        grid_cap = max(peak, peak * (mixes["discom"] / 100.0) if mixes["discom"] > 0 else peak)
    else:
        grid_cap = 0.0

    return solar_out, wind_out, bess_power, bess_energy, grid_cap


def _mix_scale(config: dict, key: str) -> float:
    """Return 0–1 scale from commercial.mix_*_pct (kept for callers)."""
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
    """Legacy optimizer hooks — plant MW overrides are ignored on the buyer path."""
    return deepcopy(config)


def summarize_dispatch(config: dict, d: DispatchResult) -> dict[str, Any]:
    load = float(d.load_mw.sum())
    re_serve = float(d.re_serving_load_mw.sum())
    # Hourly availability: energy-weighted Annual RE = Σ RE serving load / Σ load
    annual_re = (re_serve / load * 100.0) if load > 0 else 0.0
    mixes_early = _architecture_mix_pcts(config)
    contract_re_mix = float(mixes_early["solar"] + mixes_early["wind"] + mixes_early["bess"])
    target = float(v(config, "compliance.hourly_cfe_target_pct"))
    hours_meet = float(np.mean(d.hourly_cfe_pct >= target) * 100.0)
    mean_cfe = float(np.mean(d.hourly_cfe_pct))
    min_cfe = float(np.min(d.hourly_cfe_pct)) if len(d.hourly_cfe_pct) else 0.0
    ew_cfe = annual_re  # same numerator/denominator as Annual RE when CFE uses RE serving load

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

    eta_c = float(d.meta.get("eta_c") or 1.0)
    eta_d = float(d.meta.get("eta_d") or 1.0)
    charge_total = float(d.charge_mw.sum())
    # AC in → store: charge*(1−η_c); store → AC out: discharge*(1/η_d − 1)
    bess_losses = charge_total * (1.0 - eta_c) + (
        throughput * (1.0 / max(eta_d, 1e-9) - 1.0) if throughput > 0 else 0.0
    )

    solar_from_bess = float(getattr(d, "solar_from_bess_mw", np.zeros(0)).sum()) if len(getattr(d, "solar_from_bess_mw", [])) else 0.0
    wind_from_bess = float(getattr(d, "wind_from_bess_mw", np.zeros(0)).sum()) if len(getattr(d, "wind_from_bess_mw", [])) else 0.0
    grid_from_bess = float(getattr(d, "grid_from_bess_mw", np.zeros(0)).sum()) if len(getattr(d, "grid_from_bess_mw", [])) else max(0.0, throughput - float(d.re_from_bess_mw.sum()))

    solar_to_load = float(getattr(d, "solar_to_load_mw", np.zeros(0)).sum()) if len(getattr(d, "solar_to_load_mw", [])) else 0.0
    wind_to_load = float(getattr(d, "wind_to_load_mw", np.zeros(0)).sum()) if len(getattr(d, "wind_to_load_mw", [])) else 0.0
    grid_to_load = max(0.0, float(d.grid_mw.sum()) - grid_charged)
    # Dispatch diagnostics (not used for bill blend — bill uses Architecture mix)
    solar_served = solar_to_load + solar_from_bess
    wind_served = wind_to_load + wind_from_bess
    grid_served = grid_to_load + grid_from_bess
    sim_grid_pct = (grid_to_load / load * 100.0) if load > 0 else 0.0
    sim_grid_served_pct = (grid_served / load * 100.0) if load > 0 else 0.0
    sim_re_pct = (re_serve / load * 100.0) if load > 0 else 0.0
    sim_solar_pct = (solar_to_load / load * 100.0) if load > 0 else 0.0
    sim_wind_pct = (wind_to_load / load * 100.0) if load > 0 else 0.0
    sim_bess_pct = (throughput / load * 100.0) if load > 0 else 0.0
    sim_solar_origin_pct = (solar_served / load * 100.0) if load > 0 else 0.0
    sim_wind_origin_pct = (wind_served / load * 100.0) if load > 0 else 0.0

    # Bill blend shares = Architecture contracted mix (fixed-rate pricing)
    mixes = _architecture_mix_pcts(config)
    contract_grid = float(mixes["discom"])
    contract_solar = float(mixes["solar"])
    contract_wind = float(mixes["wind"])
    contract_bess = float(mixes["bess"])
    contract_re = contract_solar + contract_wind + contract_bess
    dispatch_unserved = float(d.unserved_mw.sum()) if len(d.unserved_mw) else 0.0

    return {
        "solar_mw": 0.0,
        "wind_mw": 0.0,
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
        "architecture_re_mix_pct": contract_re_mix,
        "dispatch_annual_re_pct": annual_re,
        "hourly_cfe_mean_pct": mean_cfe,
        "hourly_cfe_min_pct": min_cfe,
        "hourly_cfe_median_pct": float(np.median(d.hourly_cfe_pct)) if len(d.hourly_cfe_pct) else 0.0,
        "hourly_cfe_p95_pct": float(np.percentile(d.hourly_cfe_pct, 95)) if len(d.hourly_cfe_pct) else 0.0,
        "hourly_cfe_energy_weighted_pct": ew_cfe,
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
        "bess_charge_efficiency": eta_c,
        "bess_discharge_efficiency": eta_d,
        "bess_round_trip_efficiency": eta_c * eta_d,
        "bess_re_origin_discharge_mwh": float(d.re_from_bess_mw.sum()),
        "bess_solar_origin_discharge_mwh": solar_from_bess,
        "bess_wind_origin_discharge_mwh": wind_from_bess,
        "bess_grid_origin_discharge_mwh": grid_from_bess,
        "bess_renewable_charging_pct": re_origin_share,
        "bess_grid_charging_pct": (100.0 - re_origin_share) if total_charged > 0 else 0.0,
        # Buyer path: feasibility does not gate on plant-profile unserved
        "unserved_mwh": 0.0,
        "dispatch_unserved_mwh": dispatch_unserved,
        "re_origin_stored_share_pct": re_origin_share,
        "re_charge_mwh": re_charged,
        "grid_charge_mwh": grid_charged,
        "solar_to_load_mwh": solar_to_load,
        "wind_to_load_mwh": wind_to_load,
        "grid_to_load_mwh": grid_to_load,
        "target_mix_discom_pct": contract_grid,
        "target_mix_solar_pct": contract_solar,
        "target_mix_wind_pct": contract_wind,
        "target_mix_bess_pct": contract_bess,
        # Bill blend G|S|W|B = Architecture contracted mix
        "simulated_mix_grid_pct": contract_grid,
        "simulated_mix_grid_served_pct": contract_grid,
        "simulated_mix_re_pct": contract_re,
        "simulated_mix_solar_pct": contract_solar,
        "simulated_mix_wind_pct": contract_wind,
        "simulated_mix_bess_pct": contract_bess,
        # Physical 8760 availability shares (charts / CFE diagnostics)
        "dispatch_mix_grid_pct": sim_grid_pct,
        "dispatch_mix_grid_served_pct": sim_grid_served_pct,
        "dispatch_mix_re_pct": sim_re_pct,
        "dispatch_mix_solar_pct": sim_solar_pct,
        "dispatch_mix_wind_pct": sim_wind_pct,
        "dispatch_mix_bess_pct": sim_bess_pct,
        "simulated_mix_solar_origin_pct": sim_solar_origin_pct,
        "simulated_mix_wind_origin_pct": sim_wind_origin_pct,
        "max_grid_import_mw": float(d.grid_mw.max()) if len(d.grid_mw) else 0.0,
        "max_abs_balance_error_mw": float(d.meta.get("max_abs_balance_error_mw") or 0.0),
        "dispatch_mode": d.meta.get("dispatch_mode"),
    }


def monthly_balance(d: DispatchResult, config: dict) -> list[dict]:
    hours = len(d.load_mw)
    try:
        sm = int(v(config, "general.study_start_month"))
        em = int(v(config, "general.study_end_month"))
        cal = get_calendar(start_month=sm, end_month=em)
        if cal.hours != hours:
            cal = get_calendar(hours)
    except Exception:
        cal = get_calendar(hours)
    mixes = _architecture_mix_pcts(config)
    arch_re = float(mixes["solar"] + mixes["wind"] + mixes["bess"])
    rows = []
    for i, (a, b) in enumerate(month_slices(cal=cal)):
        load = float(d.load_mw[a:b].sum()) if b > a else 0.0
        re_serve = float(d.re_serving_load_mw[a:b].sum()) if b > a else 0.0
        cfe = float(np.mean(d.hourly_cfe_pct[a:b])) if b > a else 0.0
        rows.append(
            {
                "month": MONTH_NAMES[i],
                "month_index": i + 1,
                "load_mwh": load,
                "solar_mwh": float(d.solar_mw[a:b].sum()) if b > a else 0.0,
                "wind_mwh": float(d.wind_mw[a:b].sum()) if b > a else 0.0,
                "direct_re_mwh": float(d.direct_re_mw[a:b].sum()) if b > a else 0.0,
                "bess_charge_mwh": float(d.charge_mw[a:b].sum()) if b > a else 0.0,
                "bess_discharge_mwh": float(d.discharge_mw[a:b].sum()) if b > a else 0.0,
                "grid_mwh": float(d.grid_mw[a:b].sum()) if b > a else 0.0,
                "curtailment_mwh": float(d.curtailment_mw[a:b].sum()) if b > a else 0.0,
                # Availability KPIs (TOD/dispatch); Architecture mix kept for bill separately
                "re_pct": (re_serve / load * 100.0) if load > 0 else 0.0,
                "cfe_mean_pct": cfe,
                "architecture_re_mix_pct": arch_re,
                "dispatch_re_pct": (re_serve / load * 100.0) if load > 0 else 0.0,
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
    try:
        sm = int(v(cfg, "general.study_start_month"))
        em = int(v(cfg, "general.study_end_month"))
    except Exception:
        sm, em = 1, 12
    # Prefer month-range calendar when hours match the selected months; else prefix/full by hours
    from backend.simulation.calendar import hours_in_month_range

    auto_h = hours_in_month_range(sm, em, leap=False)
    if hours == auto_h or hours in (8760, 8784):
        cal = get_calendar(start_month=sm, end_month=em, leap=(hours == 8784 and sm == 1 and em == 12))
        hours = cal.hours
        cfg["general"]["model_hours"]["value"] = hours
    else:
        cal = get_calendar(hours)
        hours = cal.hours

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
                    gen_key["actual_cf_pct"] = float(solar.get("actual_cf_pct") or 0.0)
                if kind == "wind":
                    gen_key["actual_cf_pct"] = float(wind.get("actual_cf_pct") or 0.0)

    # Architecture mix % → annual energy contracts; TOD/profile shapes kept for hourly CFE
    solar_mw, wind_mw, bess_power_mw, bess_energy_mwh, grid_cap_mw = apply_setup_energy_contracts(
        cfg,
        load["load_mw"],
        solar.get("solar_mw") if solar else None,
        wind.get("wind_mw") if wind else None,
    )
    solar["solar_mw"] = solar_mw
    solar["annual_mwh"] = float(solar_mw.sum())
    wind["wind_mw"] = wind_mw
    wind["annual_mwh"] = float(wind_mw.sum())
    # capacity_overrides ignored on buyer path (no plant MW)

    d = run_dispatch(
        cfg,
        load["load_mw"],
        solar_mw,
        wind_mw,
        cal.hour_of_day,
        bess_power_mw=bess_power_mw,
        bess_energy_mwh=bess_energy_mwh,
        grid_cap_mw=grid_cap_mw,
    )
    d.meta["study_start_month"] = int(cal.start_month)
    d.meta["study_end_month"] = int(cal.end_month)
    d.meta["model_hours"] = int(cal.hours)

    kpis = summarize_dispatch(cfg, d)
    kpis["actual_load_factor_pct"] = load["actual_load_factor_pct"]
    kpis["solar_cf_pct"] = solar["actual_cf_pct"]
    kpis["wind_cf_pct"] = wind["actual_cf_pct"]
    kpis["structure"] = str(v(cfg, "commercial.structure"))

    from backend.compliance.cfe_analytics import analyze_cfe

    matched = getattr(d, "matched_cf_mw", None)
    supply = getattr(d, "cf_supply_mw", None)
    cfe_analytics = analyze_cfe(
        cfg,
        d.hourly_cfe_pct,
        kpis["annual_re_pct"],
        load_mw=d.load_mw,
        cf_supply_mw=supply if supply is not None and len(supply) else None,
        matched_cf_mw=matched if matched is not None and len(matched) else None,
    )
    kpis["annual_cfe_pct"] = cfe_analytics["annual_cfe_pct"]
    kpis["cfe_analytics"] = cfe_analytics
    kpis["hourly_cfe_energy_weighted_pct"] = cfe_analytics["annual_cfe_pct"]
    kpis["cfe_formula"] = cfe_analytics.get("formula")

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
    sm = d.meta.get("study_start_month")
    em = d.meta.get("study_end_month")
    if sm is not None and em is not None:
        cal = get_calendar(start_month=int(sm), end_month=int(em))
        if cal.hours != n:
            cal = get_calendar(n)
    else:
        cal = get_calendar(n)
    max_doy = int(cal.day_of_year.max()) + 1 if n else 365
    if view == "day":
        doy = max(1, min(max_doy, day)) - 1
        idx = np.where(cal.day_of_year == doy)[0]
    elif view == "week":
        doy = max(1, min(max_doy, day)) - 1
        hits = np.where(cal.day_of_year == doy)[0]
        start = int(hits[0]) if len(hits) else 0
        idx = np.arange(start, min(n, start + 24 * 7))
    elif view == "month":
        m = max(1, min(12, month)) - 1
        a, b = month_slices(cal=cal)[m]
        idx = np.arange(a, b) if b > a else np.array([], dtype=int)
    else:
        idx = np.arange(0, n, max(1, n // 1460))

    def take(arr):
        a = np.asarray(arr, dtype=float) if arr is not None and len(arr) else np.zeros(0)
        if len(a) != n:
            return []
        return a[idx].tolist() if len(idx) else []

    cf = getattr(d, "cf_supply_mw", None)
    if cf is None or len(cf) != n:
        # Fallback: reconstruct CF supply from CFE % × load
        load_arr = np.asarray(d.load_mw, dtype=float)
        cfe = np.asarray(d.hourly_cfe_pct, dtype=float)
        cf = load_arr * (cfe / 100.0)
    grid_residual = np.maximum(0.0, np.asarray(d.load_mw, dtype=float) - np.asarray(cf, dtype=float))

    return {
        "view": view,
        "index": idx.tolist(),
        "hour_of_day": cal.hour_of_day[idx].tolist() if len(idx) else [],
        "load_mw": take(d.load_mw),
        "solar_mw": take(d.solar_mw),
        "wind_mw": take(d.wind_mw),
        "charge_mw": take(d.charge_mw),
        "discharge_mw": take(d.discharge_mw),
        "soc_mwh": take(d.soc_mwh),
        "grid_mw": take(d.grid_mw),
        "curtailment_mw": take(d.curtailment_mw),
        "hourly_cfe_pct": take(d.hourly_cfe_pct),
        "cf_supply_mw": take(cf),
        "grid_contract_mw": take(grid_residual),
        "series_note": (
            "Hourly series use TOD/availability shapes: Solar (daylight), Wind, BESS discharge, DISCOM. "
            "Architecture mix % sets annual contract energy and the bill; CFE is availability each hour."
        ),
    }


def cfe_heatmap(d: DispatchResult) -> list[list[float]]:
    return cfe_heatmap_from_pct(d.hourly_cfe_pct)


def cfe_heatmap_from_pct(hourly_cfe_pct) -> list[list[float]]:
    cfe = np.asarray(hourly_cfe_pct, dtype=float)
    n = len(cfe)
    if n <= 0:
        return [[0.0] * 24 for _ in range(12)]
    cal = get_calendar(n)
    heat = np.zeros((12, 24))
    counts = np.zeros((12, 24))
    for t in range(n):
        m = int(cal.month[t])
        h = int(cal.hour_of_day[t])
        if 0 <= m < 12 and 0 <= h < 24:
            heat[m, h] += float(cfe[t])
            counts[m, h] += 1
    counts = np.maximum(counts, 1.0)
    return (heat / counts).tolist()
