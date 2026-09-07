"""CFE analytics: duration curve, deficit streaks, pass-mode visibility."""

from __future__ import annotations

from typing import Any

import numpy as np

from config.defaults import v


def analyze_cfe(config: dict, hourly_cfe_pct: np.ndarray, annual_re_pct: float) -> dict[str, Any]:
    cfe = np.asarray(hourly_cfe_pct, dtype=float)
    n = len(cfe)
    target = float(v(config, "compliance.hourly_cfe_target_pct"))
    mode = str(v(config, "compliance.cfe_pass_mode"))
    share_target = float(v(config, "compliance.cfe_hour_share_target_pct"))

    if n == 0:
        return {"pass_mode": mode, "target_pct": target, "hours": 0}

    meet = cfe >= target - 1e-12
    hours_meet = int(np.sum(meet))
    hours_below = n - hours_meet
    pct_meet = hours_meet / n * 100.0
    deficit = np.maximum(0.0, target - cfe)

    # Longest continuous hours below target
    longest = 0
    cur = 0
    for ok in meet:
        if not ok:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0

    # Duration curve: CFE sorted descending
    sorted_desc = np.sort(cfe)[::-1]
    # Sample 101 points for charts
    xs = np.linspace(0, 100, 101)
    idxs = np.clip((xs / 100.0 * (n - 1)).astype(int), 0, n - 1)
    duration_curve = [{"percentile_hours": float(xs[i]), "cfe_pct": float(sorted_desc[idxs[i]])} for i in range(len(xs))]

    if mode == "All hours >= target":
        passed = hours_meet >= n
        actual_for_pass = float(np.min(cfe))
    elif mode == "Mean hourly CFE >= target":
        passed = float(np.mean(cfe)) >= target - 1e-9
        actual_for_pass = float(np.mean(cfe))
    else:
        passed = pct_meet >= share_target - 1e-9
        actual_for_pass = pct_meet

    return {
        "pass_mode": mode,
        "target_pct": target,
        "share_target_pct": share_target,
        "passed": bool(passed),
        "actual_for_pass_mode_pct": actual_for_pass,
        "annual_cfe_pct": float(annual_re_pct),  # energy-weighted CFE ≡ annual RE in this model
        "annual_cfe_definition": "Energy-weighted CFE = Σ RE_serving_load / Σ Load × 100 (= Annual RE %)",
        "min_hourly_cfe_pct": float(np.min(cfe)),
        "mean_hourly_cfe_pct": float(np.mean(cfe)),
        "median_hourly_cfe_pct": float(np.median(cfe)),
        "p95_hourly_cfe_pct": float(np.percentile(cfe, 95)),
        "hours_total": n,
        "hours_ge_target": hours_meet,
        "hours_lt_target": hours_below,
        "pct_hours_ge_target": pct_meet,
        "longest_continuous_deficit_hours": int(longest),
        "max_cfe_deficit_pp": float(np.max(deficit)) if n else 0.0,
        "mean_cfe_deficit_pp": float(np.mean(deficit[deficit > 0])) if np.any(deficit > 0) else 0.0,
        "duration_curve": duration_curve,
    }
