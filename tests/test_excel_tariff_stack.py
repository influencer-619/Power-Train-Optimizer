"""Excel DC simulation_r3 DISCOM / CAPTIVE tariff-stack arithmetic."""

from __future__ import annotations

from backend.financial.engine import (
    excel_discom_rate_inr_per_kwh,
    excel_solar_rate_inr_per_kwh,
    excel_style_energy_charges,
)
from config.defaults import get_default_config, recompute_calculated, v


def test_it_pue_sets_peak_and_actual_load():
    cfg = recompute_calculated(get_default_config())
    # IT load is synced from Data Centre → IT capacity
    assert abs(v(cfg, "load.it_load_mw") - v(cfg, "data_center.it_capacity_mw")) < 1e-9
    assert abs(v(cfg, "load.it_load_mw") - 250.0) < 1e-9
    assert abs(v(cfg, "load.pue") - 1.25) < 1e-9
    assert abs(v(cfg, "load.peak_load_mw") - 312.5) < 1e-9  # 250 × 1.25
    # Primary LF synced from scenario 1 default 70% → 312.5 × 0.70
    assert abs(v(cfg, "load.load_factor_pct") - 70.0) < 1e-9
    assert abs(v(cfg, "load.base_load_mw") - 218.75) < 1e-9


def test_excel_discom_stack_sum():
    cfg = recompute_calculated(get_default_config())
    # 8.44 + 0 + (-0.56) + 0.59 + 0.28 + 0 other = 8.75
    assert abs(excel_discom_rate_inr_per_kwh(cfg) - 8.75) < 1e-9
    assert abs(v(cfg, "grid.excel_discom_total_inr_per_kwh") - 8.75) < 1e-9


def test_demand_kva_converts_to_mw_month():
    cfg = recompute_calculated(get_default_config())
    cfg["grid"]["demand_charge_inr_per_kva_month"]["value"] = 800.0
    cfg = recompute_calculated(cfg)
    assert abs(v(cfg, "grid.demand_charge_inr_per_mw_month") - 800_000.0) < 1e-6


def test_other_volumetric_adds_to_discom_total():
    cfg = recompute_calculated(get_default_config())
    cfg["grid"]["excel_discom_other_volumetric_inr_per_kwh"]["value"] = 0.05
    cfg = recompute_calculated(cfg)
    assert abs(excel_discom_rate_inr_per_kwh(cfg) - 8.80) < 1e-9
    assert abs(v(cfg, "grid.excel_discom_total_inr_per_kwh") - 8.80) < 1e-9


def test_excel_solar_stack_sum():
    cfg = recompute_calculated(get_default_config())
    # 3.5 + 0 + 0 + 1.04 + 0.15 + 0 + 0 + 0.05 + 0 + 0 + 0 = 4.16
    assert abs(excel_solar_rate_inr_per_kwh(cfg) - 4.16) < 1e-9
    assert abs(v(cfg, "commercial.excel_solar_total_inr_per_kwh") - 4.16) < 1e-9


def test_excel_discom_blend_100_grid():
    cfg = recompute_calculated(get_default_config())
    cfg["commercial"]["structure"]["value"] = "DISCOM"
    # Excel: Actual 200 MW × 8760 = 1,752,000 MWh; rate 8.75; Cr = 1,752,000×8.75×1000/1e7 = 1533
    energy_mwh = 200.0 * 8760.0
    kpis = {"annual_load_mwh": energy_mwh, "max_grid_import_mw": 0.0}
    out = excel_style_energy_charges(cfg, kpis)
    assert abs(out["excel_grid_pct"] - 100.0) < 1e-9
    assert abs(out["excel_re_pct"] - 0.0) < 1e-9
    assert abs(out["excel_blended_rate_inr_per_kwh"] - 8.75) < 1e-9
    assert abs(out["excel_annual_energy_cr"] - 1533.0) < 0.05


def test_excel_captive_100_pct_re_blend():
    """CAPTIVE has no DISCOM — Excel blend is 100% Solar charges stack."""
    cfg = recompute_calculated(get_default_config())
    cfg["commercial"]["structure"]["value"] = "CAPTIVE"
    cfg["commercial"]["include_solar"]["value"] = True
    cfg["commercial"]["include_wind"]["value"] = False
    cfg["commercial"]["include_bess"]["value"] = False
    cfg["commercial"]["mix_solar_pct"]["value"] = 100.0
    cfg = recompute_calculated(cfg)
    assert v(cfg, "commercial.include_discom") is False
    assert abs(v(cfg, "commercial.grid_power_pct") - 0.0) < 1e-9
    assert abs(v(cfg, "commercial.captive_re_pct") - 100.0) < 1e-9
    energy_mwh = 200.0 * 8760.0
    kpis = {"annual_load_mwh": energy_mwh, "max_grid_import_mw": 0.0}
    out = excel_style_energy_charges(cfg, kpis)
    assert abs(out["excel_grid_pct"] - 0.0) < 1e-9
    assert abs(out["excel_re_pct"] - 100.0) < 1e-9
    assert abs(out["excel_blended_rate_inr_per_kwh"] - 4.16) < 1e-9
    expected_cr = energy_mwh * 4.16 * 1000.0 / 1e7
    assert abs(out["excel_annual_energy_cr"] - expected_cr) < 0.05
    assert out["excel_savings_vs_discom_cr"] > 0


def test_power_pct_drives_re_alias_on_captive():
    """CAPTIVE Percentage of Solar/Wind/BESS power drives captive_re_pct; grid alias stays 0."""
    cfg = recompute_calculated(get_default_config())
    cfg["commercial"]["structure"]["value"] = "CAPTIVE"
    cfg["commercial"]["include_solar"]["value"] = True
    cfg["commercial"]["include_wind"]["value"] = True
    cfg["commercial"]["include_bess"]["value"] = False
    cfg["commercial"]["mix_solar_pct"]["value"] = 70.0
    cfg["commercial"]["mix_wind_pct"]["value"] = 30.0
    cfg = recompute_calculated(cfg)
    assert v(cfg, "commercial.include_discom") is False
    assert abs(v(cfg, "commercial.grid_power_pct") - 0.0) < 1e-9
    assert abs(v(cfg, "commercial.captive_re_pct") - 100.0) < 1e-9
    assert cfg["commercial"]["grid_power_pct"].get("editable") is False


def test_excel_wind_and_bess_stack_sum():
    from backend.financial.engine import excel_wind_rate_inr_per_kwh, excel_bess_rate_inr_per_kwh

    cfg = recompute_calculated(get_default_config())
    # Wind defaults mirror Solar: 3.5+1.04+0.15+0.05 = 4.16
    assert abs(excel_wind_rate_inr_per_kwh(cfg) - 4.16) < 1e-9
    assert abs(v(cfg, "commercial.excel_wind_total_inr_per_kwh") - 4.16) < 1e-9
    # BESS defaults are all 0
    assert abs(excel_bess_rate_inr_per_kwh(cfg) - 0.0) < 1e-9
    assert abs(v(cfg, "commercial.excel_bess_total_inr_per_kwh") - 0.0) < 1e-9


def test_excel_captive_solar_wind_blend():
    """CAPTIVE blend = Solar×S% + Wind×W% (no Discom)."""
    cfg = recompute_calculated(get_default_config())
    cfg["commercial"]["structure"]["value"] = "CAPTIVE"
    cfg["commercial"]["include_solar"]["value"] = True
    cfg["commercial"]["include_wind"]["value"] = True
    cfg["commercial"]["include_bess"]["value"] = False
    cfg["commercial"]["mix_solar_pct"]["value"] = 60.0
    cfg["commercial"]["mix_wind_pct"]["value"] = 40.0
    cfg = recompute_calculated(cfg)
    energy_mwh = 200.0 * 8760.0
    out = excel_style_energy_charges(cfg, {"annual_load_mwh": energy_mwh, "max_grid_import_mw": 0.0})
    expected = 4.16 * 0.6 + 4.16 * 0.4
    assert abs(out["excel_blended_rate_inr_per_kwh"] - expected) < 1e-9
    assert abs(out["excel_solar_power_pct"] - 60.0) < 1e-9
    assert abs(out["excel_wind_power_pct"] - 40.0) < 1e-9
    assert abs(out["excel_grid_pct"] - 0.0) < 1e-9


def test_excel_hybrid_discom_solar_blend():
    """HYBRID blends Discom×G% + Solar×S% from Architecture Excel stacks."""
    cfg = recompute_calculated(get_default_config())
    cfg["commercial"]["structure"]["value"] = "HYBRID"
    cfg["commercial"]["include_discom"]["value"] = True
    cfg["commercial"]["include_solar"]["value"] = True
    cfg["commercial"]["include_wind"]["value"] = False
    cfg["commercial"]["include_bess"]["value"] = False
    cfg["commercial"]["mix_discom_pct"]["value"] = 40.0
    cfg["commercial"]["mix_solar_pct"]["value"] = 60.0
    cfg = recompute_calculated(cfg)
    energy_mwh = 200.0 * 8760.0
    out = excel_style_energy_charges(cfg, {"annual_load_mwh": energy_mwh, "max_grid_import_mw": 0.0})
    expected = 8.75 * 0.4 + 4.16 * 0.6
    assert abs(out["excel_blended_rate_inr_per_kwh"] - expected) < 1e-9
    assert abs(out["excel_grid_pct"] - 40.0) < 1e-9
    assert abs(out["excel_solar_power_pct"] - 60.0) < 1e-9


def test_carbon_saved_vs_discom_from_mix():
    """Carbon saved = load×EF×(1 − grid%); CFE = RE mix %."""
    from backend.financial.engine import carbon_outcomes

    cfg = recompute_calculated(get_default_config())
    load_mwh = 1000.0
    energy = {
        "excel_grid_pct": 40.0,
        "excel_re_pct": 60.0,
        "annual_load_mwh": load_mwh,
    }
    out = carbon_outcomes(cfg, energy, energy_mwh=load_mwh)
    ef = float(v(cfg, "compliance.grid_emission_factor_tco2_per_mwh"))
    assert abs(out["cfe_pct"] - 60.0) < 1e-9
    assert abs(out["baseline_tco2"] - load_mwh * ef) < 1e-9
    assert abs(out["actual_tco2"] - load_mwh * 0.4 * ef) < 1e-9
    assert abs(out["carbon_saved_tco2"] - load_mwh * 0.6 * ef) < 1e-9


def test_commercial_breakdown_is_excel_mix_not_plant_opex():
    """Hybrid: Solar/Wind/BESS tariff stacks only; no auto BESS CAPEX when storage tariff is 0."""
    from backend.compliance.engine import evaluate_compliance
    from backend.financial.engine import evaluate_financial
    from backend.simulation.engine import run_simulation

    cfg = recompute_calculated(get_default_config())
    cfg["commercial"]["structure"]["value"] = "HYBRID"
    cfg["commercial"]["include_discom"]["value"] = True
    cfg["commercial"]["include_solar"]["value"] = True
    cfg["commercial"]["include_wind"]["value"] = True
    cfg["commercial"]["include_bess"]["value"] = True
    cfg["commercial"]["mix_discom_pct"]["value"] = 25.0
    cfg["commercial"]["mix_solar_pct"]["value"] = 35.0
    cfg["commercial"]["mix_wind_pct"]["value"] = 25.0
    cfg["commercial"]["mix_bess_pct"]["value"] = 15.0
    cfg["commercial"]["excel_bess_ppa_inr_per_kwh"]["value"] = 0.0
    cfg = recompute_calculated(cfg)

    bundle = run_simulation(cfg, structure="HYBRID")
    compliance = evaluate_compliance(bundle.config, bundle.kpis)
    fin = evaluate_financial(bundle.config, bundle.kpis, compliance, bundle.dispatch)
    br = fin["cost_breakdown"]
    assert "bess_ann_inr" not in br
    assert "bess_opex_inr" not in br
    assert fin["capex_total_inr"] == 0.0
    assert abs(fin["excel_tariff"]["bess_rate_inr_per_kwh"]) < 1e-9

    load = float(bundle.kpis["annual_load_mwh"])
    discom = float(fin["excel_tariff"]["discom_rate_inr_per_kwh"])
    solar = float(fin["excel_tariff"]["solar_rate_inr_per_kwh"])
    wind = float(fin["excel_tariff"]["wind_rate_inr_per_kwh"])
    # Tariff 0 → BESS% costs nothing; no CAPEX and no redistribute
    energy_sum = br["grid_energy_inr"] + br["solar_energy_or_ann_inr"] + br["wind_energy_or_ann_inr"]
    expected_blend = discom * 0.25 + solar * 0.35 + wind * 0.25
    assert abs(energy_sum - load * expected_blend * 1000.0) < 2.0

    peak = float(v(cfg, "load.peak_load_mw"))
    dem = float(v(cfg, "grid.demand_charge_inr_per_mw_month"))
    assert abs(br["demand_inr"] - peak * 0.25 * dem * 12.0) < 1.0


def test_captive_bess_oa_stack_forced_zero():
    cfg = recompute_calculated(get_default_config())
    cfg["commercial"]["structure"]["value"] = "CAPTIVE"
    cfg["commercial"]["excel_bess_ppa_inr_per_kwh"]["value"] = 2.0
    cfg["commercial"]["excel_bess_wheeling_inr_per_kwh"]["value"] = 0.5
    cfg = recompute_calculated(cfg)
    # Single storage tariff kept; OA lines cleared
    assert abs(v(cfg, "commercial.excel_bess_ppa_inr_per_kwh") - 2.0) < 1e-9
    assert v(cfg, "commercial.excel_bess_wheeling_inr_per_kwh") == 0.0
    assert abs(v(cfg, "commercial.excel_bess_total_inr_per_kwh") - 2.0) < 1e-9
    assert v(cfg, "commercial.apply_network_charges_to_bess") is False


def test_hybrid_storage_tariff_bills_bess_mix_not_capex():
    """Storage tariff > 0 → BESS% billed at ₹/kWh; CAPEX/OPEX not added."""
    from backend.compliance.engine import evaluate_compliance
    from backend.financial.engine import evaluate_financial
    from backend.simulation.engine import run_simulation

    cfg = recompute_calculated(get_default_config())
    cfg["commercial"]["structure"]["value"] = "HYBRID"
    cfg["commercial"]["include_discom"]["value"] = True
    cfg["commercial"]["include_solar"]["value"] = True
    cfg["commercial"]["include_wind"]["value"] = False
    cfg["commercial"]["include_bess"]["value"] = True
    cfg["commercial"]["mix_discom_pct"]["value"] = 40.0
    cfg["commercial"]["mix_solar_pct"]["value"] = 40.0
    cfg["commercial"]["mix_bess_pct"]["value"] = 20.0
    cfg["commercial"]["excel_bess_ppa_inr_per_kwh"]["value"] = 3.0
    cfg = recompute_calculated(cfg)

    bundle = run_simulation(cfg, structure="HYBRID")
    compliance = evaluate_compliance(bundle.config, bundle.kpis)
    fin = evaluate_financial(bundle.config, bundle.kpis, compliance, bundle.dispatch)
    br = fin["cost_breakdown"]
    assert "bess_ann_inr" not in br
    assert "bess_opex_inr" not in br
    assert "bess_energy_inr" in br
    assert fin["capex_total_inr"] == 0.0
    load = float(bundle.kpis["annual_load_mwh"])
    assert abs(br["bess_energy_inr"] - load * 0.20 * 3.0 * 1000.0) < 2.0
