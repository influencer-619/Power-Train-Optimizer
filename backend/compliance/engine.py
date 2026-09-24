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
    """Pass/fail from the 24×7 CFE formula vs hourly target.

    Carbon-free supply follows Architecture mix (Solar% + Wind% + BESS%) × load
    each hour — contracted firm delivery, not plant shapes.
    Pass only if every hour meets ``hourly_cfe_target_pct`` (min hourly CFE ≥ target).
    """
    from backend.compliance.cfe_analytics import CFE_FORMULA

    target = float(v(config, "compliance.hourly_cfe_target_pct"))
    actual_mean = float(kpis["hourly_cfe_mean_pct"])
    actual_min = float(kpis["hourly_cfe_min_pct"])
    hours_meet = float(kpis["hours_meeting_cfe_target_pct"])
    passed = actual_min >= target - 1e-9 and hours_meet >= 100.0 - 1e-9
    return {
        "metric": "Hourly CFE",
        "target_pct": target,
        "actual_pct": actual_min,
        "mean_pct": actual_mean,
        "min_pct": actual_min,
        "hours_meeting_pct": hours_meet,
        "pass_mode": "CFE formula (all hours ≥ target)",
        "formula": CFE_FORMULA,
        "status": "Pass" if passed else "Fail",
        "gap_pct": max(0.0, target - actual_min),
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


def _architecture_re_pct(config: dict, kpis: dict) -> float | None:
    """Architecture mix RE % (Solar + Wind + BESS) — same basis as 24×7 CFE."""
    for key in ("simulated_mix_re_pct",):
        if kpis.get(key) is not None:
            try:
                return max(0.0, min(100.0, float(kpis[key])))
            except Exception:
                pass

    def _num(kpi_key: str, config_path: str, flag_path: str, flag_default: bool) -> float:
        try:
            if not bool(v(config, flag_path)):
                return 0.0
        except Exception:
            if not flag_default:
                return 0.0
        if kpi_key in kpis and kpis[kpi_key] is not None:
            try:
                return max(0.0, float(kpis[kpi_key]))
            except Exception:
                pass
        try:
            return max(0.0, float(v(config, config_path)))
        except Exception:
            return 0.0

    solar = _num("target_mix_solar_pct", "commercial.mix_solar_pct", "commercial.include_solar", True)
    wind = _num("target_mix_wind_pct", "commercial.mix_wind_pct", "commercial.include_wind", True)
    bess = _num("target_mix_bess_pct", "commercial.mix_bess_pct", "commercial.include_bess", True)
    total = solar + wind + bess
    if total > 0 or any(k in kpis for k in ("target_mix_solar_pct", "target_mix_wind_pct", "target_mix_bess_pct")):
        return min(100.0, max(0.0, total))

    if kpis.get("annual_re_pct") is not None:
        try:
            return max(0.0, min(100.0, float(kpis["annual_re_pct"])))
        except Exception:
            pass
    try:
        from backend.compliance.cfe_analytics import architecture_cf_fraction

        return architecture_cf_fraction(config) * 100.0
    except Exception:
        return 0.0


def _architecture_bess_pct(config: dict, kpis: dict) -> float:
    """Contracted BESS share of load from Architecture mix."""
    for key in ("simulated_mix_bess_pct", "target_mix_bess_pct"):
        if kpis.get(key) is not None:
            try:
                return max(0.0, min(100.0, float(kpis[key])))
            except Exception:
                pass
    try:
        if not bool(v(config, "commercial.include_bess")):
            return 0.0
    except Exception:
        pass
    try:
        return max(0.0, min(100.0, float(v(config, "commercial.mix_bess_pct"))))
    except Exception:
        return 0.0


def _read_rpo_rco_param(config: dict, integrated: str, *legacy: str, default=None):
    """Prefer integrated RPO/RCO key; fall back to first available legacy key."""
    try:
        return v(config, f"compliance.{integrated}")
    except Exception:
        pass
    for key in legacy:
        try:
            return v(config, f"compliance.{key}")
        except Exception:
            continue
    return default


def evaluate_rpo_rco(config: dict, kpis: dict) -> dict:
    """Single integrated RPO/RCO obligation (purchase + consumption)."""
    appl = str(
        _read_rpo_rco_param(
            config,
            "rpo_rco_applicability",
            "rpo_applicability",
            "rco_applicability",
            default="Unknown / Legal Review Required",
        )
    )
    load = float(kpis["annual_load_mwh"])
    mix_re = _architecture_re_pct(config, kpis)
    actual_pct = float(mix_re if mix_re is not None else 0.0)
    re_mwh = load * actual_pct / 100.0
    actual_basis = "architecture_mix"

    try:
        target = float(
            _read_rpo_rco_param(config, "rpo_rco_target_pct", "rpo_target_pct", "rco_target_pct", default=0.0)
        )
    except Exception:
        target = 0.0
        for key in (
            "rpo_solar_target_pct",
            "rpo_wind_target_pct",
            "rpo_hydro_target_pct",
            "rpo_other_target_pct",
        ):
            try:
                target += float(v(config, f"compliance.{key}"))
            except Exception:
                pass
    target = max(0.0, min(100.0, float(target or 0.0)))

    required_mwh = load * target / 100.0
    gap_mwh = max(0.0, required_mwh - re_mwh)

    route = str(
        _read_rpo_rco_param(
            config,
            "rpo_rco_compliance_route",
            "rco_compliance_route",
            default="Buyout",
        )
        or "Buyout"
    )
    if route == "REC":
        rate = float(
            _read_rpo_rco_param(
                config,
                "rpo_rco_rec_inr_per_kwh",
                "rco_rec_inr_per_kwh",
                default=1.0,
            )
            or 1.0
        )
    else:
        rate = float(
            _read_rpo_rco_param(
                config,
                "rpo_rco_buyout_inr_per_kwh",
                "rpo_buyout_inr_per_kwh",
                "rco_buyout_inr_per_kwh",
                default=1.0,
            )
            or 1.0
        )

    cost = gap_mwh * 1000.0 * rate if appl == "Applicable" else 0.0
    passed = gap_mwh <= 1e-6
    return {
        "metric": "RPO/RCO",
        "applicability": appl,
        "target_pct": target,
        "actual_pct": actual_pct,
        "actual_basis": actual_basis,
        "required_mwh": required_mwh,
        "actual_mwh": re_mwh,
        "gap_mwh": gap_mwh,
        "compliance_route": route,
        "status": _status(appl, passed if appl == "Applicable" else None),
        "compliance_cost_inr": cost,
        "legal_note": "LEGAL REVIEW REQUIRED" if appl == "Unknown / Legal Review Required" else "",
    }


# Back-compat aliases (same integrated result)
def evaluate_rpo(config: dict, kpis: dict) -> dict:
    out = evaluate_rpo_rco(config, kpis)
    return {**out, "metric": "RPO/RCO"}


def evaluate_rco(config: dict, kpis: dict) -> dict:
    return evaluate_rpo(config, kpis)


def evaluate_eso(config: dict, kpis: dict) -> dict:
    appl = str(v(config, "compliance.eso_applicability"))
    try:
        target = float(v(config, "compliance.eso_target_pct"))
    except Exception:
        # Legacy: pick active-year value from multi-year trajectory
        year = "FY2026-27"
        try:
            year = str(v(config, "compliance.eso_active_year"))
        except Exception:
            pass
        mapping = {}
        for ykey, ckey in (
            ("FY2026-27", "eso_fy2026_27_pct"),
            ("FY2027-28", "eso_fy2027_28_pct"),
            ("FY2028-29", "eso_fy2028_29_pct"),
            ("FY2029-30", "eso_fy2029_30_pct"),
        ):
            try:
                mapping[ykey] = float(v(config, f"compliance.{ckey}"))
            except Exception:
                pass
        target = mapping.get(year, mapping.get("FY2026-27", 0.0))
    target = max(0.0, min(100.0, target))
    load = float(kpis["annual_load_mwh"])
    required_storage = load * target / 100.0
    # Buyer path: contracted BESS mix % × load (no plant charge/discharge MW)
    bess_pct = _architecture_bess_pct(config, kpis)
    actual_storage = load * bess_pct / 100.0
    # Contracted Storage tariff energy is treated as renewable-origin for ESO
    re_origin = 100.0 if actual_storage > 1e-9 else 100.0
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
        "target_pct": target,
        "required_storage_mwh": required_storage,
        "actual_storage_energy_mwh": actual_storage,
        "re_origin_storage_pct": re_origin,
        "re_origin_requirement_pct": origin_req,
        "actual_basis": "architecture_mix",
        "status": _status(appl, passed if appl == "Applicable" else None),
        "compliance_cost_inr": cost,
        "gap_storage_mwh": gap_energy,
        "storage_ok": storage_ok,
        "origin_ok": origin_ok,
    }


def evaluate_compliance(config: dict, kpis: dict) -> dict:
    re = evaluate_re(config, kpis)
    cfe = evaluate_cfe(config, kpis)
    rpo_rco = evaluate_rpo_rco(config, kpis)
    eso = evaluate_eso(config, kpis)
    total_cost = float(rpo_rco["compliance_cost_inr"]) + float(eso["compliance_cost_inr"])
    return {
        "annual_re": re,
        "hourly_cfe": cfe,
        "rpo_rco": rpo_rco,
        # Aliases so older UI / feasibility still resolve one integrated result
        "rpo": rpo_rco,
        "rco": rpo_rco,
        "eso": eso,
        "total_compliance_cost_inr": total_cost,
    }
