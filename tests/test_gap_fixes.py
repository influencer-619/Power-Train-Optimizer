"""Gap fixes: BESS RTE, financing, target vs simulated power % blend."""

from __future__ import annotations

import pytest

from backend.compliance.engine import evaluate_compliance
from backend.financial.engine import excel_style_energy_charges, evaluate_financial
from backend.simulation.engine import run_simulation
from config.defaults import get_default_config, recompute_calculated, v


def _cfg(**overrides):
    cfg = recompute_calculated(get_default_config())
    for path, value in overrides.items():
        section, key = path.split(".", 1)
        cfg[section][key]["value"] = value
    return recompute_calculated(cfg)


def test_bess_efficiency_defaults_and_losses():
    """Without BESS mix: no derived storage; Simulated bill shares = Architecture mix."""
    cfg = _cfg(
        **{
            "commercial.include_bess": False,
            "commercial.mix_bess_pct": 0.0,
        }
    )
    with pytest.raises(KeyError):
        v(cfg, "bess.charge_efficiency_pct")
    bundle = run_simulation(cfg, structure="HYBRID")
    assert bundle.kpis["bess_mw"] == pytest.approx(0.0, abs=1e-9)
    assert bundle.kpis["bess_losses_mwh"] == pytest.approx(0.0, abs=1e-6)
    assert "simulated_mix_grid_pct" in bundle.kpis
    assert "simulated_mix_re_pct" in bundle.kpis
    re = (
        float(bundle.kpis["target_mix_solar_pct"])
        + float(bundle.kpis["target_mix_wind_pct"])
        + float(bundle.kpis["target_mix_bess_pct"])
    )
    assert bundle.kpis["simulated_mix_re_pct"] == pytest.approx(re, abs=1e-6)


def test_ideal_bess_zero_losses_when_bess_off():
    cfg = _cfg(**{"commercial.include_bess": False, "commercial.mix_bess_pct": 0.0})
    bundle = run_simulation(cfg, structure="HYBRID")
    assert bundle.kpis["bess_losses_mwh"] == pytest.approx(0.0, abs=1e-6)
    assert bundle.kpis["bess_mw"] == pytest.approx(0.0, abs=1e-9)


def test_excel_blend_uses_simulated_shares_when_selected():
    cfg = _cfg()
    cfg["commercial"]["structure"]["value"] = "CAPTIVE"
    cfg["commercial"]["include_solar"]["value"] = True
    cfg["commercial"]["include_wind"]["value"] = False
    cfg["commercial"]["include_bess"]["value"] = False
    cfg["commercial"]["mix_solar_pct"]["value"] = 100.0
    cfg["commercial"]["cost_blend_basis"]["value"] = "SIMULATED_ENERGY_SHARE"
    cfg = recompute_calculated(cfg)
    assert v(cfg, "commercial.include_discom") is False
    kpis = {
        "annual_load_mwh": 200.0 * 8760.0,
        "max_grid_import_mw": 50.0,
        "simulated_mix_grid_pct": 25.0,
        "simulated_mix_re_pct": 75.0,
        "simulated_mix_solar_pct": 75.0,
        "simulated_mix_wind_pct": 0.0,
    }
    out = excel_style_energy_charges(cfg, kpis)
    assert out["cost_blend_basis"] == "SIMULATED_ENERGY_SHARE"
    assert abs(out["excel_grid_pct"] - 25.0) < 1e-9
    assert abs(out["excel_re_pct"] - 75.0) < 1e-9
    assert abs(out["target_grid_pct"] - 0.0) < 1e-9
    assert abs(out["target_re_pct"] - 100.0) < 1e-9
    assert abs(out["excel_blended_rate_inr_per_kwh"] - (8.75 * 0.25 + 4.16 * 0.75)) < 1e-9


def test_excel_blend_target_power_pct_default():
    cfg = _cfg()
    cfg["commercial"]["structure"]["value"] = "CAPTIVE"
    cfg["commercial"]["include_solar"]["value"] = True
    cfg["commercial"]["include_wind"]["value"] = False
    cfg["commercial"]["include_bess"]["value"] = False
    cfg["commercial"]["mix_solar_pct"]["value"] = 100.0
    cfg = recompute_calculated(cfg)
    assert v(cfg, "commercial.cost_blend_basis") == "TARGET_POWER_PCT"
    assert v(cfg, "commercial.include_discom") is False
    energy_mwh = 200.0 * 8760.0
    kpis = {
        "annual_load_mwh": energy_mwh,
        "max_grid_import_mw": 0.0,
        "simulated_mix_grid_pct": 10.0,
        "simulated_mix_re_pct": 90.0,
    }
    out = excel_style_energy_charges(cfg, kpis)
    assert abs(out["excel_grid_pct"] - 0.0) < 1e-9
    assert abs(out["excel_re_pct"] - 100.0) < 1e-9


def test_financing_disabled_on_consumer_tariff_path():
    """Plant CAPEX/financing are off — DC buys Solar/Wind/BESS via tariff stacks only."""
    cfg = _cfg(**{"commercial.structure": "HYBRID", "financial.tax_pct": 0.0})
    assert "financing_enabled" not in cfg.get("financial", {})
    bundle = run_simulation(cfg, structure="HYBRID")
    compliance = evaluate_compliance(bundle.config, bundle.kpis)
    fin = evaluate_financial(cfg, bundle.kpis, compliance, bundle.dispatch)
    assert fin["capex_total_inr"] == 0.0
    assert fin["financing"]["enabled"] is False
    assert "bess_ann_inr" not in fin["cost_breakdown"]
    assert "include_generation_capex" not in bundle.config.get("commercial", {})
    assert "bess" not in bundle.config


def test_priorities_not_editable():
    """Optimization section retired — plant capacity search is not part of the buyer app."""
    cfg = get_default_config()
    assert "optimization" not in cfg


def test_simulated_shares_follow_setup_mix_contracts():
    """DC buyer: Simulated mix = Architecture contracted mix % (no plant BESS MW)."""
    from backend.simulation.engine import apply_setup_energy_contracts

    cfg = _cfg()
    cfg["commercial"]["structure"]["value"] = "HYBRID"
    cfg["commercial"]["include_discom"]["value"] = True
    cfg["commercial"]["include_solar"]["value"] = True
    cfg["commercial"]["include_wind"]["value"] = True
    cfg["commercial"]["include_bess"]["value"] = False
    cfg["commercial"]["mix_discom_pct"]["value"] = 25.0
    cfg["commercial"]["mix_solar_pct"]["value"] = 50.0
    cfg["commercial"]["mix_wind_pct"]["value"] = 25.0
    cfg["commercial"]["mix_bess_pct"]["value"] = 0.0
    cfg["commercial"]["cost_blend_basis"]["value"] = "SIMULATED_ENERGY_SHARE"
    cfg = recompute_calculated(cfg)

    bundle = run_simulation(cfg, structure="HYBRID")
    load = float(bundle.kpis["annual_load_mwh"])
    assert load > 0
    assert float(bundle.profiles["solar_annual_mwh"]) == pytest.approx(load * 0.50, rel=0.02)
    assert float(bundle.profiles["wind_annual_mwh"]) == pytest.approx(load * 0.25, rel=0.02)
    assert bundle.kpis["bess_mw"] == pytest.approx(0.0, abs=1e-9)
    assert bundle.kpis["bess_mwh"] == pytest.approx(0.0, abs=1e-9)
    # Contracted delivery: Simulated = Architecture mix
    assert bundle.kpis["simulated_mix_grid_pct"] == pytest.approx(25.0, abs=1e-6)
    assert bundle.kpis["simulated_mix_solar_pct"] == pytest.approx(50.0, abs=1e-6)
    assert bundle.kpis["simulated_mix_wind_pct"] == pytest.approx(25.0, abs=1e-6)
    assert bundle.kpis["simulated_mix_re_pct"] == pytest.approx(75.0, abs=1e-6)
    fin = evaluate_financial(cfg, bundle.kpis, evaluate_compliance(bundle.config, bundle.kpis), bundle.dispatch)
    assert fin["excel_tariff"]["cost_blend_basis"] == "SIMULATED_ENERGY_SHARE"
    assert fin["excel_tariff"]["simulated_re_pct"] == pytest.approx(75.0, abs=1e-6)
    assert fin["excel_tariff"]["target_re_pct"] == pytest.approx(75.0, abs=1e-6)

    import numpy as np

    load_mw = np.ones(100) * 2.0
    solar_mw = np.ones(100) * 10.0
    wind_mw = np.ones(100) * 4.0
    s2, w2, bp, be, g = apply_setup_energy_contracts(cfg, load_mw, solar_mw, wind_mw)
    assert float(s2.sum()) == pytest.approx(100.0, rel=1e-6)  # 50% of 200 MWh
    assert float(w2.sum()) == pytest.approx(50.0, rel=1e-6)  # 25% of 200 MWh
    assert bp == pytest.approx(0.0, abs=1e-9)
    assert be == pytest.approx(0.0, abs=1e-9)
    assert g == pytest.approx(2.0, abs=1e-9)
