"""Staged capacity optimization with transparent ranking.

Algorithm (documented for MODEL_METHODOLOGY.md):
1. Capacity screening — generate a bounded candidate set for
   Solar MW, Wind MW, BESS MW, BESS MWh, Grid MW.
2. Feasibility screening — run 8,760 rule-based (or LP) dispatch.
3. Dispatch optimisation — optional LP dispatch mode.
4. Economic evaluation — commercial + compliance + financial engines.
5. Ranking — by selected objective; return top 10 feasible solutions.
"""

from __future__ import annotations

import itertools
import time
from copy import deepcopy
from typing import Callable

import numpy as np

from backend.compliance.engine import evaluate_compliance
from backend.financial.engine import evaluate_financial, incremental_vs_discom
from backend.simulation.engine import run_simulation
from config.defaults import v


def _steps(vmin: float, vmax: float, step: float) -> list[float]:
    if step <= 0:
        return [float(vmin)]
    n = int(np.floor((vmax - vmin) / step)) + 1
    vals = [round(vmin + i * step, 6) for i in range(max(n, 1))]
    if vals[-1] < vmax - 1e-9:
        vals.append(float(vmax))
    return vals


def _candidate_set(config: dict, mode: str) -> list[dict]:
    smin, smax, sstep = (
        float(v(config, "optimization.solar_min_mw")),
        float(v(config, "optimization.solar_max_mw")),
        float(v(config, "optimization.solar_step_mw")),
    )
    wmin, wmax, wstep = (
        float(v(config, "optimization.wind_min_mw")),
        float(v(config, "optimization.wind_max_mw")),
        float(v(config, "optimization.wind_step_mw")),
    )
    peak = float(v(config, "load.peak_load_mw"))
    bp_max = float(v(config, "optimization.bess_power_max_mw"))
    be_max = float(v(config, "optimization.bess_energy_max_mwh"))
    gmin = float(v(config, "optimization.grid_min_mw"))
    gmax = float(v(config, "optimization.grid_max_mw"))

    if mode == "Quick":
        solar = _steps(smin, smax, max(sstep * 4, sstep))
        wind = _steps(wmin, wmax, max(wstep * 4, wstep))
        bess_p = [0.0, 0.25 * peak, 0.5 * peak, min(bp_max, peak)]
        durs = [0.0, 2.0, 4.0]
        grid = [0.5 * peak, peak, gmax]
        limit = 80
    elif mode == "Thorough":
        solar = _steps(smin, smax, sstep)
        wind = _steps(wmin, wmax, wstep)
        bess_p = [0.0, 0.25 * peak, 0.5 * peak, 0.75 * peak, min(bp_max, peak)]
        durs = [0.0, 1.0, 2.0, 4.0, 6.0]
        grid = [0.25 * peak, 0.5 * peak, 0.75 * peak, peak, gmax]
        limit = 400
    else:
        solar = _steps(smin, smax, max(sstep * 2, sstep))
        wind = _steps(wmin, wmax, max(wstep * 2, wstep))
        bess_p = [0.0, 0.25 * peak, 0.5 * peak, 0.75 * peak, min(bp_max, peak)]
        durs = [0.0, 2.0, 4.0, 6.0]
        grid = [0.5 * peak, 0.75 * peak, peak, gmax]
        limit = 180

    solar = [x for x in solar if x <= smax + 1e-9]
    wind = [x for x in wind if x <= wmax + 1e-9]
    bess_p = sorted({round(min(max(0.0, x), bp_max), 3) for x in bess_p})
    grid = sorted({round(min(max(gmin, x), gmax), 3) for x in grid})

    # Stratified product + Latin-like thinning
    raw = []
    for s, w, bp, dur, g in itertools.product(solar, wind, bess_p, durs, grid):
        be = 0.0 if bp <= 0 or dur <= 0 else min(be_max, bp * dur)
        raw.append({"solar_mw": s, "wind_mw": w, "bess_mw": bp, "bess_mwh": be, "grid_mw": g})

    if len(raw) <= limit:
        return raw
    # Keep axis-aligned extremes and evenly spaced sample
    idx = np.linspace(0, len(raw) - 1, limit).astype(int)
    picked = [raw[i] for i in sorted(set(idx.tolist()))]
    # Always include current project capacities
    picked.append(
        {
            "solar_mw": float(v(config, "solar.capacity_mw")),
            "wind_mw": float(v(config, "wind.capacity_mw")),
            "bess_mw": float(v(config, "bess.power_mw")),
            "bess_mwh": float(v(config, "bess.energy_mwh")),
            "grid_mw": float(v(config, "grid.max_import_mw")),
        }
    )
    # Deduplicate
    uniq = []
    seen = set()
    for c in picked:
        key = tuple(round(c[k], 3) for k in ("solar_mw", "wind_mw", "bess_mw", "bess_mwh", "grid_mw"))
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq


def _cfe_pass(config: dict, compliance: dict) -> bool:
    return compliance["hourly_cfe"]["status"] == "Pass"


def _feasible(config: dict, kpis: dict, compliance: dict) -> tuple[bool, list[str]]:
    reasons = []
    if bool(v(config, "optimization.enforce_no_unserved")) and float(kpis["unserved_mwh"]) > 1e-3:
        reasons.append("Grid capacity / availability insufficient (unserved energy)")
    if bool(v(config, "optimization.enforce_re_target")) and compliance["annual_re"]["status"] != "Pass":
        reasons.append("RE target too high / renewable capacity insufficient")
    if bool(v(config, "optimization.enforce_cfe_target")) and not _cfe_pass(config, compliance):
        reasons.append("CFE target too high / BESS capacity insufficient")
    return (len(reasons) == 0), reasons


def _score(objective: str, fin: dict, kpis: dict, compliance: dict, config: dict) -> float:
    # Lower is better for ranking
    cost = float(fin["cost_per_kwh"])
    re = float(kpis["annual_re_pct"])
    cfe = float(kpis["hourly_cfe_min_pct"])
    grid = float(kpis["grid_gwh"])
    if objective == "Minimum Cost":
        return cost
    if objective == "Maximum RE":
        return -re
    if objective == "Maximum CFE":
        return -cfe
    if objective == "Minimum Grid Dependency":
        return grid
    if objective == "Compliance First":
        penalty = 0.0 if (
            compliance["annual_re"]["status"] == "Pass" and compliance["hourly_cfe"]["status"] == "Pass"
        ) else 1e6
        return penalty + cost
    # Balanced
    wc = float(v(config, "optimization.weight_cost"))
    wr = float(v(config, "optimization.weight_re"))
    wf = float(v(config, "optimization.weight_cfe"))
    wg = float(v(config, "optimization.weight_grid"))
    # normalize roughly
    return wc * cost - wr * (re / 100.0) - wf * (cfe / 100.0) + wg * (grid / 100.0)


def evaluate_candidate(
    base_config: dict,
    candidate: dict,
    structure: str,
    discom_cache: dict | None = None,
    project_id: int | None = None,
) -> dict:
    bundle = run_simulation(
        base_config,
        structure=structure,
        capacity_overrides=candidate,
        skip_validation=True,
        project_id=project_id,
    )
    compliance = evaluate_compliance(bundle.config, bundle.kpis)
    fin = evaluate_financial(bundle.config, bundle.kpis, compliance, bundle.dispatch)
    if discom_cache is not None:
        fin["incremental"] = incremental_vs_discom(fin, discom_cache)
        # Recompute incremental NPV with project discount
        disc = float(v(base_config, "financial.discount_rate_pct")) / 100.0
        cfs = fin["incremental"]["cashflows_inr"]
        fin["incremental"]["npv_inr"] = float(sum(cf / ((1 + disc) ** t) for t, cf in enumerate(cfs)))
        fin["npv_inr"] = fin["incremental"]["npv_inr"]
        fin["npv_cr"] = fin["npv_inr"] / 1e7
        fin["irr_pct"] = fin["incremental"]["irr_pct"]
        fin["payback_years"] = fin["incremental"]["payback_years"]
    feasible, reasons = _feasible(base_config, bundle.kpis, compliance)
    return {
        "candidate": candidate,
        "kpis": bundle.kpis,
        "compliance": compliance,
        "financial": fin,
        "feasible": feasible,
        "binding_constraints": reasons,
        "monthly": bundle.monthly,
        "validation": bundle.validation,
        "_bundle": bundle,
    }


def run_optimization(
    config: dict,
    progress_cb: Callable[[dict], None] | None = None,
    cancel_cb: Callable[[], bool] | None = None,
    project_id: int | None = None,
) -> dict:
    cfg = deepcopy(config)
    structure = str(v(cfg, "commercial.structure"))
    mode = str(v(cfg, "optimization.search_mode"))
    objective = str(v(cfg, "optimization.objective"))
    candidates = _candidate_set(cfg, mode)

    # DISCOM baseline for incremental economics
    discom_bundle = run_simulation(cfg, structure="DISCOM", skip_validation=True, project_id=project_id)
    discom_comp = evaluate_compliance(discom_bundle.config, discom_bundle.kpis)
    discom_fin = evaluate_financial(discom_bundle.config, discom_bundle.kpis, discom_comp, discom_bundle.dispatch)

    results = []
    best_cost = None
    t0 = time.time()
    for i, cand in enumerate(candidates, start=1):
        if cancel_cb and cancel_cb():
            return {
                "status": "cancelled",
                "iterations": i - 1,
                "candidates_evaluated": i - 1,
                "feasible_solutions": [r for r in results if r["feasible"]],
                "top_solutions": [],
                "elapsed_sec": time.time() - t0,
            }
        try:
            # Force rule-based during screening for speed unless user chose LP and Quick is false
            run_cfg = deepcopy(cfg)
            if mode != "Thorough":
                run_cfg["optimization"]["dispatch_mode"]["value"] = "Rule-Based"
            row = evaluate_candidate(run_cfg, cand, structure, discom_fin, project_id=project_id)
        except Exception as exc:  # noqa: BLE001
            row = {
                "candidate": cand,
                "feasible": False,
                "binding_constraints": [f"Evaluation error: {exc}"],
                "kpis": {},
                "compliance": {},
                "financial": {"cost_per_kwh": 1e9},
            }
        results.append(row)
        if row.get("feasible") and row.get("financial"):
            c = float(row["financial"]["cost_per_kwh"])
            if best_cost is None or c < best_cost:
                best_cost = c
        if progress_cb:
            progress_cb(
                {
                    "status": "running",
                    "iteration": i,
                    "total": len(candidates),
                    "best_cost_per_kwh": best_cost,
                    "feasible_count": sum(1 for r in results if r.get("feasible")),
                    "scenario": structure,
                }
            )

    feasible = [r for r in results if r.get("feasible")]
    feasible.sort(key=lambda r: _score(objective, r["financial"], r["kpis"], r["compliance"], cfg))

    # Local neighborhood refinement around top 3
    refined = []
    for base in feasible[:3]:
        c0 = base["candidate"]
        neighbors = []
        for ds in (-float(v(cfg, "optimization.solar_step_mw")), 0.0, float(v(cfg, "optimization.solar_step_mw"))):
            for dw in (-float(v(cfg, "optimization.wind_step_mw")), 0.0, float(v(cfg, "optimization.wind_step_mw"))):
                neighbors.append(
                    {
                        "solar_mw": min(max(0.0, c0["solar_mw"] + ds), float(v(cfg, "optimization.solar_max_mw"))),
                        "wind_mw": min(max(0.0, c0["wind_mw"] + dw), float(v(cfg, "optimization.wind_max_mw"))),
                        "bess_mw": c0["bess_mw"],
                        "bess_mwh": c0["bess_mwh"],
                        "grid_mw": c0["grid_mw"],
                    }
                )
        for cand in neighbors:
            if cancel_cb and cancel_cb():
                break
            try:
                row = evaluate_candidate(cfg, cand, structure, discom_fin, project_id=project_id)
                refined.append(row)
            except Exception:  # noqa: BLE001
                continue

    all_feas = [r for r in (feasible + refined) if r.get("feasible")]
    # Deduplicate by candidate
    uniq = {}
    for r in all_feas:
        key = tuple(round(r["candidate"][k], 3) for k in ("solar_mw", "wind_mw", "bess_mw", "bess_mwh", "grid_mw"))
        score = _score(objective, r["financial"], r["kpis"], r["compliance"], cfg)
        if key not in uniq or score < uniq[key][0]:
            uniq[key] = (score, r)
    ranked = [x[1] for x in sorted(uniq.values(), key=lambda z: z[0])]
    top = ranked[:10]

    # Strip heavy bundles
    def slim(r):
        out = {k: v_ for k, v_ in r.items() if k != "_bundle"}
        return out

    top_slim = [slim(r) for r in top]
    winner = top_slim[0] if top_slim else None

    no_feas_reasons = [
        "RE target too high",
        "CFE target too high",
        "BESS capacity insufficient",
        "Renewable capacity limit insufficient",
        "Grid capacity insufficient",
        "Compliance constraint impossible",
        "Commercial structure constraints",
    ]
    binding = []
    if not winner:
        # Aggregate most common binding constraints
        from collections import Counter

        c = Counter()
        for r in results:
            for b in r.get("binding_constraints") or []:
                c[b] += 1
        binding = [k for k, _ in c.most_common(5)] or no_feas_reasons

    recommendation = None
    explanation = None
    no_feasible_detail = None
    if winner:
        # Final winner already evaluated via full 8,760 run_simulation in evaluate_candidate
        from backend.optimization.explain import explain_winner

        nearby = [slim(r) for r in results if r is not winner][:8]
        explanation = explain_winner(winner, rejected_nearby=nearby)
        recommendation = {
            "architecture": structure,
            "solar_mw": winner["candidate"]["solar_mw"],
            "wind_mw": winner["candidate"]["wind_mw"],
            "bess_mw": winner["candidate"]["bess_mw"],
            "bess_mwh": winner["candidate"]["bess_mwh"],
            "grid_mw": winner["candidate"]["grid_mw"],
            "annual_re_pct": winner["kpis"]["annual_re_pct"],
            "hourly_cfe_pct": winner["kpis"]["hourly_cfe_min_pct"],
            "cost_per_kwh": winner["financial"]["cost_per_kwh"],
            "label": "RECOMMENDED" if winner.get("feasible") else "NOT RECOMMENDED",
            "full_8760_validated": True,
            "why": explanation["why_selected"] + " " + " ".join(explanation["bullets"][:2]),
            "explanation": explanation,
        }
    else:
        from collections import Counter

        from backend.compliance.feasibility import explain_no_feasible

        c = Counter()
        for r in results:
            for b in r.get("binding_constraints") or []:
                c[b] += 1
        binding = [k for k, _ in c.most_common(5)] or no_feas_reasons
        no_feasible_detail = explain_no_feasible(cfg, results, dict(c))

    return {
        "status": "completed" if winner else "no_feasible",
        "objective": objective,
        "structure": structure,
        "iterations": len(results) + len(refined),
        "candidates_evaluated": len(results) + len(refined),
        "feasible_count": len(ranked),
        "best_cost_per_kwh": winner["financial"]["cost_per_kwh"] if winner else None,
        "top_solutions": top_slim,
        "winner": winner,
        "recommendation": recommendation,
        "explanation": explanation,
        "binding_constraints": binding if not winner else [],
        "no_feasible_detail": no_feasible_detail,
        "no_feasible_message": None
        if winner
        else (no_feasible_detail or {}).get("message")
        or (
            "NO FEASIBLE SOLUTION. Likely binding constraints: "
            + "; ".join(binding)
            + ". Try relaxing targets, increasing capacity bounds, or switching search mode to Thorough."
        ),
        "elapsed_sec": time.time() - t0,
        "search_mode": mode,
        "full_8760_per_candidate": True,
        "discom_baseline_cost_per_kwh": discom_fin["cost_per_kwh"],
    }
