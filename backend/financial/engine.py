"""Commercial cost stacking and project financials."""

from __future__ import annotations

from typing import Any

import numpy as np

from config.defaults import v


def _crf(rate: float, n: int) -> float:
    if n <= 0:
        return 1.0
    if abs(rate) < 1e-12:
        return 1.0 / n
    return rate * (1.0 + rate) ** n / ((1.0 + rate) ** n - 1.0)


def capital_costs(config: dict) -> dict[str, float]:
    solar = float(v(config, "solar.capacity_mw")) * float(v(config, "solar.capex_inr_per_mw"))
    wind = float(v(config, "wind.capacity_mw")) * float(v(config, "wind.capex_inr_per_mw"))
    bess = (
        float(v(config, "bess.power_mw")) * float(v(config, "bess.capex_inr_per_mw"))
        + float(v(config, "bess.energy_mwh")) * float(v(config, "bess.capex_inr_per_mwh"))
    )
    return {"solar_capex": solar, "wind_capex": wind, "bess_capex": bess, "total_capex": solar + wind + bess}


def annual_opex(config: dict) -> dict[str, float]:
    solar = float(v(config, "solar.capacity_mw")) * float(v(config, "solar.opex_inr_per_mw_year"))
    wind = float(v(config, "wind.capacity_mw")) * float(v(config, "wind.opex_inr_per_mw_year"))
    bess = float(v(config, "bess.opex_inr_per_year"))
    return {"solar_opex": solar, "wind_opex": wind, "bess_opex": bess, "total_opex": solar + wind + bess}


def annual_energy_charges(config: dict, kpis: dict, dispatch_tariff: np.ndarray, grid_mw: np.ndarray) -> dict[str, float]:
    structure = str(v(config, "commercial.structure"))
    grid_cost = float(np.sum(grid_mw * dispatch_tariff) * 1000.0)  # MW * ₹/kWh * 1000 = ₹
    demand = float(kpis["max_grid_import_mw"]) * float(v(config, "grid.demand_charge_inr_per_mw_month")) * 12.0
    fixed = float(v(config, "grid.fixed_charge_inr_per_year"))

    solar_mwh = float(kpis["annual_solar_mwh"])
    wind_mwh = float(kpis["annual_wind_mwh"])
    re_served = float(kpis["re_serving_load_mwh"])
    loss = float(v(config, "grid.loss_pct")) / 100.0

    tx = float(v(config, "grid.transmission_inr_per_kwh"))
    wh = float(v(config, "grid.wheeling_inr_per_kwh"))
    bank = float(v(config, "grid.banking_inr_per_kwh")) if bool(v(config, "grid.banking_enabled")) else 0.0
    other = float(v(config, "grid.other_charges_inr_per_kwh"))

    re_energy_cost = 0.0
    network_on_re = 0.0
    network_on_grid = 0.0

    if structure == "DISCOM":
        re_energy_cost = 0.0
    elif structure == "CAPTIVE":
        # Captive energy price on RE served, grossed for losses
        delivered = re_served / max(1.0 - loss, 1e-6)
        re_energy_cost = delivered * 1000.0 * float(v(config, "commercial.captive_energy_price"))
    elif structure == "OPEN_ACCESS":
        delivered = re_served / max(1.0 - loss, 1e-6)
        re_energy_cost = delivered * 1000.0 * float(v(config, "commercial.oa_energy_price"))
    else:  # HYBRID
        if not bool(v(config, "commercial.include_generation_capex")):
            re_energy_cost = (
                solar_mwh * 1000.0 * float(v(config, "solar.energy_cost_inr_per_kwh"))
                + wind_mwh * 1000.0 * float(v(config, "wind.energy_cost_inr_per_kwh"))
            )

    if bool(v(config, "commercial.apply_network_charges_to_re")) and structure != "DISCOM":
        network_on_re = re_served * 1000.0 * (tx + wh + bank + other)
    if bool(v(config, "commercial.apply_network_charges_to_grid")):
        network_on_grid = float(kpis["grid_mwh"]) * 1000.0 * (tx + wh + other)

    return {
        "grid_energy_cost_inr": grid_cost,
        "demand_charge_inr": demand,
        "fixed_charge_inr": fixed,
        "re_energy_cost_inr": re_energy_cost,
        "network_re_inr": network_on_re,
        "network_grid_inr": network_on_grid,
        "energy_and_network_inr": grid_cost + demand + fixed + re_energy_cost + network_on_re + network_on_grid,
    }


def annualized_capex(config: dict) -> dict[str, float]:
    caps = capital_costs(config)
    include = bool(v(config, "commercial.include_generation_capex"))
    if not include or str(v(config, "commercial.structure")) == "DISCOM":
        return {"solar_ann": 0.0, "wind_ann": 0.0, "bess_ann": 0.0, "total_ann": 0.0, **caps}

    r = float(v(config, "financial.discount_rate_pct")) / 100.0
    solar_ann = caps["solar_capex"] * _crf(r, int(v(config, "solar.project_life_yr")))
    wind_ann = caps["wind_capex"] * _crf(r, int(v(config, "wind.project_life_yr")))
    bess_ann = caps["bess_capex"] * _crf(r, int(v(config, "bess.project_life_yr")))
    return {
        **caps,
        "solar_ann": solar_ann,
        "wind_ann": wind_ann,
        "bess_ann": bess_ann,
        "total_ann": solar_ann + wind_ann + bess_ann,
    }


def evaluate_financial(config: dict, kpis: dict, compliance: dict, dispatch) -> dict[str, Any]:
    tariff = dispatch.meta["tariff_inr_per_kwh"]
    energy = annual_energy_charges(config, kpis, tariff, dispatch.grid_mw)
    opex = annual_opex(config)
    ann = annualized_capex(config)
    structure = str(v(config, "commercial.structure"))
    if structure == "DISCOM":
        opex = {"solar_opex": 0.0, "wind_opex": 0.0, "bess_opex": 0.0, "total_opex": 0.0}

    compliance_cost = float(compliance["total_compliance_cost_inr"])
    total_annual = (
        energy["energy_and_network_inr"]
        + opex["total_opex"]
        + ann["total_ann"]
        + compliance_cost
    )
    load_kwh = float(kpis["annual_load_mwh"]) * 1000.0
    cost_per_kwh = total_annual / load_kwh if load_kwh > 0 else 0.0

    life = int(v(config, "financial.project_life_yr"))
    discount = float(v(config, "financial.discount_rate_pct")) / 100.0
    inflation = float(v(config, "financial.inflation_pct")) / 100.0
    elec_esc = float(v(config, "financial.electricity_escalation_pct")) / 100.0
    re_esc = float(v(config, "financial.re_cost_escalation_pct")) / 100.0
    residual_pct = float(v(config, "financial.residual_value_pct")) / 100.0

    caps = capital_costs(config)
    include_capex = bool(v(config, "commercial.include_generation_capex")) and structure != "DISCOM"
    capex0 = caps["total_capex"] if include_capex else 0.0

    cashflows = [-capex0]
    annual_costs = []
    for y in range(1, life + 1):
        grid_part = energy["grid_energy_cost_inr"] * ((1 + elec_esc) ** (y - 1))
        demand_fixed = (energy["demand_charge_inr"] + energy["fixed_charge_inr"]) * ((1 + inflation) ** (y - 1))
        re_part = (energy["re_energy_cost_inr"] + energy["network_re_inr"] + energy["network_grid_inr"]) * (
            (1 + re_esc) ** (y - 1)
        )
        opex_y = opex["total_opex"] * ((1 + inflation) ** (y - 1))
        comp_y = compliance_cost * ((1 + inflation) ** (y - 1))
        repl = 0.0
        if include_capex and y == int(v(config, "bess.replacement_year")):
            repl = caps["bess_capex"] * float(v(config, "bess.replacement_cost_pct")) / 100.0
        cost_y = grid_part + demand_fixed + re_part + opex_y + comp_y + repl
        residual = 0.0
        if y == life and include_capex:
            residual = -capex0 * residual_pct  # credit
        cf = -cost_y - residual
        cashflows.append(cf)
        annual_costs.append(cost_y)

    npv = float(sum(cf / ((1 + discount) ** t) for t, cf in enumerate(cashflows)))
    irr = _irr(cashflows)
    payback = _payback([-c for c in cashflows])  # cost recovery framing vs zero — use incremental later

    breakdown = {
        "solar_energy_or_ann_inr": ann["solar_ann"] if include_capex else energy["re_energy_cost_inr"] * (
            float(kpis["annual_solar_mwh"]) / max(float(kpis["annual_solar_mwh"] + kpis["annual_wind_mwh"]), 1e-9)
        ),
        "wind_energy_or_ann_inr": ann["wind_ann"],
        "bess_ann_inr": ann["bess_ann"],
        "bess_opex_inr": opex["bess_opex"],
        "grid_energy_inr": energy["grid_energy_cost_inr"],
        "demand_inr": energy["demand_charge_inr"],
        "fixed_inr": energy["fixed_charge_inr"],
        "transmission_wheeling_inr": energy["network_re_inr"] + energy["network_grid_inr"],
        "compliance_inr": compliance_cost,
        "opex_re_inr": opex["solar_opex"] + opex["wind_opex"],
    }

    return {
        "structure": structure,
        "total_annual_cost_inr": total_annual,
        "cost_per_kwh": cost_per_kwh,
        "capex_inr": capex0,
        "capex_detail": caps,
        "opex_detail": opex,
        "energy_detail": energy,
        "annualized_capex": ann,
        "compliance_cost_inr": compliance_cost,
        "cost_breakdown": breakdown,
        "cashflows_inr": cashflows,
        "annual_costs_inr": annual_costs,
        "npv_inr": npv,
        "npv_cr": npv / 1e7,
        "irr_pct": irr * 100.0 if irr is not None else None,
        "payback_years": payback,
        "lcoe_inr_per_kwh": cost_per_kwh,
        "total_cost_of_delivered_energy_inr_per_kwh": cost_per_kwh,
        "cost_metric_label": "TOTAL COST OF DELIVERED ENERGY",
        "cost_metric_definition": (
            "Year-1 total annual cost (energy + network + OPEX + annualised CAPEX + compliance) "
            "/ annual load kWh. Not a formal LCOE unless CAPEX annualisation assumptions match your LCOE standard."
        ),
    }


def incremental_vs_discom(project_fin: dict, discom_fin: dict) -> dict:
    """Savings vs DISCOM as inflows; incremental CAPEX as outflow."""
    inc_capex = float(project_fin["capex_inr"]) - float(discom_fin["capex_inr"])
    life = min(len(project_fin["annual_costs_inr"]), len(discom_fin["annual_costs_inr"]))
    cfs = [-inc_capex]
    annual_savings = []
    for y in range(life):
        savings = float(discom_fin["annual_costs_inr"][y]) - float(project_fin["annual_costs_inr"][y])
        annual_savings.append(savings)
        cfs.append(savings)
    year1_savings = annual_savings[0] if annual_savings else 0.0
    inc_opex = float(project_fin.get("opex_detail", {}).get("total_opex") or 0.0) - float(
        discom_fin.get("opex_detail", {}).get("total_opex") or 0.0
    )
    npv = float(sum(cf / ((1 + 0.10) ** t) for t, cf in enumerate(cfs)))
    return {
        "baseline_label": "DISCOM (grid-only)",
        "discom_annual_cost_inr": float(discom_fin.get("total_annual_cost_inr") or 0.0),
        "architecture_annual_cost_inr": float(project_fin.get("total_annual_cost_inr") or 0.0),
        "annual_savings_inr_year1": year1_savings,
        "incremental_capex_inr": inc_capex,
        "incremental_opex_inr_year1": inc_opex,
        "cashflows_inr": cfs,
        "npv_inr": npv,
        "irr_pct": (lambda x: x * 100.0 if x is not None else None)(_irr(cfs)),
        "payback_years": _payback(cfs),
        "notes": (
            "Incremental economics vs DISCOM baseline. "
            "Project NPV/IRR/payback for non-DISCOM structures use these incremental cashflows."
        ),
    }


def _irr(cashflows: list[float], guess: float = 0.1) -> float | None:
    if not cashflows or all(c <= 0 for c in cashflows) or all(c >= 0 for c in cashflows):
        return None
    r = guess
    for _ in range(100):
        npv = 0.0
        d = 0.0
        for t, cf in enumerate(cashflows):
            npv += cf / ((1 + r) ** t)
            if t:
                d -= t * cf / ((1 + r) ** (t + 1))
        if abs(d) < 1e-12:
            break
        r2 = r - npv / d
        if abs(r2 - r) < 1e-9:
            return float(r2)
        r = r2
        if r <= -0.999:
            r = -0.999
    # bisection fallback
    lo, hi = -0.99, 5.0
    def f(x):
        return sum(cf / ((1 + x) ** t) for t, cf in enumerate(cashflows))
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        return None
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if abs(fm) < 1e-6:
            return float(mid)
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return float(0.5 * (lo + hi))


def _payback(cashflows: list[float]) -> float | None:
    if not cashflows:
        return None
    cum = 0.0
    for t, cf in enumerate(cashflows):
        prev = cum
        cum += cf
        if t > 0 and prev < 0 <= cum:
            return float(t - 1 + (-prev / cf if cf else 0.0))
    return None
