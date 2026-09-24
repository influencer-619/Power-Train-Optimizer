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


def excel_discom_rate_inr_per_kwh(config: dict) -> float:
    """DISCOM volumetric stack: Energy + Wheeling + TOD + ED + TOSE + Other."""
    other = 0.0
    try:
        other = float(v(config, "grid.excel_discom_other_volumetric_inr_per_kwh"))
    except Exception:
        other = 0.0
    return (
        float(v(config, "grid.excel_discom_energy_inr_per_kwh"))
        + float(v(config, "grid.excel_discom_wheeling_inr_per_kwh"))
        + float(v(config, "grid.excel_discom_tod_inr_per_kwh"))
        + float(v(config, "grid.excel_discom_ed_inr_per_kwh"))
        + float(v(config, "grid.excel_discom_tose_inr_per_kwh"))
        + other
    )


def grid_fixed_annual_inr(config: dict) -> float:
    """Fixed charge + DISCOM meter rent and liquidated damages (monthly × 12)."""
    fixed = float(v(config, "grid.fixed_charge_inr_per_year"))
    try:
        meter = float(v(config, "grid.meter_rent_inr_per_month"))
    except Exception:
        meter = 0.0
    try:
        ld = float(v(config, "grid.liquidated_damages_inr_per_month"))
    except Exception:
        ld = 0.0
    return fixed + (meter + ld) * 12.0


def excel_solar_rate_inr_per_kwh(config: dict) -> float:
    """Captive solar column: PPA + charges sum."""
    return (
        float(v(config, "commercial.excel_solar_ppa_inr_per_kwh"))
        + float(v(config, "commercial.excel_solar_energy_inr_per_kwh"))
        + float(v(config, "commercial.excel_solar_wheeling_inr_per_kwh"))
        + float(v(config, "commercial.excel_solar_transmission_inr_per_kwh"))
        + float(v(config, "commercial.excel_solar_transmission_loss_inr_per_kwh"))
        + float(v(config, "commercial.excel_solar_css_inr_per_kwh"))
        + float(v(config, "commercial.excel_solar_as_inr_per_kwh"))
        + float(v(config, "commercial.excel_solar_sldc_inr_per_kwh"))
        + float(v(config, "commercial.excel_solar_banking_inr_per_kwh"))
        + float(v(config, "commercial.excel_solar_ed_inr_per_kwh"))
        + float(v(config, "commercial.excel_solar_tose_inr_per_kwh"))
    )


def excel_wind_rate_inr_per_kwh(config: dict) -> float:
    """Wind charge stack (same line items as Solar)."""
    try:
        return (
            float(v(config, "commercial.excel_wind_ppa_inr_per_kwh"))
            + float(v(config, "commercial.excel_wind_energy_inr_per_kwh"))
            + float(v(config, "commercial.excel_wind_wheeling_inr_per_kwh"))
            + float(v(config, "commercial.excel_wind_transmission_inr_per_kwh"))
            + float(v(config, "commercial.excel_wind_transmission_loss_inr_per_kwh"))
            + float(v(config, "commercial.excel_wind_css_inr_per_kwh"))
            + float(v(config, "commercial.excel_wind_as_inr_per_kwh"))
            + float(v(config, "commercial.excel_wind_sldc_inr_per_kwh"))
            + float(v(config, "commercial.excel_wind_banking_inr_per_kwh"))
            + float(v(config, "commercial.excel_wind_ed_inr_per_kwh"))
            + float(v(config, "commercial.excel_wind_tose_inr_per_kwh"))
        )
    except Exception:
        return excel_solar_rate_inr_per_kwh(config)


def excel_bess_rate_inr_per_kwh(config: dict) -> float:
    """BESS volumetric rate.

    Captive/Hybrid: single Storage tariff (excel_bess_ppa_inr_per_kwh) only —
    other OA lines are ignored. 0 = no ₹/kWh BESS cost (no auto CAPEX/OPEX).
    """
    structure = str(v(config, "commercial.structure") or "")
    if structure in ("CAPTIVE", "HYBRID"):
        try:
            return max(0.0, float(v(config, "commercial.excel_bess_ppa_inr_per_kwh")))
        except Exception:
            return 0.0
    try:
        return (
            float(v(config, "commercial.excel_bess_ppa_inr_per_kwh"))
            + float(v(config, "commercial.excel_bess_energy_inr_per_kwh"))
            + float(v(config, "commercial.excel_bess_wheeling_inr_per_kwh"))
            + float(v(config, "commercial.excel_bess_transmission_inr_per_kwh"))
            + float(v(config, "commercial.excel_bess_transmission_loss_inr_per_kwh"))
            + float(v(config, "commercial.excel_bess_css_inr_per_kwh"))
            + float(v(config, "commercial.excel_bess_as_inr_per_kwh"))
            + float(v(config, "commercial.excel_bess_sldc_inr_per_kwh"))
            + float(v(config, "commercial.excel_bess_banking_inr_per_kwh"))
            + float(v(config, "commercial.excel_bess_ed_inr_per_kwh"))
            + float(v(config, "commercial.excel_bess_tose_inr_per_kwh"))
        )
    except Exception:
        return 0.0


def _bess_storage_tariff_inr_per_kwh(config: dict) -> float:
    """Single Captive/Hybrid storage ₹/kWh (user-entered; 0 = free at ₹/kWh)."""
    return excel_bess_rate_inr_per_kwh(config) if str(v(config, "commercial.structure") or "") in (
        "CAPTIVE",
        "HYBRID",
    ) else 0.0


def _bess_owned_in_structure(config: dict) -> bool:
    """DC is always a BESS consumer (fixed Storage ₹/kWh) — never plant CAPEX/OPEX."""
    return False


def excel_style_energy_charges(config: dict, kpis: dict) -> dict[str, float]:
    """DISCOM / CAPTIVE closed-form energy cost matching tariff stacks.

    Energy share from Architecture Percentage of power (TARGET_POWER_PCT) or 8760
    served-energy shares (SIMULATED_ENERGY_SHARE).
    Rate = Discom×G% + Solar×S% + Wind×W% + BESS×B% (BESS = consumer Storage tariff).
    Annual ₹ = Energy_MWh × rate × 1000; Annual ₹ Cr = Annual ₹ / 1e7.
    """
    structure = str(v(config, "commercial.structure"))
    energy_mwh = float(kpis.get("annual_load_mwh") or 0.0)
    discom = excel_discom_rate_inr_per_kwh(config)
    solar = excel_solar_rate_inr_per_kwh(config)
    wind = excel_wind_rate_inr_per_kwh(config)
    bess = excel_bess_rate_inr_per_kwh(config)

    def _flag(dotted: str, default: bool = True) -> bool:
        try:
            return bool(v(config, dotted))
        except Exception:
            return default

    def _mix(key: str) -> float:
        try:
            return max(0.0, min(100.0, float(v(config, f"commercial.{key}"))))
        except Exception:
            return 0.0

    try:
        blend_basis = str(v(config, "commercial.cost_blend_basis") or "TARGET_POWER_PCT")
    except Exception:
        blend_basis = "TARGET_POWER_PCT"

    arch_bess_pct = 0.0
    if structure == "DISCOM":
        grid_pct, re_pct = 100.0, 0.0
        solar_pct = wind_pct = bess_pct = 0.0
        blend_basis = "TARGET_POWER_PCT"
    elif blend_basis == "SIMULATED_ENERGY_SHARE":
        # DC buyer: Simulated = Architecture contracted mix % (fixed-rate delivery; no plant MW).
        grid_pct = max(0.0, min(100.0, float(kpis.get("simulated_mix_grid_pct") or 0.0)))
        solar_pct = max(0.0, min(100.0, float(kpis.get("simulated_mix_solar_pct") or 0.0)))
        wind_pct = max(0.0, min(100.0, float(kpis.get("simulated_mix_wind_pct") or 0.0)))
        bess_pct = (
            max(0.0, min(100.0, float(kpis.get("simulated_mix_bess_pct") or 0.0)))
            if _flag("commercial.include_bess", True)
            else 0.0
        )
        arch_bess_pct = bess_pct
        re_pct = max(0.0, min(100.0, float(kpis.get("simulated_mix_re_pct") or (solar_pct + wind_pct + bess_pct))))
        if grid_pct <= 0 and re_pct <= 0:
            solar_pct, re_pct = 100.0, 100.0
    else:
        grid_pct = _mix("mix_discom_pct") if _flag("commercial.include_discom", False) else 0.0
        solar_pct = _mix("mix_solar_pct") if _flag("commercial.include_solar", True) else 0.0
        wind_pct = _mix("mix_wind_pct") if _flag("commercial.include_wind", True) else 0.0
        bess_pct = _mix("mix_bess_pct") if _flag("commercial.include_bess", True) else 0.0
        arch_bess_pct = bess_pct
        re_pct = solar_pct + wind_pct + bess_pct
        if grid_pct <= 0 and (solar_pct + wind_pct + bess_pct) <= 0:
            solar_pct, re_pct = 100.0, 100.0

    blended = (
        discom * (grid_pct / 100.0)
        + solar * (solar_pct / 100.0)
        + wind * (wind_pct / 100.0)
        + bess * (bess_pct / 100.0)
    )
    # Price any RE not already in S/W/B at solar rate (origin-attributed RE vs direct shares)
    priced_re = solar_pct + wind_pct + bess_pct
    residual_re = max(0.0, re_pct - priced_re) if blend_basis == "SIMULATED_ENERGY_SHARE" else 0.0
    if residual_re > 0 and bess_pct <= 0:
        # Only when BESS is not separately priced — avoid double-counting Storage tariff energy
        blended += solar * (residual_re / 100.0)
    elif residual_re > 0:
        residual_re = 0.0

    grid_cost = energy_mwh * (grid_pct / 100.0) * discom * 1000.0
    solar_cost = energy_mwh * (solar_pct / 100.0) * solar * 1000.0
    wind_cost = energy_mwh * (wind_pct / 100.0) * wind * 1000.0
    bess_cost = energy_mwh * (bess_pct / 100.0) * bess * 1000.0
    if residual_re > 0:
        solar_cost += energy_mwh * (residual_re / 100.0) * solar * 1000.0
    re_cost = solar_cost + wind_cost + bess_cost
    annual_inr = energy_mwh * blended * 1000.0
    annual_cr = annual_inr / 1e7
    discom_only_cr = (energy_mwh * discom * 1000.0) / 1e7
    savings_cr = discom_only_cr - annual_cr

    return {
        "grid_energy_cost_inr": grid_cost,
        "solar_energy_cost_inr": solar_cost,
        "wind_energy_cost_inr": wind_cost,
        "bess_energy_cost_inr": bess_cost,
        "demand_charge_inr": 0.0,
        "fixed_charge_inr": 0.0,
        "re_energy_cost_inr": re_cost,
        "network_solar_inr": 0.0,
        "network_wind_inr": 0.0,
        "network_bess_inr": 0.0,
        "network_re_inr": 0.0,
        "network_grid_inr": 0.0,
        "energy_and_network_inr": annual_inr,
        "excel_discom_rate_inr_per_kwh": discom,
        "excel_solar_rate_inr_per_kwh": solar,
        "excel_wind_rate_inr_per_kwh": wind,
        "excel_bess_rate_inr_per_kwh": bess,
        "excel_blended_rate_inr_per_kwh": blended,
        "excel_grid_pct": grid_pct,
        "excel_re_pct": re_pct,
        "excel_solar_power_pct": solar_pct if structure != "DISCOM" else 0.0,
        "excel_wind_power_pct": wind_pct if structure != "DISCOM" else 0.0,
        "excel_bess_power_pct": (
            arch_bess_pct if structure in ("CAPTIVE", "HYBRID") else bess_pct
        )
        if structure != "DISCOM"
        else 0.0,
        "excel_annual_energy_cr": annual_cr,
        "excel_discom_only_cr": discom_only_cr,
        "excel_savings_vs_discom_cr": savings_cr,
        "cost_basis": "excel_tariff_stack",
        "cost_blend_basis": blend_basis,
        "target_grid_pct": (
            _mix("mix_discom_pct") if _flag("commercial.include_discom", False) else 0.0
        )
        if structure != "DISCOM"
        else 100.0,
        "target_re_pct": (
            (_mix("mix_solar_pct") if _flag("commercial.include_solar", True) else 0.0)
            + (_mix("mix_wind_pct") if _flag("commercial.include_wind", True) else 0.0)
            + (_mix("mix_bess_pct") if _flag("commercial.include_bess", True) else 0.0)
        )
        if structure != "DISCOM"
        else 0.0,
        "simulated_grid_pct": float(
            kpis.get("simulated_mix_grid_served_pct")
            or kpis.get("simulated_mix_grid_pct")
            or 0.0
        ),
        "simulated_re_pct": float(kpis.get("simulated_mix_re_pct") or 0.0),
        "annual_load_mwh": energy_mwh,
    }


def carbon_outcomes(config: dict, energy_detail: dict, energy_mwh: float | None = None) -> dict[str, float]:
    """CFE / carbon vs 100% DISCOM using Architecture power % and grid EF.

    RE share (Solar+Wind+BESS) is treated as carbon-free for this commercial model.
    """
    load_mwh = float(
        energy_mwh
        if energy_mwh is not None
        else (energy_detail.get("annual_load_mwh") or 0.0)
    )
    try:
        ef = float(v(config, "compliance.grid_emission_factor_tco2_per_mwh"))
    except Exception:
        ef = 0.82
    grid_pct = float(energy_detail.get("excel_grid_pct") or 0.0)
    re_pct = float(energy_detail.get("excel_re_pct") or 0.0)
    baseline = load_mwh * ef
    actual = load_mwh * (grid_pct / 100.0) * ef
    saved = max(0.0, baseline - actual)
    return {
        "grid_emission_factor_tco2_per_mwh": ef,
        "cfe_pct": re_pct,
        "annual_load_mwh": load_mwh,
        "grid_energy_mwh": load_mwh * (grid_pct / 100.0),
        "re_energy_mwh": load_mwh * (re_pct / 100.0),
        "baseline_tco2": baseline,
        "actual_tco2": actual,
        "carbon_saved_tco2": saved,
    }


def capital_costs(config: dict) -> dict[str, float]:
    """Always zero — DC buyer path has no generation-plant CAPEX."""
    return {"solar_capex": 0.0, "wind_capex": 0.0, "bess_capex": 0.0, "total_capex": 0.0}


def annual_opex(config: dict) -> dict[str, float]:
    """Always zero — DC buyer path has no generation-plant OPEX."""
    return {"solar_opex": 0.0, "wind_opex": 0.0, "bess_opex": 0.0, "total_opex": 0.0}


def additional_annual_costs(config: dict) -> dict[str, Any]:
    """User-defined extra annual cost line items from financial.additional_costs."""
    raw = []
    try:
        p = config.get("financial", {}).get("additional_costs")
        if isinstance(p, dict):
            raw = p.get("value") or []
        elif isinstance(p, list):
            raw = p
    except Exception:
        raw = []
    items: list[dict[str, Any]] = []
    total = 0.0
    if isinstance(raw, list):
        for row in raw:
            if not isinstance(row, dict):
                continue
            label = str(row.get("label") or row.get("name") or "").strip() or "Additional cost"
            try:
                amount = float(row.get("amount_inr_per_year", row.get("amount", 0.0)) or 0.0)
            except Exception:
                amount = 0.0
            if amount == 0.0 and not str(row.get("label") or "").strip():
                continue
            items.append({"label": label, "amount_inr_per_year": amount})
            total += amount
    return {"items": items, "total_inr": total}


def annual_energy_charges(config: dict, kpis: dict, dispatch_tariff: np.ndarray, grid_mw: np.ndarray) -> dict[str, float]:
    structure = str(v(config, "commercial.structure"))
    grid_cost = float(np.sum(grid_mw * dispatch_tariff) * 1000.0)  # MW * ₹/kWh * 1000 = ₹
    demand = float(kpis["max_grid_import_mw"]) * float(v(config, "grid.demand_charge_inr_per_mw_month")) * 12.0
    fixed = grid_fixed_annual_inr(config)

    solar_mwh = float(kpis["annual_solar_mwh"])
    wind_mwh = float(kpis["annual_wind_mwh"])
    bess_discharge_mwh = float(kpis.get("bess_discharge_mwh", 0.0) or 0.0)
    re_served = float(kpis["re_serving_load_mwh"])
    loss = float(v(config, "grid.loss_pct")) / 100.0

    tx = float(v(config, "grid.transmission_inr_per_kwh"))
    wh = float(v(config, "grid.wheeling_inr_per_kwh"))
    other = float(v(config, "grid.other_charges_inr_per_kwh"))

    re_energy_cost = 0.0
    network_on_re = 0.0
    network_on_grid = 0.0
    network_solar = 0.0
    network_wind = 0.0
    network_bess = 0.0

    if structure == "DISCOM":
        re_energy_cost = 0.0
    elif structure == "CAPTIVE":
        # Captive energy price on RE served, grossed for losses
        delivered = re_served / max(1.0 - loss, 1e-6)
        re_energy_cost = delivered * 1000.0 * float(v(config, "commercial.captive_energy_price"))
    elif structure == "OPEN_ACCESS":
        delivered = re_served / max(1.0 - loss, 1e-6)
        re_energy_cost = delivered * 1000.0 * float(v(config, "commercial.oa_energy_price"))
    else:  # HYBRID — buyer path always uses energy ₹/kWh (never plant CAPEX)
        from config.defaults import v_opt

        re_energy_cost = (
            solar_mwh * 1000.0 * float(v_opt(config, "solar.energy_cost_inr_per_kwh", 0.0) or 0.0)
            + wind_mwh * 1000.0 * float(v_opt(config, "wind.energy_cost_inr_per_kwh", 0.0) or 0.0)
        )

    if structure != "DISCOM":
        if bool(v(config, "commercial.apply_network_charges_to_solar")):
            s_bank = (
                float(v(config, "commercial.solar_banking_inr_per_kwh"))
                if bool(v(config, "commercial.solar_banking_enabled"))
                else 0.0
            )
            network_solar = solar_mwh * 1000.0 * (
                float(v(config, "commercial.solar_transmission_inr_per_kwh"))
                + float(v(config, "commercial.solar_wheeling_inr_per_kwh"))
                + s_bank
                + float(v(config, "commercial.solar_other_charges_inr_per_kwh"))
            )
        if bool(v(config, "commercial.apply_network_charges_to_wind")):
            w_bank = (
                float(v(config, "commercial.wind_banking_inr_per_kwh"))
                if bool(v(config, "commercial.wind_banking_enabled"))
                else 0.0
            )
            network_wind = wind_mwh * 1000.0 * (
                float(v(config, "commercial.wind_transmission_inr_per_kwh"))
                + float(v(config, "commercial.wind_wheeling_inr_per_kwh"))
                + w_bank
                + float(v(config, "commercial.wind_other_charges_inr_per_kwh"))
            )
        if bool(v(config, "commercial.apply_network_charges_to_bess")) and structure not in (
            "CAPTIVE",
            "HYBRID",
        ):
            b_bank = (
                float(v(config, "commercial.bess_banking_inr_per_kwh"))
                if bool(v(config, "commercial.bess_banking_enabled"))
                else 0.0
            )
            network_bess = bess_discharge_mwh * 1000.0 * (
                float(v(config, "commercial.bess_transmission_inr_per_kwh"))
                + float(v(config, "commercial.bess_wheeling_inr_per_kwh"))
                + b_bank
                + float(v(config, "commercial.bess_other_charges_inr_per_kwh"))
            )
        network_on_re = network_solar + network_wind + network_bess

    if bool(v(config, "commercial.apply_network_charges_to_grid")):
        network_on_grid = float(kpis["grid_mwh"]) * 1000.0 * (tx + wh + other)

    return {
        "grid_energy_cost_inr": grid_cost,
        "demand_charge_inr": demand,
        "fixed_charge_inr": fixed,
        "re_energy_cost_inr": re_energy_cost,
        "network_solar_inr": network_solar,
        "network_wind_inr": network_wind,
        "network_bess_inr": network_bess,
        "network_re_inr": network_on_re,
        "network_grid_inr": network_on_grid,
        "energy_and_network_inr": grid_cost + demand + fixed + re_energy_cost + network_on_re + network_on_grid,
    }


def annualized_capex(config: dict) -> dict[str, float]:
    """Always zero for DC buyer path (Solar/Wind/BESS priced via tariff stacks only)."""
    return {
        "solar_capex": 0.0,
        "wind_capex": 0.0,
        "bess_capex": 0.0,
        "total_capex": 0.0,
        "solar_ann": 0.0,
        "wind_ann": 0.0,
        "bess_ann": 0.0,
        "total_ann": 0.0,
    }


def evaluate_financial(config: dict, kpis: dict, compliance: dict, dispatch) -> dict[str, Any]:
    """Year-1 power bill + multi-year cash-flows for the data-centre buyer.

    Commercial path (CAPTIVE / HYBRID / DISCOM):
      Energy = Load × (DISCOM%×Discom + Solar%×Solar + Wind%×Wind + BESS%×Storage_tariff)
      Solar / Wind / BESS are always consumer tariff stacks — never plant CAPEX/OPEX.
      Demand = Peak_MW × DISCOM% × demand ₹/MW-month × 12
      Fixed  = fixed charge + meter/LD
    """
    tariff = dispatch.meta["tariff_inr_per_kwh"]
    structure = str(v(config, "commercial.structure"))
    excel_path = structure in ("DISCOM", "CAPTIVE", "HYBRID")
    include_capex = False  # buyer: tariff stacks only
    bess_owned = False

    if excel_path:
        energy = excel_style_energy_charges(config, kpis)
        grid_pct = float(energy.get("excel_grid_pct") or 0.0)
        try:
            peak_mw = float(v(config, "load.peak_load_mw"))
        except Exception:
            peak_mw = float(kpis.get("max_grid_import_mw") or 0.0)
        # Buyer path: demand charge always Peak × Architecture DISCOM% (SIMULATED = TARGET mix).
        demand_mw = peak_mw * (grid_pct / 100.0)
        energy["demand_charge_inr"] = demand_mw * float(v(config, "grid.demand_charge_inr_per_mw_month")) * 12.0
        energy["fixed_charge_inr"] = grid_fixed_annual_inr(config)
        energy["demand_billing_mw"] = demand_mw
        energy_only = (
            float(energy.get("grid_energy_cost_inr") or 0.0)
            + float(energy.get("solar_energy_cost_inr") or 0.0)
            + float(energy.get("wind_energy_cost_inr") or 0.0)
            + float(energy.get("bess_energy_cost_inr") or 0.0)
        )
        energy["energy_and_network_inr"] = (
            energy_only + energy["demand_charge_inr"] + energy["fixed_charge_inr"]
        )
        energy["excel_annual_bill_cr"] = float(energy["energy_and_network_inr"]) / 1e7
    else:
        energy = annual_energy_charges(config, kpis, tariff, dispatch.grid_mw)

    opex = {"solar_opex": 0.0, "wind_opex": 0.0, "bess_opex": 0.0, "total_opex": 0.0}
    caps = {"solar_capex": 0.0, "wind_capex": 0.0, "bess_capex": 0.0, "total_capex": 0.0}
    ann = {**caps, "solar_ann": 0.0, "wind_ann": 0.0, "bess_ann": 0.0, "total_ann": 0.0}

    # No plant CAPEX in cashflows (consumer tariff path)
    include_capex_cf = False

    compliance_cost = float(compliance["total_compliance_cost_inr"])
    extra = additional_annual_costs(config)
    extra_total = float(extra["total_inr"])
    load_kwh = float(kpis["annual_load_mwh"]) * 1000.0

    life = int(v(config, "financial.project_life_yr"))
    discount = float(v(config, "financial.discount_rate_pct")) / 100.0
    from config.defaults import v_opt

    inflation = float(v_opt(config, "financial.inflation_pct", 0.0) or 0.0) / 100.0
    elec_esc = float(v(config, "financial.electricity_escalation_pct")) / 100.0
    re_esc = float(v(config, "financial.re_cost_escalation_pct")) / 100.0
    residual_pct = float(v_opt(config, "financial.residual_value_pct", 0.0) or 0.0) / 100.0

    capex0 = caps["total_capex"] if include_capex_cf else 0.0
    financing_on = False  # plant financing removed
    debt_pct = 0.0
    interest_rate = 0.0
    debt_tenor = 0
    tax_rate = float(v(config, "financial.tax_pct")) / 100.0
    debt0 = 0.0
    equity0 = capex0
    principal_annual = 0.0
    outstanding = 0.0

    # Year-1 uses annualised BESS (and plant if flag) unless financing replaces with debt service
    ann_for_year1 = 0.0 if financing_on else float(ann["total_ann"])
    total_annual = (
        float(energy["energy_and_network_inr"])
        + opex["total_opex"]
        + ann_for_year1
        + compliance_cost
        + extra_total
    )

    def _re_energy_base() -> float:
        split = (
            float(energy.get("solar_energy_cost_inr") or 0.0)
            + float(energy.get("wind_energy_cost_inr") or 0.0)
            + float(energy.get("bess_energy_cost_inr") or 0.0)
        )
        if split > 0:
            return split + float(energy.get("network_re_inr") or 0.0) + float(energy.get("network_grid_inr") or 0.0)
        return (
            float(energy.get("re_energy_cost_inr") or 0.0)
            + float(energy.get("network_re_inr") or 0.0)
            + float(energy.get("network_grid_inr") or 0.0)
        )

    cashflows = [-equity0]
    annual_costs = []
    debt_schedule = []
    for y in range(1, life + 1):
        grid_part = float(energy["grid_energy_cost_inr"]) * ((1 + elec_esc) ** (y - 1))
        demand_fixed = (float(energy["demand_charge_inr"]) + float(energy["fixed_charge_inr"])) * (
            (1 + inflation) ** (y - 1)
        )
        re_part = _re_energy_base() * ((1 + re_esc) ** (y - 1))
        opex_y = opex["total_opex"] * ((1 + inflation) ** (y - 1))
        comp_y = compliance_cost * ((1 + inflation) ** (y - 1))
        extra_y = extra_total * ((1 + inflation) ** (y - 1))
        repl = 0.0
        if include_capex_cf and y == int(v_opt(config, "bess.replacement_year", -1) or -1):
            repl = caps["bess_capex"] * float(v_opt(config, "bess.replacement_cost_pct", 0.0) or 0.0) / 100.0

        interest_y = 0.0
        principal_y = 0.0
        if financing_on and y <= debt_tenor and outstanding > 1e-9:
            interest_y = outstanding * interest_rate
            principal_y = min(principal_annual, outstanding)
            outstanding = max(0.0, outstanding - principal_y)
        debt_service_y = interest_y + principal_y
        tax_y = 0.0
        if tax_rate > 0 and interest_y > 0:
            tax_y = -tax_rate * interest_y

        cost_y = grid_part + demand_fixed + re_part + opex_y + comp_y + extra_y + repl + debt_service_y + tax_y
        residual = 0.0
        if y == life and include_capex_cf:
            residual = -capex0 * residual_pct
        cf = -cost_y - residual
        cashflows.append(cf)
        annual_costs.append(cost_y)
        if financing_on:
            debt_schedule.append(
                {
                    "year": y,
                    "interest_inr": interest_y,
                    "principal_inr": principal_y,
                    "debt_service_inr": debt_service_y,
                    "tax_shield_inr": -tax_y if tax_y < 0 else 0.0,
                    "outstanding_end_inr": outstanding,
                }
            )

    npv = float(sum(cf / ((1 + discount) ** t) for t, cf in enumerate(cashflows)))
    irr = _irr(cashflows)
    payback = _payback([-c for c in cashflows])

    year1_debt = float(debt_schedule[0]["debt_service_inr"]) if debt_schedule else 0.0
    year1_tax_shield = float(debt_schedule[0]["tax_shield_inr"]) if debt_schedule else 0.0
    total_annual_reported = total_annual + year1_debt - year1_tax_shield
    # All-in delivered ₹/kWh (energy + demand + fixed + compliance + extras)
    delivered_cost_per_kwh = total_annual_reported / load_kwh if load_kwh > 0 else 0.0
    cost_per_kwh = delivered_cost_per_kwh

    if excel_path and not include_capex and not bess_owned:
        # Commercial buyer path — only mix bill lines (no plant CAPEX/OPEX/debt).
        breakdown = {
            "solar_energy_or_ann_inr": float(energy.get("solar_energy_cost_inr") or 0.0),
            "wind_energy_or_ann_inr": float(energy.get("wind_energy_cost_inr") or 0.0),
            "bess_energy_inr": float(energy.get("bess_energy_cost_inr") or 0.0),
            "grid_energy_inr": float(energy.get("grid_energy_cost_inr") or 0.0),
            "demand_inr": float(energy.get("demand_charge_inr") or 0.0),
            "fixed_inr": float(energy.get("fixed_charge_inr") or 0.0),
            "compliance_inr": compliance_cost,
        }
        if abs(extra_total) > 1e-9:
            breakdown["additional_costs_inr"] = extra_total
        # Headline Energy Cost ₹/kWh = blended (Captive/Hybrid) or DISCOM stack rate (DISCOM).
        # Annual energy bill = that rate × annual load; demand/fixed stay separate in breakdown.
        blended = float(energy.get("excel_blended_rate_inr_per_kwh") or 0.0)
        cost_per_kwh = blended
        energy_only_inr = (
            float(energy.get("grid_energy_cost_inr") or 0.0)
            + float(energy.get("solar_energy_cost_inr") or 0.0)
            + float(energy.get("wind_energy_cost_inr") or 0.0)
            + float(energy.get("bess_energy_cost_inr") or 0.0)
        )
        energy["excel_annual_energy_cr"] = energy_only_inr / 1e7
        # Keep full bill (energy + demand + fixed) under a clear key; annual_bill_cr = energy-only for UI headline
        energy["excel_total_bill_cr"] = float(energy.get("energy_and_network_inr") or 0.0) / 1e7
        energy["excel_annual_bill_cr"] = energy_only_inr / 1e7
        cost_metric_label = "ENERGY COST"
        cost_metric_definition = (
            "Energy Cost ₹/kWh = Architecture blended rate "
            "(Discom×G% + Solar×S% + Wind×W% + BESS×Storage%) for Captive/Hybrid, "
            "or DISCOM stack rate for DISCOM baseline. "
            "Annual energy bill ₹ = Energy Cost × annual load kWh. "
            "Demand / fixed / compliance are shown separately (not in Energy Cost)."
        )
    else:
        sol_mwh = float(kpis.get("annual_solar_mwh") or 0.0)
        win_mwh = float(kpis.get("annual_wind_mwh") or 0.0)
        re_bill = float(energy.get("re_energy_cost_inr") or 0.0)
        breakdown = {
            "solar_energy_or_ann_inr": (0.0 if financing_on else ann["solar_ann"])
            if include_capex
            else re_bill * (sol_mwh / max(sol_mwh + win_mwh, 1e-9)),
            "wind_energy_or_ann_inr": 0.0 if financing_on else ann["wind_ann"],
            "bess_ann_inr": 0.0 if financing_on else ann["bess_ann"],
            "bess_opex_inr": opex["bess_opex"],
            "grid_energy_inr": energy["grid_energy_cost_inr"],
            "demand_inr": energy["demand_charge_inr"],
            "fixed_inr": energy["fixed_charge_inr"],
            "transmission_wheeling_inr": float(energy.get("network_re_inr") or 0.0)
            + float(energy.get("network_grid_inr") or 0.0),
            "compliance_inr": compliance_cost,
            "opex_re_inr": opex["solar_opex"] + opex["wind_opex"],
            "additional_costs_inr": extra_total,
            "debt_service_inr_year1": year1_debt,
            "tax_shield_inr_year1": year1_tax_shield,
        }
        cost_metric_label = "TOTAL COST OF DELIVERED ENERGY"
        cost_metric_definition = (
            "Year-1 total annual cost (energy + network + OPEX + annualised CAPEX + compliance"
            + (" + debt service" if financing_on else "")
            + ") / annual load kWh."
        )

    financing_detail = {
        "enabled": financing_on,
        "debt_pct": debt_pct * 100.0 if financing_on else 0.0,
        "interest_rate_pct": interest_rate * 100.0 if financing_on else 0.0,
        "debt_tenor_yr": debt_tenor if financing_on else 0,
        "tax_pct": tax_rate * 100.0,
        "debt_inr": debt0,
        "equity_inr": equity0,
        "total_capex_inr": capex0,
        "schedule": debt_schedule,
    }

    load_mwh = float(kpis.get("annual_load_mwh") or 0.0)
    carbon = carbon_outcomes(config, energy, energy_mwh=load_mwh)

    return {
        "structure": structure,
        "total_annual_cost_inr": total_annual_reported,
        "cost_per_kwh": cost_per_kwh,
        "delivered_cost_per_kwh": delivered_cost_per_kwh,
        "energy_cost_per_kwh": cost_per_kwh,
        "capex_inr": equity0 if financing_on else capex0,
        "capex_total_inr": capex0,
        "capex_detail": caps,
        "opex_detail": opex,
        "energy_detail": energy,
        "carbon": carbon,
        "financing": financing_detail,
        "excel_tariff": {
            "discom_rate_inr_per_kwh": energy.get("excel_discom_rate_inr_per_kwh"),
            "solar_rate_inr_per_kwh": energy.get("excel_solar_rate_inr_per_kwh"),
            "wind_rate_inr_per_kwh": energy.get("excel_wind_rate_inr_per_kwh"),
            "bess_rate_inr_per_kwh": energy.get("excel_bess_rate_inr_per_kwh"),
            "blended_rate_inr_per_kwh": energy.get("excel_blended_rate_inr_per_kwh"),
            "grid_pct": energy.get("excel_grid_pct"),
            "re_pct": energy.get("excel_re_pct"),
            "solar_pct": energy.get("excel_solar_power_pct"),
            "wind_pct": energy.get("excel_wind_power_pct"),
            "bess_pct": energy.get("excel_bess_power_pct"),
            "annual_energy_cr": energy.get("excel_annual_energy_cr"),
            "annual_bill_cr": energy.get("excel_annual_bill_cr"),
            "total_bill_cr": energy.get("excel_total_bill_cr"),
            "annual_energy_inr": (
                float(energy.get("grid_energy_cost_inr") or 0.0)
                + float(energy.get("solar_energy_cost_inr") or 0.0)
                + float(energy.get("wind_energy_cost_inr") or 0.0)
                + float(energy.get("bess_energy_cost_inr") or 0.0)
            ),
            "discom_only_cr": energy.get("excel_discom_only_cr"),
            "savings_vs_discom_cr": energy.get("excel_savings_vs_discom_cr"),
            "cost_basis": energy.get("cost_basis"),
            "cost_blend_basis": energy.get("cost_blend_basis"),
            "target_grid_pct": energy.get("target_grid_pct"),
            "target_re_pct": energy.get("target_re_pct"),
            "simulated_grid_pct": energy.get("simulated_grid_pct"),
            "simulated_re_pct": energy.get("simulated_re_pct"),
            "cfe_pct": carbon.get("cfe_pct"),
            "carbon_saved_tco2": carbon.get("carbon_saved_tco2"),
            "baseline_tco2": carbon.get("baseline_tco2"),
            "actual_tco2": carbon.get("actual_tco2"),
            "annual_load_mwh": load_mwh,
            "demand_billing_mw": energy.get("demand_billing_mw"),
            "solar_energy_cost_inr": energy.get("solar_energy_cost_inr"),
            "wind_energy_cost_inr": energy.get("wind_energy_cost_inr"),
            "bess_energy_cost_inr": energy.get("bess_energy_cost_inr"),
            "grid_energy_cost_inr": energy.get("grid_energy_cost_inr"),
        }
        if energy.get("cost_basis") == "excel_tariff_stack"
        else None,
        "annualized_capex": ann,
        "compliance_cost_inr": compliance_cost,
        "additional_costs_inr": extra_total,
        "additional_cost_items": extra["items"],
        "cost_breakdown": breakdown,
        "cashflows_inr": cashflows,
        "annual_costs_inr": annual_costs,
        "npv_inr": npv,
        "npv_cr": npv / 1e7,
        "irr_pct": irr * 100.0 if irr is not None else None,
        "payback_years": payback,
        "lcoe_inr_per_kwh": cost_per_kwh,
        "total_cost_of_delivered_energy_inr_per_kwh": delivered_cost_per_kwh,
        "cost_metric_label": cost_metric_label,
        "cost_metric_definition": cost_metric_definition,
    }



def data_center_project_economics(
    config: dict,
    project_fin: dict,
    discom_fin: dict | None = None,
    discount_rate: float | None = None,
) -> dict[str, Any]:
    """Investment / IRR / Payback from the data-centre owner's point of view.

    Year-0 outflow = data_center.capex_inr (facility build).
    Annual inflows:
      - If annual_revenue_inr > 0: revenue − power bill − non-power OPEX
      - Else: power-bill savings vs 100% DISCOM (procurement benefit only)
    """
    disc = 0.10 if discount_rate is None else float(discount_rate)
    try:
        dc_capex = max(0.0, float(v(config, "data_center.capex_inr")))
    except Exception:
        dc_capex = 0.0
    try:
        revenue0 = max(0.0, float(v(config, "data_center.annual_revenue_inr")))
    except Exception:
        revenue0 = 0.0
    try:
        opex0 = max(0.0, float(v(config, "data_center.annual_opex_ex_power_inr")))
    except Exception:
        opex0 = 0.0
    try:
        inflation = float(v(config, "financial.inflation_pct")) / 100.0
    except Exception:
        inflation = 0.05

    annual_costs = list(project_fin.get("annual_costs_inr") or [])
    life = len(annual_costs)
    if life <= 0:
        try:
            life = int(v(config, "financial.project_life_yr"))
        except Exception:
            life = 25
        annual_costs = [float(project_fin.get("total_annual_cost_inr") or 0.0)] * life

    use_revenue = revenue0 > 0
    mode = "dc_revenue_minus_costs" if use_revenue else "power_savings_vs_discom"

    cfs: list[float] = [-dc_capex]
    annual_net: list[float] = []
    for y in range(life):
        power_y = float(annual_costs[y]) if y < len(annual_costs) else float(annual_costs[-1])
        if use_revenue:
            rev_y = revenue0 * ((1 + inflation) ** y)
            opex_y = opex0 * ((1 + inflation) ** y)
            net = rev_y - power_y - opex_y
        else:
            if discom_fin is not None:
                d_costs = list(discom_fin.get("annual_costs_inr") or [])
                discom_y = (
                    float(d_costs[y])
                    if y < len(d_costs)
                    else float(discom_fin.get("total_annual_cost_inr") or 0.0)
                )
            else:
                discom_y = power_y
            net = discom_y - power_y  # savings vs DISCOM
        annual_net.append(net)
        cfs.append(net)

    npv = float(sum(cf / ((1 + disc) ** t) for t, cf in enumerate(cfs)))
    irr = _irr(cfs) if dc_capex > 0 else None
    payback = _payback(cfs) if dc_capex > 0 else None

    return {
        "capex_inr": dc_capex,
        "annual_revenue_inr": revenue0,
        "annual_opex_ex_power_inr": opex0,
        "mode": mode,
        "cashflows_inr": cfs,
        "annual_net_inr": annual_net,
        "npv_inr": npv,
        "npv_cr": npv / 1e7,
        "irr_pct": irr * 100.0 if irr is not None else None,
        "payback_years": payback,
        "notes": (
            "DC project: Year-0 = data-centre CAPEX; annual = revenue − power − other OPEX."
            if use_revenue
            else "DC investment recovered from power-bill savings vs 100% DISCOM (enter Data Centre annual revenue for full project IRR)."
        ),
    }


def incremental_vs_discom(
    project_fin: dict,
    discom_fin: dict,
    discount_rate: float | None = None,
) -> dict:
    """Savings vs DISCOM as inflows; incremental CAPEX as outflow.

    ``discount_rate`` is a fraction (e.g. 0.10 for 10%). Prefer the project's
    ``financial.discount_rate_pct``; if omitted, falls back to 10% for callers
    that have not yet passed a rate.
    """
    disc = 0.10 if discount_rate is None else float(discount_rate)
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
    npv = float(sum(cf / ((1 + disc) ** t) for t, cf in enumerate(cfs)))
    return {
        "baseline_label": "DISCOM (grid-only)",
        "discom_annual_cost_inr": float(discom_fin.get("total_annual_cost_inr") or 0.0),
        "architecture_annual_cost_inr": float(project_fin.get("total_annual_cost_inr") or 0.0),
        "annual_savings_inr_year1": year1_savings,
        "incremental_capex_inr": inc_capex,
        "incremental_opex_inr_year1": inc_opex,
        "cashflows_inr": cfs,
        "npv_inr": npv,
        "discount_rate": disc,
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
