"""24×7 CFE: TOD/availability (Solar+Wind+RE-BESS) vs Architecture mix for the bill."""

import numpy as np
import pytest

from backend.compliance.cfe_analytics import (
    analyze_cfe,
    architecture_cf_fraction,
    compute_hourly_cfe_pct,
)
from backend.compliance.engine import evaluate_cfe
from backend.simulation.engine import run_simulation
from config.defaults import get_default_config, recompute_calculated


def _cfg(**overrides):
    cfg = recompute_calculated(get_default_config())
    for path, value in overrides.items():
        section, key = path.split(".", 1)
        cfg[section][key]["value"] = value
    return recompute_calculated(cfg)


def test_compute_hourly_cfe_min_load_supply():
    """Availability path sums Solar+Wind+… streams."""
    load = np.array([100.0, 80.0, 50.0, 0.0])
    solar = np.array([40.0, 90.0, 10.0, 5.0])
    wind = np.array([20.0, 0.0, 10.0, 0.0])
    hydro = np.array([10.0, 0.0, 0.0, 0.0])
    nuclear = np.array([0.0, 5.0, 0.0, 0.0])
    bess = np.array([5.0, 0.0, 40.0, 0.0])
    cfe, supply, matched = compute_hourly_cfe_pct(
        load,
        solar_mw=solar,
        wind_mw=wind,
        hydro_mw=hydro,
        nuclear_mw=nuclear,
        bess_cf_discharge_mw=bess,
    )
    np.testing.assert_allclose(supply, [75.0, 95.0, 60.0, 5.0])
    np.testing.assert_allclose(matched, [75.0, 80.0, 50.0, 0.0])
    np.testing.assert_allclose(cfe, [75.0, 100.0, 100.0, 100.0])


def test_cf_fraction_flat_override_still_works():
    """Explicit cf_fraction remains available for tests — not the product path."""
    load = np.array([100.0, 100.0, 100.0, 100.0])
    cfe, supply, matched = compute_hourly_cfe_pct(load, cf_fraction=0.40)
    np.testing.assert_allclose(supply, [40.0, 40.0, 40.0, 40.0])
    np.testing.assert_allclose(cfe, [40.0, 40.0, 40.0, 40.0])
    np.testing.assert_allclose(matched, supply)


def test_night_solar_zero_lowers_cfe_without_wind_bess():
    """Solar-only at night → CFE ≈ 0; day hours can still be high."""
    load = np.full(4, 100.0)
    solar = np.array([80.0, 80.0, 0.0, 0.0])  # last two = night
    wind = np.zeros(4)
    cfe, supply, _ = compute_hourly_cfe_pct(load, solar_mw=solar, wind_mw=wind)
    assert cfe[0] == pytest.approx(80.0)
    assert cfe[2] == pytest.approx(0.0)
    assert supply[2] == pytest.approx(0.0)


def test_architecture_cf_fraction_from_config():
    cfg = _cfg(
        **{
            "commercial.structure": "CAPTIVE",
            "commercial.include_solar": True,
            "commercial.include_wind": True,
            "commercial.include_bess": False,
            "commercial.include_discom": False,
            "commercial.mix_solar_pct": 25.0,
            "commercial.mix_wind_pct": 25.0,
            "commercial.mix_bess_pct": 0.0,
            "commercial.mix_discom_pct": 0.0,
        }
    )
    assert architecture_cf_fraction(cfg) == pytest.approx(1.0)

    hyb = _cfg(
        **{
            "commercial.structure": "HYBRID",
            "commercial.include_discom": True,
            "commercial.include_solar": True,
            "commercial.include_wind": True,
            "commercial.include_bess": False,
            "commercial.mix_discom_pct": 60.0,
            "commercial.mix_solar_pct": 20.0,
            "commercial.mix_wind_pct": 20.0,
            "commercial.mix_bess_pct": 0.0,
        }
    )
    assert architecture_cf_fraction(hyb) == pytest.approx(0.40, abs=0.02)


def test_analyze_cfe_performance_blocks():
    n = 48
    load = np.full(n, 100.0)
    supply = np.concatenate([np.full(24, 90.0), np.full(24, 50.0)])
    matched = np.minimum(load, supply)
    cfe = matched / load * 100.0
    cfg = _cfg(**{"compliance.hourly_cfe_target_pct": 80.0})
    out = analyze_cfe(
        cfg,
        cfe,
        load_mw=load,
        cf_supply_mw=supply,
        matched_cf_mw=matched,
    )
    assert "Solar_available" in out["formula"] or "TOD" in out["formula"]
    assert out["annual_cfe_pct"] == pytest.approx(70.0, abs=1e-6)
    assert out["performance"]["annual"]["matched_cf_mwh"] == pytest.approx(3360.0)
    assert len(out["performance"]["hourly_of_day"]) == 24
    assert len(out["performance"]["daily"]) >= 2
    assert len(out["performance"]["monthly"]) >= 1


def test_simulation_solar_shape_zero_at_night():
    """Annual solar ≈ mix%×load, but night hours have ~0 solar from TOD shape."""
    cfg = _cfg(
        **{
            "commercial.structure": "HYBRID",
            "commercial.include_discom": True,
            "commercial.include_solar": True,
            "commercial.include_wind": True,
            "commercial.include_bess": False,
            "commercial.mix_discom_pct": 40.0,
            "commercial.mix_solar_pct": 30.0,
            "commercial.mix_wind_pct": 30.0,
            "commercial.mix_bess_pct": 0.0,
            "solar.sunrise_hour": 6.0,
            "solar.sunset_hour": 18.0,
        }
    )
    bundle = run_simulation(cfg, structure="HYBRID")
    load = bundle.dispatch.load_mw
    solar = bundle.dispatch.solar_mw
    from backend.simulation.calendar import get_calendar

    cal = get_calendar(len(load))
    night = cal.hour_of_day < 6
    # Night hours: solar near zero from TOD shape
    assert float(np.mean(solar[night])) < float(np.mean(solar[~night])) * 0.05 + 1e-6
    assert float(np.max(solar[night])) < 1e-6 or float(np.mean(solar[night])) < 0.01 * float(np.mean(load))
    # Annual contract energy still tracks Architecture mix
    assert float(solar.sum()) == pytest.approx(float(load.sum()) * 0.30, rel=0.02)
    assert float(bundle.dispatch.wind_mw.sum()) == pytest.approx(float(load.sum()) * 0.30, rel=0.02)
    # Bill shares stay Architecture mix
    assert bundle.kpis["simulated_mix_solar_pct"] == pytest.approx(30.0)
    assert bundle.kpis["simulated_mix_re_pct"] == pytest.approx(60.0)
    assert bundle.kpis["unserved_mwh"] == 0.0


def test_simulation_min_cfe_below_architecture_mix_at_night():
    """Without enough night wind/BESS, min hourly CFE < Architecture RE mix %."""
    cfg = _cfg(
        **{
            "commercial.structure": "HYBRID",
            "commercial.include_discom": True,
            "commercial.include_solar": True,
            "commercial.include_wind": False,
            "commercial.include_bess": False,
            "commercial.mix_discom_pct": 50.0,
            "commercial.mix_solar_pct": 50.0,
            "commercial.mix_wind_pct": 0.0,
            "commercial.mix_bess_pct": 0.0,
            "compliance.hourly_cfe_target_pct": 35.0,
        }
    )
    bundle = run_simulation(cfg, structure="HYBRID")
    ca = bundle.kpis["cfe_analytics"]
    assert ca["architecture_cf_pct"] == pytest.approx(50.0, abs=1.0)
    # Night solar = 0 → min CFE well below contracted 50%
    assert ca["min_hourly_cfe_pct"] < ca["architecture_cf_pct"] - 10.0
    assert ca["passed"] is False  # some night hours < 35%


def test_simulation_captive_with_wind_can_pass_modest_cfe():
    """CAPTIVE Solar+Wind: contracted mix 100%; night CFE from wind (not firm solar)."""
    cfg = _cfg(
        **{
            "commercial.structure": "CAPTIVE",
            "commercial.include_solar": True,
            "commercial.include_wind": True,
            "commercial.include_bess": False,
            "commercial.include_discom": False,
            "commercial.mix_solar_pct": 40.0,
            "commercial.mix_wind_pct": 60.0,
            "commercial.mix_bess_pct": 0.0,
            "commercial.mix_discom_pct": 0.0,
            "compliance.hourly_cfe_target_pct": 20.0,
            "compliance.annual_re_target_pct": 20.0,
        }
    )
    bundle = run_simulation(cfg, structure="CAPTIVE")
    ca = bundle.kpis["cfe_analytics"]
    assert ca["architecture_cf_pct"] == pytest.approx(100.0, abs=0.1)
    # Availability annual RE / CFE is from dispatch, not flat 100%
    assert bundle.kpis["annual_re_pct"] <= 100.0 + 1e-6
    assert "TOD" in (bundle.kpis.get("cfe_formula") or "") or "Solar_available" in (
        bundle.kpis.get("cfe_formula") or ""
    )
    # Bill still Architecture
    assert bundle.kpis["simulated_mix_re_pct"] == pytest.approx(100.0)


def test_simulation_bess_mix_derives_storage():
    cfg = _cfg(
        **{
            "commercial.structure": "HYBRID",
            "commercial.include_discom": True,
            "commercial.include_solar": True,
            "commercial.include_wind": True,
            "commercial.include_bess": True,
            "commercial.mix_discom_pct": 20.0,
            "commercial.mix_solar_pct": 40.0,
            "commercial.mix_wind_pct": 20.0,
            "commercial.mix_bess_pct": 20.0,
        }
    )
    bundle = run_simulation(cfg, structure="HYBRID")
    assert bundle.kpis["bess_mw"] > 0.0
    assert bundle.kpis["bess_mwh"] > 0.0
    assert bundle.kpis["simulated_mix_bess_pct"] == pytest.approx(20.0)


def test_simulation_attaches_cfe_performance():
    bundle = run_simulation(_cfg(), structure="HYBRID")
    ca = bundle.kpis["cfe_analytics"]
    assert "performance" in ca
    assert "hourly_of_day" in ca["performance"]
    assert "daily" in ca["performance"]
    assert "monthly" in ca["performance"]
    assert "annual" in ca["performance"]
    assert bundle.kpis["cfe_formula"]
    assert len(bundle.dispatch.cf_supply_mw) == len(bundle.dispatch.load_mw)
    assert len(bundle.dispatch.matched_cf_mw) == len(bundle.dispatch.load_mw)
    load_sum = float(bundle.dispatch.load_mw.sum())
    matched_sum = float(bundle.dispatch.matched_cf_mw.sum())
    assert ca["annual_cfe_pct"] == pytest.approx(matched_sum / load_sum * 100.0, abs=1e-4)
    # Availability: min hourly typically below contracted Architecture CF %
    assert ca["min_hourly_cfe_pct"] <= ca["architecture_cf_pct"] + 1.0
