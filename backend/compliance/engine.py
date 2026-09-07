"""RPO / RCO / ESO / RE / CFE compliance engine."""

from __future__ import annotations

from config.defaults import LEGAL_REVIEW, v


def _status(applicability: str, pass_: bool | None) -> str:
    if applicability == "Not Applicable":
        return "Not Applicable"
    if applicability == "Unknown / Legal Review Required":
        return LEGAL_REVIEW
    if pass_ is None:
        return LEGAL_REVIEW
    return "Pass" if pass_ else "Fail"


def evaluate_cfe(config: dict, kpis: dict) -> dict:
    target = float(v(config, "compliance.hourly_cfe_target_pct"))
    mode = str(v(config, "compliance.cfe_pass_mode"))
    actual_mean = float(kpis["hourly_cfe_mean_pct"])
    actual_min = float(kpis["hourly_cfe_min_pct"])
    hours_meet = float(kpis["hours_meeting_cfe_target_pct"])
    share_target = float(v(config, "compliance.cfe_hour_share_target_pct"))

    if mode == "All hours >= target":
        passed = hours_meet >= 100.0 - 1e-9
        actual = actual_min
    elif mode == "Mean hourly CFE >= target":
        passed = actual_mean >= target - 1e-9
        actual = actual_mean
    else:
        passed = hours_meet >= share_target - 1e-9
        actual = hours_meet

    return {
        "metric": "Hourly CFE",
        "target_pct": target,
        "actual_pct": actual,
        "mean_pct": actual_mean,
        "min_pct": actual_min,
        "hours_meeting_pct": hours_meet,
        "pass_mode": mode,
        "status": "Pass" if passed else "Fail",
        "gap_pct": max(0.0, target - actual) if mode != "Share of hours >= target" else max(0.0, share_target - hours_meet),
    }


def evaluate_re(config: dict, kpis: dict) -> dict:
    target = float(v(config, "compliance.annual_re_target_pct"))
    actual = float(kpis["annual_re_pct"])
    return {
        "metric": "Annual RE %",
        "target_pct": target,
        "actual_pct": actual,
        "status": "Pass" if actual >= target - 1e-9 else "Fail",
        "gap_pct": max(0.0, target - actual),
    }


def evaluate_rpo(config: dict, kpis: dict) -> dict:
    appl = str(v(config, "compliance.rpo_applicability"))
    load = float(kpis["annual_load_mwh"])
    solar = float(kpis["annual_solar_mwh"])
    wind = float(kpis["annual_wind_mwh"])
    targets = {
        "solar": float(v(config, "compliance.rpo_solar_target_pct")),
        "wind": float(v(config, "compliance.rpo_wind_target_pct")),
        "hydro": float(v(config, "compliance.rpo_hydro_target_pct")),
        "other": float(v(config, "compliance.rpo_other_target_pct")),
    }
    required = {k: load * t / 100.0 for k, t in targets.items()}
    actual = {"solar": solar, "wind": wind, "hydro": 0.0, "other": 0.0}
    gaps = {k: max(0.0, required[k] - actual[k]) for k in targets}
    total_gap = sum(gaps.values())
    buyout = float(v(config, "compliance.rpo_buyout_inr_per_kwh"))
    cost = total_gap * 1000.0 * buyout if appl == "Applicable" else 0.0
    passed = total_gap <= 1e-6
    return {
        "metric": "RPO",
        "applicability": appl,
        "targets_pct": targets,
        "required_mwh": required,
        "actual_mwh": actual,
        "gap_mwh": gaps,
        "status": _status(appl, passed if appl == "Applicable" else None),
        "compliance_cost_inr": cost,
    }


def evaluate_rco(config: dict, kpis: dict) -> dict:
    appl = str(v(config, "compliance.rco_applicability"))
    target = float(v(config, "compliance.rco_target_pct"))
    actual = float(kpis["annual_re_pct"])
    load = float(kpis["annual_load_mwh"])
    gap_mwh = max(0.0, load * target / 100.0 - float(kpis["re_serving_load_mwh"]))
    route = str(v(config, "compliance.rco_compliance_route"))
    if route == "REC":
        rate = float(v(config, "compliance.rco_rec_inr_per_kwh"))
    else:
        rate = float(v(config, "compliance.rco_buyout_inr_per_kwh"))
    cost = gap_mwh * 1000.0 * rate if appl == "Applicable" else 0.0
    passed = actual >= target - 1e-9
    return {
        "metric": "RCO",
        "applicability": appl,
        "target_pct": target,
        "actual_pct": actual,
        "gap_mwh": gap_mwh,
        "compliance_route": route,
        "status": _status(appl, passed if appl == "Applicable" else None),
        "compliance_cost_inr": cost,
        "legal_note": "LEGAL REVIEW REQUIRED" if appl != "Applicable" else "",
    }


def evaluate_eso(config: dict, kpis: dict) -> dict:
    appl = str(v(config, "compliance.eso_applicability"))
    year = str(v(config, "compliance.eso_active_year"))
    mapping = {
        "FY2026-27": float(v(config, "compliance.eso_fy2026_27_pct")),
        "FY2027-28": float(v(config, "compliance.eso_fy2027_28_pct")),
        "FY2028-29": float(v(config, "compliance.eso_fy2028_29_pct")),
        "FY2029-30": float(v(config, "compliance.eso_fy2029_30_pct")),
    }
    target = mapping.get(year, mapping["FY2026-27"])
    load = float(kpis["annual_load_mwh"])
    required_storage = load * target / 100.0
    actual_storage = float(kpis["bess_charge_mwh"])
    re_origin = float(kpis["re_origin_stored_share_pct"])
    origin_req = float(v(config, "compliance.eso_re_origin_min_pct"))
    storage_ok = actual_storage >= required_storage - 1e-6
    origin_ok = (actual_storage <= 1e-9) or (re_origin >= origin_req - 1e-9)
    passed = storage_ok and origin_ok
    gap_energy = max(0.0, required_storage - actual_storage)
    buyout = float(v(config, "compliance.eso_buyout_inr_per_kwh"))
    cost = 0.0
    if appl == "Applicable":
        cost = gap_energy * 1000.0 * buyout
        if actual_storage > 0 and not origin_ok:
            cost += actual_storage * 1000.0 * buyout
    return {
        "metric": "ESO",
        "applicability": appl,
        "active_year": year,
        "target_pct": target,
        "required_storage_mwh": required_storage,
        "actual_storage_energy_mwh": actual_storage,
        "re_origin_storage_pct": re_origin,
        "re_origin_requirement_pct": origin_req,
        "status": _status(appl, passed if appl == "Applicable" else None),
        "compliance_cost_inr": cost,
        "trajectory": mapping,
    }


def evaluate_compliance(config: dict, kpis: dict) -> dict:
    re = evaluate_re(config, kpis)
    cfe = evaluate_cfe(config, kpis)
    rpo = evaluate_rpo(config, kpis)
    rco = evaluate_rco(config, kpis)
    eso = evaluate_eso(config, kpis)
    total_cost = (
        float(rpo["compliance_cost_inr"])
        + float(rco["compliance_cost_inr"])
        + float(eso["compliance_cost_inr"])
    )
    return {
        "annual_re": re,
        "hourly_cfe": cfe,
        "rpo": rpo,
        "rco": rco,
        "eso": eso,
        "total_compliance_cost_inr": total_cost,
    }
