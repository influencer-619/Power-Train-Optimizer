"""24×7 CFE analytics: hourly formula + daily / monthly / annual performance."""

from __future__ import annotations

from typing import Any

import numpy as np

from backend.simulation.calendar import MONTH_NAMES, get_calendar
from config.defaults import v


CFE_FORMULA = (
    "Hourly CFE% = Min(Hourly Load, Hourly Carbon-Free Supply) ÷ Hourly Load × 100. "
    "Carbon-Free Supply = Solar_available + Wind_available + RE-origin BESS discharge "
    "(TOD/availability shapes; solar ≈ 0 at night). Architecture mix % sets annual contract "
    "energy and the bill — not a flat firm CF every hour."
)


def _flag(config: dict, dotted: str, default: bool = True) -> bool:
    try:
        return bool(v(config, dotted))
    except Exception:
        return default


def _mix_pct(config: dict, key: str, included: bool) -> float:
    if not included:
        return 0.0
    try:
        return max(0.0, min(100.0, float(v(config, f"commercial.{key}"))))
    except Exception:
        return 0.0


def architecture_cf_fraction(config: dict) -> float:
    """Contracted Architecture RE mix as a fraction of load (0–1) — bill / reporting only.

    Not used for hourly CFE (which follows TOD/availability). DISCOM is not CF.
    """
    solar = _mix_pct(config, "mix_solar_pct", _flag(config, "commercial.include_solar", True))
    wind = _mix_pct(config, "mix_wind_pct", _flag(config, "commercial.include_wind", True))
    bess = _mix_pct(config, "mix_bess_pct", _flag(config, "commercial.include_bess", True))
    return max(0.0, min(1.0, (solar + wind + bess) / 100.0))


def compute_hourly_cfe_pct(
    load_mw: np.ndarray,
    *,
    solar_mw: np.ndarray | None = None,
    wind_mw: np.ndarray | None = None,
    hydro_mw: np.ndarray | None = None,
    nuclear_mw: np.ndarray | None = None,
    bess_cf_discharge_mw: np.ndarray | None = None,
    cf_fraction: float | None = None,
    config: dict | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (hourly_cfe_pct, cf_supply_mw, matched_cf_mw).

    Prefer availability streams (Solar + Wind + RE-origin BESS, …).
    ``cf_fraction`` is an optional flat override for unit tests only — not the product path.
    ``config`` alone does not force firm mix; use architecture_cf_fraction for contracted mix %.
    """
    load = np.asarray(load_mw, dtype=float)
    n = len(load)
    load_pos = np.maximum(load, 0.0)

    def _arr(x) -> np.ndarray:
        if x is None:
            return np.zeros(n, dtype=float)
        a = np.asarray(x, dtype=float)
        if len(a) != n:
            out = np.zeros(n, dtype=float)
            m = min(n, len(a))
            out[:m] = a[:m]
            return out
        return a

    has_streams = any(
        x is not None
        for x in (solar_mw, wind_mw, hydro_mw, nuclear_mw, bess_cf_discharge_mw)
    )

    if has_streams:
        solar = np.maximum(0.0, _arr(solar_mw))
        wind = np.maximum(0.0, _arr(wind_mw))
        hydro = np.maximum(0.0, _arr(hydro_mw))
        nuclear = np.maximum(0.0, _arr(nuclear_mw))
        bess_cf = np.maximum(0.0, _arr(bess_cf_discharge_mw))

        cf_supply = solar + wind + hydro + nuclear + bess_cf
        matched = np.minimum(load_pos, cf_supply)
        cfe = np.full(n, 100.0, dtype=float)
        np.divide(matched, load, out=cfe, where=load > 1e-9)
        cfe = np.where(load > 1e-9, cfe * 100.0, 100.0)
        cfe = np.clip(cfe, 0.0, 100.0)
        return cfe, cf_supply, matched

    # Flat fraction override (tests / explicit callers only)
    frac = cf_fraction
    if frac is None and config is not None and not has_streams:
        # No streams provided: do not invent firm mix from Architecture % for CFE.
        # Return zeros so callers must pass availability series.
        cf_supply = np.zeros(n, dtype=float)
        matched = np.zeros(n, dtype=float)
        cfe = np.where(load > 1e-9, 0.0, 100.0)
        return cfe, cf_supply, matched

    if frac is not None:
        f = max(0.0, min(1.0, float(frac)))
        cf_supply = load_pos * f
        matched = np.minimum(load_pos, cf_supply)
        cfe = np.full(n, 100.0, dtype=float)
        np.divide(matched, load, out=cfe, where=load > 1e-9)
        cfe = np.where(load > 1e-9, cfe * 100.0, 100.0)
        return np.clip(cfe, 0.0, 100.0), cf_supply, matched

    cf_supply = np.zeros(n, dtype=float)
    matched = np.zeros(n, dtype=float)
    cfe = np.where(load > 1e-9, 0.0, 100.0)
    return cfe, cf_supply, matched


def analyze_cfe(
    config: dict,
    hourly_cfe_pct: np.ndarray,
    annual_re_pct: float | None = None,
    *,
    load_mw: np.ndarray | None = None,
    cf_supply_mw: np.ndarray | None = None,
    matched_cf_mw: np.ndarray | None = None,
) -> dict[str, Any]:
    cfe = np.asarray(hourly_cfe_pct, dtype=float)
    n = len(cfe)
    target = float(v(config, "compliance.hourly_cfe_target_pct"))
    # Pass/fail is always vs the CFE formula (every hour ≥ target)
    mode = "CFE formula (all hours ≥ target)"

    if n == 0:
        return {
            "pass_mode": mode,
            "target_pct": target,
            "hours": 0,
            "formula": CFE_FORMULA,
        }

    load = np.asarray(load_mw, dtype=float) if load_mw is not None else None
    matched = np.asarray(matched_cf_mw, dtype=float) if matched_cf_mw is not None else None
    supply = np.asarray(cf_supply_mw, dtype=float) if cf_supply_mw is not None else None

    if load is not None and matched is None and supply is not None and len(load) == n and len(supply) == n:
        matched = np.minimum(np.maximum(load, 0.0), np.maximum(supply, 0.0))

    # Energy-weighted annual CFE (preferred) = Σ matched / Σ load
    if load is not None and matched is not None and len(load) == n and float(load.sum()) > 1e-9:
        annual_cfe = float(matched.sum() / load.sum() * 100.0)
        annual_def = "Energy-weighted CFE = Σ Min(Load, CF supply) / Σ Load × 100"
    elif annual_re_pct is not None:
        annual_cfe = float(annual_re_pct)
        annual_def = "Fallback: Annual RE % (matched CF series unavailable)"
    else:
        annual_cfe = float(np.mean(cfe))
        annual_def = "Fallback: unweighted mean of hourly CFE %"

    meet = cfe >= target - 1e-12
    hours_meet = int(np.sum(meet))
    hours_below = n - hours_meet
    pct_meet = hours_meet / n * 100.0
    deficit = np.maximum(0.0, target - cfe)

    longest = 0
    cur = 0
    for ok in meet:
        if not ok:
            cur += 1
            longest = max(longest, cur)
        else:
            cur = 0

    sorted_desc = np.sort(cfe)[::-1]
    xs = np.linspace(0, 100, 101)
    idxs = np.clip((xs / 100.0 * (n - 1)).astype(int), 0, n - 1)
    duration_curve = [
        {"percentile_hours": float(xs[i]), "cfe_pct": float(sorted_desc[idxs[i]])} for i in range(len(xs))
    ]

    # Pass = every hour’s formula CFE% meets the target
    passed = hours_meet >= n
    actual_for_pass = float(np.min(cfe))

    # Calendar for daily / monthly / hour-of-day summaries
    try:
        sm = int(v(config, "general.study_start_month"))
        em = int(v(config, "general.study_end_month"))
        cal = get_calendar(start_month=sm, end_month=em)
        if cal.hours != n:
            cal = get_calendar(n)
    except Exception:
        cal = get_calendar(n)

    hourly_of_day = _hourly_of_day_summary(cfe, cal.hour_of_day, load, matched, target)
    daily = _daily_summary(cfe, cal.day_of_year, load, matched, target)
    monthly = _monthly_summary(cfe, cal.month, load, matched, target)

    return {
        "formula": CFE_FORMULA,
        "pass_mode": mode,
        "target_pct": target,
        "passed": bool(passed),
        "actual_for_pass_mode_pct": actual_for_pass,
        "annual_cfe_pct": annual_cfe,
        "annual_cfe_definition": annual_def,
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
        "architecture_cf_pct": float(architecture_cf_fraction(config) * 100.0),
        "duration_curve": duration_curve,
        "performance": {
            "hourly_of_day": hourly_of_day,
            "daily": daily,
            "monthly": monthly,
            "annual": {
                "cfe_pct": annual_cfe,
                "mean_hourly_cfe_pct": float(np.mean(cfe)),
                "min_hourly_cfe_pct": float(np.min(cfe)),
                "hours_ge_target_pct": pct_meet,
                "load_mwh": float(load.sum()) if load is not None and len(load) == n else None,
                "matched_cf_mwh": float(matched.sum()) if matched is not None and len(matched) == n else None,
                "cf_supply_mwh": float(supply.sum()) if supply is not None and len(supply) == n else None,
            },
        },
    }


def _block_stats(
    cfe_slice: np.ndarray,
    load_slice: np.ndarray | None,
    matched_slice: np.ndarray | None,
    target: float,
) -> dict[str, float]:
    if len(cfe_slice) == 0:
        return {
            "mean_cfe_pct": 0.0,
            "min_cfe_pct": 0.0,
            "energy_weighted_cfe_pct": 0.0,
            "hours_ge_target_pct": 0.0,
            "hours": 0,
        }
    ew = float(np.mean(cfe_slice))
    if (
        load_slice is not None
        and matched_slice is not None
        and len(load_slice) == len(cfe_slice)
        and float(load_slice.sum()) > 1e-9
    ):
        ew = float(matched_slice.sum() / load_slice.sum() * 100.0)
    return {
        "mean_cfe_pct": float(np.mean(cfe_slice)),
        "min_cfe_pct": float(np.min(cfe_slice)),
        "energy_weighted_cfe_pct": ew,
        "hours_ge_target_pct": float(np.mean(cfe_slice >= target - 1e-12) * 100.0),
        "hours": int(len(cfe_slice)),
    }


def _hourly_of_day_summary(
    cfe: np.ndarray,
    hod: np.ndarray,
    load: np.ndarray | None,
    matched: np.ndarray | None,
    target: float,
) -> list[dict[str, Any]]:
    rows = []
    for h in range(24):
        mask = hod == h
        if not np.any(mask):
            continue
        stats = _block_stats(
            cfe[mask],
            load[mask] if load is not None else None,
            matched[mask] if matched is not None else None,
            target,
        )
        rows.append({"hour": h, **stats})
    return rows


def _daily_summary(
    cfe: np.ndarray,
    doy: np.ndarray,
    load: np.ndarray | None,
    matched: np.ndarray | None,
    target: float,
) -> list[dict[str, Any]]:
    rows = []
    for day in sorted(set(int(x) for x in doy)):
        mask = doy == day
        stats = _block_stats(
            cfe[mask],
            load[mask] if load is not None else None,
            matched[mask] if matched is not None else None,
            target,
        )
        rows.append({"day_of_year": int(day) + 1, **stats})  # 1-indexed display
    return rows


def _monthly_summary(
    cfe: np.ndarray,
    month: np.ndarray,
    load: np.ndarray | None,
    matched: np.ndarray | None,
    target: float,
) -> list[dict[str, Any]]:
    rows = []
    for m in range(12):
        mask = month == m
        if not np.any(mask):
            continue
        stats = _block_stats(
            cfe[mask],
            load[mask] if load is not None else None,
            matched[mask] if matched is not None else None,
            target,
        )
        rows.append(
            {
                "month_index": m + 1,
                "month": MONTH_NAMES[m],
                **stats,
            }
        )
    return rows
