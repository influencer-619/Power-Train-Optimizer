"""Optimization explainability helpers."""

from __future__ import annotations

from typing import Any


def explain_winner(winner: dict, rejected_nearby: list[dict] | None = None) -> dict[str, Any]:
    """Human-readable why-this-configuration text from actual KPIs (not hard-coded numbers)."""
    c = winner["candidate"]
    k = winner["kpis"]
    f = winner["financial"]
    comp = winner["compliance"]
    rejected_nearby = rejected_nearby or []

    bullets = [
        f"Solar {c['solar_mw']:.0f} MW, Wind {c['wind_mw']:.0f} MW, "
        f"BESS {c['bess_mw']:.0f} MW / {c['bess_mwh']:.0f} MWh, Grid {c['grid_mw']:.0f} MW.",
        f"Annual RE {k['annual_re_pct']:.1f}% (status {comp['annual_re']['status']}); "
        f"Hourly CFE min {k['hourly_cfe_min_pct']:.1f}% (mode {comp['hourly_cfe']['pass_mode']}, "
        f"status {comp['hourly_cfe']['status']}).",
        f"Grid import {k['grid_gwh']:.2f} GWh; curtailment {k['curtailment_pct']:.1f}%; "
        f"unserved {k['unserved_mwh']:.1f} MWh.",
        f"Delivered-energy cost ₹{f['cost_per_kwh']:.4f}/kWh; "
        f"NPV ₹{f.get('npv_cr', 0):.2f} Cr.",
    ]
    if k.get("hourly_cfe_min_pct", 100) < float(comp["hourly_cfe"].get("target_pct") or 90):
        bullets.append(
            "Night / low-RE hours remain the CFE stress — BESS duration and wind drive deficit coverage."
        )
    else:
        bullets.append("CFE pass mode is satisfied under the selected rule.")

    why_selected = "Selected as lowest-scoring feasible candidate under the active objective."
    alts = []
    for r in rejected_nearby[:5]:
        alts.append(
            {
                "candidate": r.get("candidate"),
                "cost_per_kwh": r.get("financial", {}).get("cost_per_kwh"),
                "annual_re_pct": r.get("kpis", {}).get("annual_re_pct"),
                "hourly_cfe_min_pct": r.get("kpis", {}).get("hourly_cfe_min_pct"),
                "feasible": r.get("feasible"),
                "binding_constraints": r.get("binding_constraints"),
                "why_not": (
                    "Infeasible: " + "; ".join(r.get("binding_constraints") or [])
                    if not r.get("feasible")
                    else "Feasible but worse objective score than the winner."
                ),
            }
        )

    return {
        "headline": "WHY THIS CONFIGURATION?",
        "bullets": bullets,
        "why_selected": why_selected,
        "alternatives": alts,
        "can_recommend": bool(winner.get("feasible")),
        "recommendation_label": "RECOMMENDED" if winner.get("feasible") else "NOT RECOMMENDED (infeasible)",
    }


def marginal_capacity_analysis(base_result: dict, variants: list[dict]) -> dict[str, Any]:
    """Compare incremental capacity steps using evaluated candidate results."""
    rows = []
    base_k = base_result["kpis"]
    base_f = base_result["financial"]
    for var in variants:
        k = var["kpis"]
        f = var["financial"]
        rows.append(
            {
                "label": var.get("label"),
                "candidate": var.get("candidate"),
                "delta_cost_per_kwh": float(f["cost_per_kwh"]) - float(base_f["cost_per_kwh"]),
                "delta_annual_re_pp": float(k["annual_re_pct"]) - float(base_k["annual_re_pct"]),
                "delta_cfe_min_pp": float(k["hourly_cfe_min_pct"]) - float(base_k["hourly_cfe_min_pct"]),
                "delta_grid_gwh": float(k["grid_gwh"]) - float(base_k["grid_gwh"]),
                "delta_curtailment_pp": float(k["curtailment_pct"]) - float(base_k["curtailment_pct"]),
                "delta_npv_cr": float(f.get("npv_cr") or 0) - float(base_f.get("npv_cr") or 0),
                "cost_per_kwh": f["cost_per_kwh"],
                "annual_re_pct": k["annual_re_pct"],
                "hourly_cfe_min_pct": k["hourly_cfe_min_pct"],
                "feasible": var.get("feasible"),
            }
        )
    return {"base": base_result.get("candidate"), "steps": rows}
