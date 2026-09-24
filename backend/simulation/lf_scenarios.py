"""Load-factor scenario helpers (no DB / ORM imports)."""

from __future__ import annotations

from typing import Any

from config.defaults import recompute_calculated, v


def load_factor_scenario_values(config: dict) -> list[tuple[int, float]]:
    """Return [(scenario_index, load_factor_pct), ...] for up to four LF scenarios."""
    out: list[tuple[int, float]] = []
    for i in range(1, 5):
        try:
            lf = float(v(config, f"load.load_factor_s{i}_pct"))
        except Exception:
            if i == 1:
                try:
                    lf = float(v(config, "load.load_factor_pct"))
                except Exception:
                    lf = 80.0
            else:
                continue
        lf = max(1.0, min(100.0, lf))
        out.append((i, lf))
    if not out:
        try:
            lf = float(v(config, "load.load_factor_pct"))
        except Exception:
            lf = 80.0
        out = [(1, max(1.0, min(100.0, lf)))]
    return out


def apply_scenario_load_factor(config: dict, lf: float) -> dict:
    """Set load factor for one LF scenario without letting recompute snap back to S1.

    ``recompute_calculated`` syncs ``load_factor_pct`` from ``load_factor_s1_pct``
    unless source is SCENARIO/USER. Mark override as SCENARIO so nested
    recompute inside ``run_simulation`` keeps the scenario LF.
    """
    lf = max(1.0, min(100.0, float(lf)))
    config = recompute_calculated(config)
    config["load"]["load_factor_pct"]["value"] = lf
    config["load"]["load_factor_pct"]["source"] = "SCENARIO"
    try:
        peak = float(v(config, "load.peak_load_mw"))
        if "base_load_mw" in config.get("load", {}):
            config["load"]["base_load_mw"]["value"] = round(peak * lf / 100.0, 6)
    except Exception:
        pass
    # Refresh calculated fields that depend on LF (e.g. base_load) while preserving SCENARIO.
    config = recompute_calculated(config)
    return config


def lf_scenario_summary(idx: int, lf: float, eval_out: dict[str, Any]) -> dict[str, Any]:
    bundle = eval_out["bundle"]
    financial = eval_out["financial"]
    compliance = eval_out["compliance"]
    xt = financial.get("excel_tariff") or {}
    carbon = financial.get("carbon") or {}
    kpis = bundle.kpis or {}
    ca = kpis.get("cfe_analytics") or {}
    hc = (compliance.get("hourly_cfe") or {}) if isinstance(compliance, dict) else {}
    return {
        "id": idx,
        "label": f"LF {lf:g}%",
        "load_factor_pct": lf,
        "annual_load_mwh": float(
            xt.get("annual_load_mwh")
            if xt.get("annual_load_mwh") is not None
            else carbon.get("annual_load_mwh")
            if carbon.get("annual_load_mwh") is not None
            else kpis.get("annual_load_mwh")
            or 0.0
        ),
        "cost_per_kwh": financial.get("cost_per_kwh"),
        "annual_energy_cr": xt.get("annual_energy_cr"),
        "annual_bill_cr": xt.get("annual_bill_cr") or xt.get("annual_energy_cr"),
        "savings_vs_discom_cr": xt.get("savings_vs_discom_cr"),
        "npv_cr": financial.get("npv_cr"),
        "cfe_pct": xt.get("cfe_pct") or carbon.get("cfe_pct"),
        "carbon_saved_tco2": xt.get("carbon_saved_tco2") or carbon.get("carbon_saved_tco2"),
        "baseline_tco2": xt.get("baseline_tco2") or carbon.get("baseline_tco2"),
        "actual_tco2": xt.get("actual_tco2") or carbon.get("actual_tco2"),
        "blended_rate_inr_per_kwh": xt.get("blended_rate_inr_per_kwh"),
        "annual_re_pct": kpis.get("annual_re_pct"),
        "compliance_re_status": (compliance.get("annual_re") or {}).get("status"),
        "hourly_cfe_min_pct": ca.get("min_hourly_cfe_pct", kpis.get("hourly_cfe_min_pct", hc.get("min_pct"))),
        "hourly_cfe_mean_pct": ca.get("mean_hourly_cfe_pct", kpis.get("hourly_cfe_mean_pct", hc.get("mean_pct"))),
        "hours_meeting_cfe_target_pct": ca.get(
            "pct_hours_ge_target", kpis.get("hours_meeting_cfe_target_pct", hc.get("hours_meeting_pct"))
        ),
        "longest_continuous_deficit_hours": ca.get("longest_continuous_deficit_hours"),
        "max_cfe_deficit_pp": ca.get("max_cfe_deficit_pp"),
        "hourly_cfe_passed": ca.get("passed") if ca.get("passed") is not None else (hc.get("status") == "Pass"),
        "cost_breakdown": financial.get("cost_breakdown") or {},
    }
