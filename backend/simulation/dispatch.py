"""Hourly rule-based and LP energy dispatch with renewable-origin tracking."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from config.defaults import v, v_opt


@dataclass
class DispatchResult:
    load_mw: np.ndarray
    solar_mw: np.ndarray
    wind_mw: np.ndarray
    charge_mw: np.ndarray
    discharge_mw: np.ndarray
    grid_mw: np.ndarray
    curtailment_mw: np.ndarray
    unserved_mw: np.ndarray
    soc_mwh: np.ndarray
    re_origin_soc_mwh: np.ndarray
    grid_origin_soc_mwh: np.ndarray
    direct_re_mw: np.ndarray
    re_from_bess_mw: np.ndarray
    re_serving_load_mw: np.ndarray
    hourly_cfe_pct: np.ndarray
    charge_from_re_mw: np.ndarray
    charge_from_grid_mw: np.ndarray
    balance_error_mw: np.ndarray
    # Explicit ledger flows (Phase 1)
    solar_to_load_mw: np.ndarray = field(default_factory=lambda: np.zeros(0))
    wind_to_load_mw: np.ndarray = field(default_factory=lambda: np.zeros(0))
    solar_to_bess_mw: np.ndarray = field(default_factory=lambda: np.zeros(0))
    wind_to_bess_mw: np.ndarray = field(default_factory=lambda: np.zeros(0))
    solar_curtailment_mw: np.ndarray = field(default_factory=lambda: np.zeros(0))
    wind_curtailment_mw: np.ndarray = field(default_factory=lambda: np.zeros(0))
    solar_from_bess_mw: np.ndarray = field(default_factory=lambda: np.zeros(0))
    wind_from_bess_mw: np.ndarray = field(default_factory=lambda: np.zeros(0))
    grid_from_bess_mw: np.ndarray = field(default_factory=lambda: np.zeros(0))
    solar_origin_soc_mwh: np.ndarray = field(default_factory=lambda: np.zeros(0))
    wind_origin_soc_mwh: np.ndarray = field(default_factory=lambda: np.zeros(0))
    cf_supply_mw: np.ndarray = field(default_factory=lambda: np.zeros(0))
    matched_cf_mw: np.ndarray = field(default_factory=lambda: np.zeros(0))
    hydro_mw: np.ndarray = field(default_factory=lambda: np.zeros(0))
    nuclear_mw: np.ndarray = field(default_factory=lambda: np.zeros(0))
    meta: dict = field(default_factory=dict)


def _tariff_series(config: dict, hours: int, hod: np.ndarray) -> np.ndarray:
    if bool(v(config, "grid.use_tod")):
        start = int(v(config, "grid.tod_peak_start_hour"))
        end = int(v(config, "grid.tod_peak_end_hour"))
        peak = float(v(config, "grid.tod_peak_tariff"))
        off = float(v(config, "grid.tod_offpeak_tariff"))
        if start < end:
            mask = (hod >= start) & (hod < end)
        else:
            mask = (hod >= start) | (hod < end)
        return np.where(mask, peak, off).astype(float)
    return np.full(hours, float(v(config, "grid.energy_tariff_inr_per_kwh")), dtype=float)


def rule_based_dispatch(
    config: dict,
    load_mw: np.ndarray,
    solar_mw: np.ndarray,
    wind_mw: np.ndarray,
    hod: np.ndarray,
    bess_power_mw: float | None = None,
    bess_energy_mwh: float | None = None,
    grid_cap_mw: float | None = None,
) -> DispatchResult:
    n = len(load_mw)
    power = float(bess_power_mw if bess_power_mw is not None else v_opt(config, "bess.power_mw", 0.0) or 0.0)
    energy = float(bess_energy_mwh if bess_energy_mwh is not None else v_opt(config, "bess.energy_mwh", 0.0) or 0.0)
    grid_cap = float(grid_cap_mw if grid_cap_mw is not None else v_opt(config, "grid.max_import_mw", 0.0) or 0.0)
    avail = float(v_opt(config, "grid.availability_pct", 100.0) or 100.0) / 100.0
    grid_cap_eff = grid_cap * avail

    soc_min_pct = float(v_opt(config, "bess.min_soc_pct", 10.0) or 10.0) / 100.0
    soc_max_pct = float(v_opt(config, "bess.max_soc_pct", 95.0) or 95.0) / 100.0
    soc0_pct = float(v_opt(config, "bess.initial_soc_pct", 50.0) or 50.0) / 100.0
    try:
        eta_c = max(1e-6, min(1.0, float(v(config, "bess.charge_efficiency_pct")) / 100.0))
    except Exception:
        eta_c = 1.0
    try:
        eta_d = max(1e-6, min(1.0, float(v(config, "bess.discharge_efficiency_pct")) / 100.0))
    except Exception:
        eta_d = 1.0
    max_c = power
    max_d = power
    allow_grid_charge = bool(v_opt(config, "bess.allow_grid_charge", False))

    if energy <= 0 or power <= 0:
        energy = 0.0
        power = 0.0
        max_c = 0.0
        max_d = 0.0

    soc_min = soc_min_pct * energy
    soc_max = soc_max_pct * energy
    soc = float(np.clip(soc0_pct * energy, soc_min, soc_max))
    re_soc = soc  # start as RE-origin by convention (conservative for ESO)
    grid_soc = 0.0
    solar_soc = soc  # entire initial SOC attributed to solar-origin RE bucket
    wind_soc = 0.0

    charge = np.zeros(n)
    discharge = np.zeros(n)
    grid = np.zeros(n)
    curtail = np.zeros(n)
    unserved = np.zeros(n)
    soc_arr = np.zeros(n)
    re_soc_arr = np.zeros(n)
    grid_soc_arr = np.zeros(n)
    solar_soc_arr = np.zeros(n)
    wind_soc_arr = np.zeros(n)
    direct_re = np.zeros(n)
    re_from_bess = np.zeros(n)
    re_serving = np.zeros(n)
    cfe = np.zeros(n)
    ch_re = np.zeros(n)
    ch_grid = np.zeros(n)
    bal_err = np.zeros(n)
    solar_to_load = np.zeros(n)
    wind_to_load = np.zeros(n)
    solar_to_bess = np.zeros(n)
    wind_to_bess = np.zeros(n)
    solar_curtail = np.zeros(n)
    wind_curtail = np.zeros(n)
    solar_from_bess = np.zeros(n)
    wind_from_bess = np.zeros(n)
    grid_from_bess = np.zeros(n)

    for t in range(n):
        load = float(load_mw[t])
        sol = float(solar_mw[t])
        win = float(wind_mw[t])
        re = sol + win

        d_re = min(re, load)
        if re > 1e-12:
            s_share = sol / re
            w_share = win / re
        else:
            s_share = w_share = 0.0
        s_to_load = d_re * s_share
        w_to_load = d_re * w_share
        leftover_s = sol - s_to_load
        leftover_w = win - w_to_load
        leftover_re = leftover_s + leftover_w
        remaining = load - d_re

        # Charge from RE
        headroom = max(0.0, (soc_max - soc) / max(eta_c, 1e-9)) if energy > 0 else 0.0
        c_re = min(leftover_re, max_c, headroom)
        if leftover_re > 1e-12:
            s_to_bess = c_re * leftover_s / leftover_re
            w_to_bess = c_re * leftover_w / leftover_re
        else:
            s_to_bess = w_to_bess = 0.0
        leftover_s -= s_to_bess
        leftover_w -= w_to_bess
        curtail_s = leftover_s
        curtail_w = leftover_w
        curtail_t = curtail_s + curtail_w

        # Discharge to residual load
        energy_avail = max(0.0, soc - soc_min)
        d_max = min(max_d, remaining, energy_avail * eta_d) if energy > 0 else 0.0
        stored_pre = re_soc + grid_soc
        frac_re = re_soc / stored_pre if stored_pre > 1e-12 else 1.0
        frac_solar = solar_soc / stored_pre if stored_pre > 1e-12 else 1.0
        frac_wind = wind_soc / stored_pre if stored_pre > 1e-12 else 0.0
        frac_grid = grid_soc / stored_pre if stored_pre > 1e-12 else 0.0
        re_d = d_max * frac_re
        s_from_bess = d_max * frac_solar
        w_from_bess = d_max * frac_wind
        g_from_bess = d_max * frac_grid
        remaining -= d_max

        # Grid serves residual
        g = min(remaining, grid_cap_eff)
        remaining -= g

        # Optional grid charging (after load is met)
        c_g = 0.0
        if allow_grid_charge and remaining <= 1e-12 and energy > 0:
            headroom2 = max(0.0, (soc_max - (soc + c_re * eta_c)) / max(eta_c, 1e-9))
            room_grid = max(0.0, grid_cap_eff - g)
            c_g = min(max_c - c_re, headroom2, room_grid)
            g += c_g

        unserved_t = max(0.0, remaining)

        # SOC update
        soc = soc + c_re * eta_c + c_g * eta_c - (d_max / max(eta_d, 1e-9) if d_max > 0 else 0.0)
        soc = float(np.clip(soc, soc_min - 1e-9, soc_max + 1e-9))

        solar_soc = solar_soc + s_to_bess * eta_c
        wind_soc = wind_soc + w_to_bess * eta_c
        re_soc = solar_soc + wind_soc
        grid_soc = grid_soc + c_g * eta_c
        if d_max > 0:
            removed = d_max / max(eta_d, 1e-9)
            solar_soc = max(0.0, solar_soc - removed * frac_solar)
            wind_soc = max(0.0, wind_soc - removed * frac_wind)
            grid_soc = max(0.0, grid_soc - removed * frac_grid)
            re_soc = solar_soc + wind_soc
        # renormalize origin buckets to SOC
        stored = re_soc + grid_soc
        if stored > 1e-9 and abs(stored - soc) > 1e-6:
            scale = soc / stored
            solar_soc *= scale
            wind_soc *= scale
            re_soc = solar_soc + wind_soc
            grid_soc *= scale
        elif stored <= 1e-9:
            solar_soc = wind_soc = re_soc = grid_soc = 0.0

        charge[t] = c_re + c_g
        discharge[t] = d_max
        grid[t] = g
        curtail[t] = curtail_t
        unserved[t] = unserved_t
        soc_arr[t] = soc
        re_soc_arr[t] = re_soc
        grid_soc_arr[t] = grid_soc
        solar_soc_arr[t] = solar_soc
        wind_soc_arr[t] = wind_soc
        direct_re[t] = d_re
        re_from_bess[t] = re_d
        re_serving[t] = d_re + re_d
        ch_re[t] = c_re
        ch_grid[t] = c_g
        solar_to_load[t] = s_to_load
        wind_to_load[t] = w_to_load
        solar_to_bess[t] = s_to_bess
        wind_to_bess[t] = w_to_bess
        solar_curtail[t] = curtail_s
        wind_curtail[t] = curtail_w
        solar_from_bess[t] = s_from_bess
        wind_from_bess[t] = w_from_bess
        grid_from_bess[t] = g_from_bess

        supply = sol + win + d_max + g + unserved_t
        demand = load + (c_re + c_g) + curtail_t
        bal_err[t] = supply - demand

    # 24×7 CFE from hourly availability: Solar + Wind + RE-origin BESS discharge
    from backend.compliance.cfe_analytics import CFE_FORMULA, compute_hourly_cfe_pct

    hydro = np.zeros(n, dtype=float)
    nuclear = np.zeros(n, dtype=float)
    cfe, cf_supply, matched_cf = compute_hourly_cfe_pct(
        load_mw,
        solar_mw=solar_mw,
        wind_mw=wind_mw,
        hydro_mw=hydro,
        nuclear_mw=nuclear,
        bess_cf_discharge_mw=re_from_bess,
    )

    # Final SOC should still be physical
    max_abs_err = float(np.max(np.abs(bal_err))) if n else 0.0
    return DispatchResult(
        load_mw=load_mw.astype(float),
        solar_mw=solar_mw.astype(float),
        wind_mw=wind_mw.astype(float),
        charge_mw=charge,
        discharge_mw=discharge,
        grid_mw=grid,
        curtailment_mw=curtail,
        unserved_mw=unserved,
        soc_mwh=soc_arr,
        re_origin_soc_mwh=re_soc_arr,
        grid_origin_soc_mwh=grid_soc_arr,
        direct_re_mw=direct_re,
        re_from_bess_mw=re_from_bess,
        re_serving_load_mw=re_serving,
        hourly_cfe_pct=cfe,
        charge_from_re_mw=ch_re,
        charge_from_grid_mw=ch_grid,
        balance_error_mw=bal_err,
        solar_to_load_mw=solar_to_load,
        wind_to_load_mw=wind_to_load,
        solar_to_bess_mw=solar_to_bess,
        wind_to_bess_mw=wind_to_bess,
        solar_curtailment_mw=solar_curtail,
        wind_curtailment_mw=wind_curtail,
        solar_from_bess_mw=solar_from_bess,
        wind_from_bess_mw=wind_from_bess,
        grid_from_bess_mw=grid_from_bess,
        solar_origin_soc_mwh=solar_soc_arr,
        wind_origin_soc_mwh=wind_soc_arr,
        cf_supply_mw=cf_supply,
        matched_cf_mw=matched_cf,
        hydro_mw=hydro,
        nuclear_mw=nuclear,
        meta={
            "dispatch_mode": "Rule-Based",
            "max_abs_balance_error_mw": max_abs_err,
            "bess_power_mw": power,
            "bess_energy_mwh": energy,
            "grid_cap_mw": grid_cap,
            "grid_cap_effective_mw": grid_cap_eff,
            "eta_c": eta_c,
            "eta_d": eta_d,
            "tariff_inr_per_kwh": _tariff_series(config, n, hod),
            "cfe_formula": CFE_FORMULA,
        },
    )


def lp_dispatch(
    config: dict,
    load_mw: np.ndarray,
    solar_mw: np.ndarray,
    wind_mw: np.ndarray,
    hod: np.ndarray,
    bess_power_mw: float | None = None,
    bess_energy_mwh: float | None = None,
    grid_cap_mw: float | None = None,
) -> DispatchResult:
    """Hourly LP dispatch via SciPy HiGHS when available; falls back to rule-based.

    Decision variables per hour: charge, discharge, grid, curtail.
    Objective: minimise grid energy cost + small curtailment penalty.
    """
    try:
        from scipy.optimize import linprog
    except Exception:
        return rule_based_dispatch(
            config, load_mw, solar_mw, wind_mw, hod, bess_power_mw, bess_energy_mwh, grid_cap_mw
        )

    # Full 8760 LP is large; solve in weekly blocks with SOC carry-over for practicality.
    n = len(load_mw)
    block = 24 * 7
    power = float(bess_power_mw if bess_power_mw is not None else v_opt(config, "bess.power_mw", 0.0) or 0.0)
    energy = float(bess_energy_mwh if bess_energy_mwh is not None else v_opt(config, "bess.energy_mwh", 0.0) or 0.0)
    grid_cap = float(grid_cap_mw if grid_cap_mw is not None else v_opt(config, "grid.max_import_mw", 0.0) or 0.0)
    avail = float(v_opt(config, "grid.availability_pct", 100.0) or 100.0) / 100.0
    grid_cap_eff = grid_cap * avail
    try:
        eta_c = max(1e-6, min(1.0, float(v(config, "bess.charge_efficiency_pct")) / 100.0))
    except Exception:
        eta_c = 1.0
    try:
        eta_d = max(1e-6, min(1.0, float(v(config, "bess.discharge_efficiency_pct")) / 100.0))
    except Exception:
        eta_d = 1.0
    soc_min = float(v_opt(config, "bess.min_soc_pct", 10.0) or 10.0) / 100.0 * energy
    soc_max = float(v_opt(config, "bess.max_soc_pct", 95.0) or 95.0) / 100.0 * energy
    soc = float(np.clip(float(v_opt(config, "bess.initial_soc_pct", 50.0) or 50.0) / 100.0 * energy, soc_min, soc_max))
    tariff = _tariff_series(config, n, hod)

    if energy <= 0 or power <= 0:
        return rule_based_dispatch(
            config, load_mw, solar_mw, wind_mw, hod, bess_power_mw, bess_energy_mwh, grid_cap_mw
        )

    charge = np.zeros(n)
    discharge = np.zeros(n)
    grid = np.zeros(n)
    curtail = np.zeros(n)
    soc_arr = np.zeros(n)

    for start in range(0, n, block):
        end = min(n, start + block)
        m = end - start
        # vars: [charge_0..m-1, discharge_0..m-1, grid_0..m-1, curtail_0..m-1, soc_0..m-1]
        # Use SOC as variables with coupling.
        # Simpler formulation matching rule-based feasibility: use rule-based for reliability
        # if LP fails.
        c = np.concatenate(
            [
                np.zeros(m),
                np.zeros(m),
                tariff[start:end],
                np.full(m, 0.01),
            ]
        )
        bounds = (
            [(0, power)] * m
            + [(0, power)] * m
            + [(0, grid_cap_eff)] * m
            + [(0, None)] * m
        )
        # Equality: solar+wind+discharge+grid = load+charge+curtail
        A_eq = []
        b_eq = []
        for i in range(m):
            row = np.zeros(4 * m)
            row[i] = -1.0  # charge
            row[m + i] = 1.0  # discharge
            row[2 * m + i] = 1.0  # grid
            row[3 * m + i] = -1.0  # curtail
            A_eq.append(row)
            b_eq.append(float(load_mw[start + i] - solar_mw[start + i] - wind_mw[start + i]))
        # SOC inequalities via cumulative charge/discharge
        # soc0 + sum_{k<=i}(eta_c*ch - dis/eta_d) between soc_min and soc_max
        A_ub = []
        b_ub = []
        for i in range(m):
            # upper: soc0 + sum <= soc_max
            row_u = np.zeros(4 * m)
            row_l = np.zeros(4 * m)
            for k in range(i + 1):
                row_u[k] = eta_c
                row_u[m + k] = -1.0 / max(eta_d, 1e-9)
                row_l[k] = -eta_c
                row_l[m + k] = 1.0 / max(eta_d, 1e-9)
            A_ub.append(row_u)
            b_ub.append(soc_max - soc)
            A_ub.append(row_l)
            b_ub.append(-(soc_min - soc))

        try:
            res = linprog(
                c,
                A_ub=np.array(A_ub),
                b_ub=np.array(b_ub),
                A_eq=np.array(A_eq),
                b_eq=np.array(b_eq),
                bounds=bounds,
                method="highs",
                options={"presolve": True, "time_limit": 5.0},
            )
            if not res.success:
                raise RuntimeError(res.message)
            x = res.x
            charge[start:end] = x[0:m]
            discharge[start:end] = x[m : 2 * m]
            grid[start:end] = x[2 * m : 3 * m]
            curtail[start:end] = x[3 * m : 4 * m]
            for i in range(m):
                soc = soc + charge[start + i] * eta_c - discharge[start + i] / max(eta_d, 1e-9)
                soc = float(np.clip(soc, soc_min, soc_max))
                soc_arr[start + i] = soc
        except Exception:
            # Fall back for this block using rule-based and continue SOC
            block_res = rule_based_dispatch(
                config,
                load_mw[start:end],
                solar_mw[start:end],
                wind_mw[start:end],
                hod[start:end],
                power,
                energy,
                grid_cap,
            )
            # Override initial SOC by temporarily patching — approximate by using block result
            charge[start:end] = block_res.charge_mw
            discharge[start:end] = block_res.discharge_mw
            grid[start:end] = block_res.grid_mw
            curtail[start:end] = block_res.curtailment_mw
            soc_arr[start:end] = block_res.soc_mwh
            soc = float(block_res.soc_mwh[-1]) if m else soc

    # Rebuild origin tracking & CFE with a second pass using LP charge/discharge schedules
    # by replaying SOC origin accounting
    unserved = np.zeros(n)
    re_soc = float(np.clip(float(v_opt(config, "bess.initial_soc_pct", 50.0) or 50.0) / 100.0 * energy, soc_min, soc_max))
    grid_soc = 0.0
    soc = re_soc
    direct_re = np.zeros(n)
    re_from_bess = np.zeros(n)
    re_serving = np.zeros(n)
    cfe = np.zeros(n)
    ch_re = np.zeros(n)
    ch_grid = np.zeros(n)
    bal_err = np.zeros(n)
    re_soc_arr = np.zeros(n)
    grid_soc_arr = np.zeros(n)

    for t in range(n):
        load = float(load_mw[t])
        re = float(solar_mw[t] + wind_mw[t])
        c = float(charge[t])
        d = float(discharge[t])
        g = float(grid[t])
        cu = float(curtail[t])
        d_re = min(re, load)
        leftover = re - d_re
        c_re = min(c, leftover)
        c_g = max(0.0, c - c_re)
        frac_re = re_soc / (re_soc + grid_soc) if (re_soc + grid_soc) > 1e-12 else 1.0
        re_d = d * frac_re
        soc = soc + c_re * eta_c + c_g * eta_c - d / max(eta_d, 1e-9)
        re_soc = re_soc + c_re * eta_c
        grid_soc = grid_soc + c_g * eta_c
        if d > 0:
            removed = d / max(eta_d, 1e-9)
            re_soc = max(0.0, re_soc - removed * frac_re)
            grid_soc = max(0.0, grid_soc - removed * (1.0 - frac_re))
        stored = re_soc + grid_soc
        if stored > 1e-9 and abs(stored - soc) > 1e-6:
            re_soc *= soc / stored
            grid_soc *= soc / stored
        remaining = load - d_re - d
        unserved[t] = max(0.0, remaining - g)
        soc_arr[t] = soc
        re_soc_arr[t] = re_soc
        grid_soc_arr[t] = grid_soc
        direct_re[t] = d_re
        re_from_bess[t] = re_d
        re_serving[t] = d_re + re_d
        ch_re[t] = c_re
        ch_grid[t] = c_g
        bal_err[t] = (solar_mw[t] + wind_mw[t] + d + g + unserved[t]) - (load + c + cu)

    from backend.compliance.cfe_analytics import CFE_FORMULA, compute_hourly_cfe_pct

    hydro = np.zeros(n, dtype=float)
    nuclear = np.zeros(n, dtype=float)
    cfe, cf_supply, matched_cf = compute_hourly_cfe_pct(
        load_mw,
        solar_mw=solar_mw,
        wind_mw=wind_mw,
        hydro_mw=hydro,
        nuclear_mw=nuclear,
        bess_cf_discharge_mw=re_from_bess,
    )

    result = DispatchResult(
        load_mw=load_mw.astype(float),
        solar_mw=solar_mw.astype(float),
        wind_mw=wind_mw.astype(float),
        charge_mw=charge,
        discharge_mw=discharge,
        grid_mw=grid,
        curtailment_mw=curtail,
        unserved_mw=unserved,
        soc_mwh=soc_arr,
        re_origin_soc_mwh=re_soc_arr,
        grid_origin_soc_mwh=grid_soc_arr,
        direct_re_mw=direct_re,
        re_from_bess_mw=re_from_bess,
        re_serving_load_mw=re_serving,
        hourly_cfe_pct=cfe,
        charge_from_re_mw=ch_re,
        charge_from_grid_mw=ch_grid,
        balance_error_mw=bal_err,
        cf_supply_mw=cf_supply,
        matched_cf_mw=matched_cf,
        hydro_mw=hydro,
        nuclear_mw=nuclear,
        meta={
            "dispatch_mode": "LP Dispatch",
            "max_abs_balance_error_mw": float(np.max(np.abs(bal_err))) if n else 0.0,
            "bess_power_mw": power,
            "bess_energy_mwh": energy,
            "grid_cap_mw": grid_cap,
            "grid_cap_effective_mw": grid_cap_eff,
            "eta_c": eta_c,
            "eta_d": eta_d,
            "tariff_inr_per_kwh": tariff,
            "cfe_formula": CFE_FORMULA,
        },
    )
    return enrich_split_flows(result)


def enrich_split_flows(d: DispatchResult) -> DispatchResult:
    """Fill solar/wind split arrays when missing (e.g. LP replay path)."""
    n = len(d.load_mw)
    if len(getattr(d, "solar_to_load_mw", np.zeros(0))) == n and float(np.sum(d.solar_to_load_mw)) + float(
        np.sum(d.wind_to_load_mw)
    ) > 0:
        return d

    solar_to_load = np.zeros(n)
    wind_to_load = np.zeros(n)
    solar_to_bess = np.zeros(n)
    wind_to_bess = np.zeros(n)
    solar_curtail = np.zeros(n)
    wind_curtail = np.zeros(n)
    solar_from_bess = np.zeros(n)
    wind_from_bess = np.zeros(n)
    grid_from_bess = np.zeros(n)
    solar_soc_arr = np.zeros(n)
    wind_soc_arr = np.zeros(n)

    for t in range(n):
        sol = float(d.solar_mw[t])
        win = float(d.wind_mw[t])
        re = sol + win
        d_re = float(d.direct_re_mw[t])
        c_re = float(d.charge_from_re_mw[t])
        if re > 1e-12:
            solar_to_load[t] = d_re * sol / re
            wind_to_load[t] = d_re * win / re
        leftover_s = max(0.0, sol - solar_to_load[t])
        leftover_w = max(0.0, win - wind_to_load[t])
        leftover = leftover_s + leftover_w
        if leftover > 1e-12 and c_re > 0:
            solar_to_bess[t] = c_re * leftover_s / leftover
            wind_to_bess[t] = c_re * leftover_w / leftover
        solar_curtail[t] = max(0.0, leftover_s - solar_to_bess[t])
        wind_curtail[t] = max(0.0, leftover_w - wind_to_bess[t])
        dis = float(d.discharge_mw[t])
        re_d = float(d.re_from_bess_mw[t])
        grid_from_bess[t] = max(0.0, dis - re_d)
        # Approximate solar/wind origin split by contemporaneous charge shares
        ch_s = solar_to_bess[t]
        ch_w = wind_to_bess[t]
        ch = ch_s + ch_w
        if ch > 1e-12:
            solar_from_bess[t] = re_d * ch_s / ch
            wind_from_bess[t] = re_d * ch_w / ch
        else:
            solar_from_bess[t] = re_d
            wind_from_bess[t] = 0.0
        solar_soc_arr[t] = float(d.re_origin_soc_mwh[t])  # not split in LP path
        wind_soc_arr[t] = 0.0

    d.solar_to_load_mw = solar_to_load
    d.wind_to_load_mw = wind_to_load
    d.solar_to_bess_mw = solar_to_bess
    d.wind_to_bess_mw = wind_to_bess
    d.solar_curtailment_mw = solar_curtail
    d.wind_curtailment_mw = wind_curtail
    d.solar_from_bess_mw = solar_from_bess
    d.wind_from_bess_mw = wind_from_bess
    d.grid_from_bess_mw = grid_from_bess
    d.solar_origin_soc_mwh = solar_soc_arr
    d.wind_origin_soc_mwh = wind_soc_arr
    return d


def run_dispatch(
    config: dict,
    load_mw: np.ndarray,
    solar_mw: np.ndarray,
    wind_mw: np.ndarray,
    hod: np.ndarray,
    **overrides,
) -> DispatchResult:
    mode = str(v_opt(config, "optimization.dispatch_mode", "Rule-Based") or "Rule-Based")
    solar_full = np.asarray(solar_mw, dtype=float).copy()
    wind_full = np.asarray(wind_mw, dtype=float).copy()
    solar_avail, wind_avail, force_s, force_w = _apply_input_re_curtailment(config, solar_full, wind_full)

    if mode == "LP Dispatch":
        d = lp_dispatch(config, load_mw, solar_avail, wind_avail, hod, **overrides)
    else:
        d = rule_based_dispatch(config, load_mw, solar_avail, wind_avail, hod, **overrides)

    # Restore full RE generation on the result and add forced curtailment to totals
    d.solar_mw = solar_full
    d.wind_mw = wind_full
    d.curtailment_mw = np.asarray(d.curtailment_mw, dtype=float) + force_s + force_w
    if hasattr(d, "solar_curtailment_mw") and d.solar_curtailment_mw is not None and len(d.solar_curtailment_mw):
        d.solar_curtailment_mw = np.asarray(d.solar_curtailment_mw, dtype=float) + force_s
    if hasattr(d, "wind_curtailment_mw") and d.wind_curtailment_mw is not None and len(d.wind_curtailment_mw):
        d.wind_curtailment_mw = np.asarray(d.wind_curtailment_mw, dtype=float) + force_w
    d.meta = dict(d.meta or {})
    d.meta["input_re_curtailment_pct"] = _input_re_curtailment_pct(config) * 100.0
    d.meta["input_re_curtailment_scope"] = _input_re_curtailment_scope(config)
    d.meta["forced_curtailment_mwh"] = float(force_s.sum() + force_w.sum())
    return d


def _input_re_curtailment_pct(config: dict) -> float:
    try:
        pct = float(v(config, "general.re_curtailment_pct")) / 100.0
    except Exception:
        pct = 0.0
    return float(np.clip(pct, 0.0, 1.0))


def _input_re_curtailment_scope(config: dict) -> str:
    try:
        scope = str(v(config, "general.re_curtailment_scope")).strip()
    except Exception:
        scope = "Solar + Wind"
    if scope not in ("Solar + Wind", "Solar only", "Wind only"):
        return "Solar + Wind"
    return scope


def _apply_input_re_curtailment(
    config: dict, solar_mw: np.ndarray, wind_mw: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Remove user-specified % of RE for the selected scope before load/BESS allocation."""
    pct = _input_re_curtailment_pct(config)
    z = np.zeros_like(solar_mw)
    if pct <= 0:
        return solar_mw, wind_mw, z, z

    scope = _input_re_curtailment_scope(config)
    if scope == "Solar only":
        force_s = solar_mw * pct
        force_w = z
    elif scope == "Wind only":
        force_s = z
        force_w = wind_mw * pct
    else:
        # Solar + Wind: % of combined RE, split proportionally by hour
        re = solar_mw + wind_mw
        force = re * pct
        with np.errstate(divide="ignore", invalid="ignore"):
            s_share = np.where(re > 1e-12, solar_mw / re, 0.0)
            w_share = np.where(re > 1e-12, wind_mw / re, 0.0)
        force_s = force * s_share
        force_w = force * w_share

    return solar_mw - force_s, wind_mw - force_w, force_s, force_w
