"""Full energy ledger: annual / monthly flows with reconciliation."""

from __future__ import annotations

from typing import Any

import numpy as np

from backend.simulation.calendar import MONTH_NAMES, month_slices
from backend.simulation.dispatch import DispatchResult


TOL_MWH = 1e-3  # annual/monthly energy balance tolerance (MWh)


def _sum(a: np.ndarray | None) -> float:
    if a is None:
        return 0.0
    return float(np.asarray(a, dtype=float).sum())


def _slice_sum(a: np.ndarray | None, start: int, end: int) -> float:
    if a is None:
        return 0.0
    return float(np.asarray(a, dtype=float)[start:end].sum())


def _flows_from_dispatch(d: DispatchResult, start: int = 0, end: int | None = None) -> dict[str, float]:
    """Aggregate energy flows over [start, end) hours (MWh ≡ MW·h at hourly resolution)."""
    n = len(d.load_mw)
    end = n if end is None else end

    solar = _slice_sum(d.solar_mw, start, end)
    wind = _slice_sum(d.wind_mw, start, end)
    load = _slice_sum(d.load_mw, start, end)

    solar_to_load = _slice_sum(getattr(d, "solar_to_load_mw", None), start, end)
    wind_to_load = _slice_sum(getattr(d, "wind_to_load_mw", None), start, end)
    # Fallback if older dispatch without splits
    if solar_to_load == 0.0 and wind_to_load == 0.0 and _slice_sum(d.direct_re_mw, start, end) > 0:
        direct = _slice_sum(d.direct_re_mw, start, end)
        gen = solar + wind
        if gen > 1e-12:
            solar_to_load = direct * (solar / gen)
            wind_to_load = direct * (wind / gen)
        else:
            solar_to_load = wind_to_load = 0.0

    solar_to_bess = _slice_sum(getattr(d, "solar_to_bess_mw", None), start, end)
    wind_to_bess = _slice_sum(getattr(d, "wind_to_bess_mw", None), start, end)
    if solar_to_bess == 0.0 and wind_to_bess == 0.0:
        ch_re = _slice_sum(d.charge_from_re_mw, start, end)
        leftover_s = max(0.0, solar - solar_to_load)
        leftover_w = max(0.0, wind - wind_to_load)
        leftover = leftover_s + leftover_w
        if leftover > 1e-12 and ch_re > 0:
            solar_to_bess = ch_re * leftover_s / leftover
            wind_to_bess = ch_re * leftover_w / leftover

    solar_curtail = _slice_sum(getattr(d, "solar_curtailment_mw", None), start, end)
    wind_curtail = _slice_sum(getattr(d, "wind_curtailment_mw", None), start, end)
    if solar_curtail == 0.0 and wind_curtail == 0.0:
        # Residual after load + BESS charge
        solar_curtail = max(0.0, solar - solar_to_load - solar_to_bess)
        wind_curtail = max(0.0, wind - wind_to_load - wind_to_bess)

    solar_from_bess = _slice_sum(getattr(d, "solar_from_bess_mw", None), start, end)
    wind_from_bess = _slice_sum(getattr(d, "wind_from_bess_mw", None), start, end)
    grid_from_bess = _slice_sum(getattr(d, "grid_from_bess_mw", None), start, end)
    re_from_bess = _slice_sum(d.re_from_bess_mw, start, end)
    discharge = _slice_sum(d.discharge_mw, start, end)
    if solar_from_bess == 0.0 and wind_from_bess == 0.0 and grid_from_bess == 0.0:
        # Split RE-origin discharge by solar/wind charge shares in window; grid-origin = rest
        grid_from_bess = max(0.0, discharge - re_from_bess)
        ch_s = solar_to_bess
        ch_w = wind_to_bess
        ch_re = ch_s + ch_w
        if ch_re > 1e-12:
            solar_from_bess = re_from_bess * ch_s / ch_re
            wind_from_bess = re_from_bess * ch_w / ch_re
        else:
            solar_from_bess = re_from_bess
            wind_from_bess = 0.0

    charge_re = _slice_sum(d.charge_from_re_mw, start, end)
    charge_grid = _slice_sum(d.charge_from_grid_mw, start, end)
    grid_total = _slice_sum(d.grid_mw, start, end)
    grid_to_bess = charge_grid
    grid_to_load = max(0.0, grid_total - grid_to_bess)

    unserved = _slice_sum(d.unserved_mw, start, end)
    curtail_total = _slice_sum(d.curtailment_mw, start, end)

    eta_c = float(d.meta.get("eta_c") or 1.0)
    eta_d = float(d.meta.get("eta_d") or 1.0)
    # AC charge in → DC store: loss = charge * (1 - η_c)
    # DC out → AC discharge: loss = discharge * (1/η_d - 1)
    bess_charge_loss = charge_re * (1.0 - eta_c) + charge_grid * (1.0 - eta_c)
    bess_discharge_loss = discharge * (1.0 / max(eta_d, 1e-9) - 1.0) if discharge > 0 else 0.0
    bess_losses = bess_charge_loss + bess_discharge_loss

    direct_re = solar_to_load + wind_to_load
    bess_to_load = discharge  # AC discharge serving load (by construction)
    load_served = load - unserved

    return {
        "solar_generation_mwh": solar,
        "solar_to_load_mwh": solar_to_load,
        "solar_to_bess_mwh": solar_to_bess,
        "solar_curtailment_mwh": solar_curtail,
        "wind_generation_mwh": wind,
        "wind_to_load_mwh": wind_to_load,
        "wind_to_bess_mwh": wind_to_bess,
        "wind_curtailment_mwh": wind_curtail,
        "bess_charge_from_solar_mwh": solar_to_bess,
        "bess_charge_from_wind_mwh": wind_to_bess,
        "bess_charge_from_grid_mwh": grid_to_bess,
        "bess_charge_total_mwh": charge_re + charge_grid,
        "bess_discharge_total_mwh": discharge,
        "bess_solar_origin_to_load_mwh": solar_from_bess,
        "bess_wind_origin_to_load_mwh": wind_from_bess,
        "bess_grid_origin_to_load_mwh": grid_from_bess,
        "bess_losses_mwh": bess_losses,
        "grid_to_load_mwh": grid_to_load,
        "grid_to_bess_mwh": grid_to_bess,
        "grid_import_total_mwh": grid_total,
        "load_mwh": load,
        "load_served_mwh": load_served,
        "load_from_direct_re_mwh": direct_re,
        "load_from_bess_mwh": bess_to_load,
        "load_from_grid_mwh": grid_to_load,
        "unserved_mwh": unserved,
        "curtailment_solar_mwh": solar_curtail,
        "curtailment_wind_mwh": wind_curtail,
        "curtailment_total_mwh": curtail_total,
    }


def _reconcile(flows: dict[str, float]) -> dict[str, Any]:
    """
    Generation identity (solar):
      solar = solar→load + solar→BESS + solar curtail
    Same for wind.
    Load identity:
      load = direct RE + BESS discharge + grid→load + unserved
    Supply-side check (AC bus):
      solar + wind + discharge + grid_import + unserved
        ≈ load + charge_total + curtail_total
    (BESS losses appear inside SOC path, not the AC equality used by dispatch.)
    """
    solar_lhs = flows["solar_generation_mwh"]
    solar_rhs = (
        flows["solar_to_load_mwh"]
        + flows["solar_to_bess_mwh"]
        + flows["solar_curtailment_mwh"]
    )
    wind_lhs = flows["wind_generation_mwh"]
    wind_rhs = (
        flows["wind_to_load_mwh"]
        + flows["wind_to_bess_mwh"]
        + flows["wind_curtailment_mwh"]
    )
    load_lhs = flows["load_mwh"]
    load_rhs = (
        flows["load_from_direct_re_mwh"]
        + flows["load_from_bess_mwh"]
        + flows["load_from_grid_mwh"]
        + flows["unserved_mwh"]
    )
    # AC power balance aggregate (matches dispatch bal_err definition)
    supply = (
        flows["solar_generation_mwh"]
        + flows["wind_generation_mwh"]
        + flows["bess_discharge_total_mwh"]
        + flows["grid_import_total_mwh"]
        + flows["unserved_mwh"]
    )
    demand = (
        flows["load_mwh"]
        + flows["bess_charge_total_mwh"]
        + flows["curtailment_total_mwh"]
    )

    checks = {
        "solar_identity_gap_mwh": solar_lhs - solar_rhs,
        "wind_identity_gap_mwh": wind_lhs - wind_rhs,
        "load_identity_gap_mwh": load_lhs - load_rhs,
        "ac_balance_gap_mwh": supply - demand,
    }
    ok = all(abs(g) <= TOL_MWH for g in checks.values())
    return {
        "ok": ok,
        "tolerance_mwh": TOL_MWH,
        **checks,
        "status": "OK" if ok else "MODEL ERROR: ENERGY BALANCE",
    }


def build_energy_ledger(d: DispatchResult) -> dict[str, Any]:
    annual = _flows_from_dispatch(d)
    annual_rec = _reconcile(annual)
    months = []
    n = len(d.load_mw)
    for i, (a, b) in enumerate(month_slices(n)):
        flows = _flows_from_dispatch(d, a, b)
        rec = _reconcile(flows)
        months.append(
            {
                "month": MONTH_NAMES[i],
                "month_index": i + 1,
                "flows": flows,
                "reconciliation": rec,
            }
        )
    monthly_ok = all(m["reconciliation"]["ok"] for m in months)
    return {
        "annual": {"flows": annual, "reconciliation": annual_rec},
        "monthly": months,
        "energy_balance_ok": bool(annual_rec["ok"] and monthly_ok),
        "definitions": {
            "bess_utilization_pct": (
                "min(100, (Σ discharge_mwh / bess_energy_mwh) / 365 × 100) — "
                "equivalent full cycles per year as % of 1 cycle/day."
            ),
            "bess_losses_mwh": (
                "Conversion losses are modelled as zero (ideal charge/discharge at BESS power rating)."
            ),
            "ac_balance": (
                "solar+wind+discharge+grid+unserved = load+charge+curtail (hourly MW identity)."
            ),
        },
    }
