"""Architecture mix % scales configured capacities for CAPTIVE / HYBRID / OA."""

from __future__ import annotations

from copy import deepcopy

from backend.simulation.engine import apply_architecture_asset_flags
from backend.simulation.validation import validate_config
from config.defaults import (
    ensure_architecture_mix_sums_to_100,
    get_default_config,
    merge_missing_defaults,
    recompute_calculated,
    v,
)


def _cfg(**overrides):
    cfg = recompute_calculated(get_default_config())
    for path, val in overrides.items():
        section, key = path.split(".", 1)
        cfg[section][key]["value"] = val
    return cfg


def test_captive_mix_scales_solar_wind_bess_not_grid():
    cfg = _cfg(
        **{
            "commercial.structure": "CAPTIVE",
            "commercial.include_solar": True,
            "commercial.include_wind": True,
            "commercial.include_bess": True,
            "commercial.mix_solar_pct": 50.0,
            "commercial.mix_wind_pct": 30.0,
            "commercial.mix_bess_pct": 20.0,
            "solar.capacity_mw": 400.0,
            "wind.capacity_mw": 200.0,
            "bess.power_mw": 100.0,
            "bess.energy_mwh": 400.0,
            "grid.max_import_mw": 250.0,
        }
    )
    out = apply_architecture_asset_flags(deepcopy(cfg))
    assert v(out, "solar.capacity_mw") == 200.0
    assert v(out, "wind.capacity_mw") == 60.0
    assert v(out, "bess.power_mw") == 20.0
    assert v(out, "bess.energy_mwh") == 80.0
    # Captive forces DISCOM off → grid import zeroed (mix_discom ignored)
    assert v(out, "grid.max_import_mw") == 0.0


def test_hybrid_mix_scales_discom_and_re():
    cfg = _cfg(
        **{
            "commercial.structure": "HYBRID",
            "commercial.include_discom": True,
            "commercial.include_solar": True,
            "commercial.include_wind": False,
            "commercial.include_bess": True,
            "commercial.mix_discom_pct": 25.0,
            "commercial.mix_solar_pct": 50.0,
            "commercial.mix_bess_pct": 25.0,
            "solar.capacity_mw": 450.0,
            "wind.capacity_mw": 300.0,
            "bess.power_mw": 150.0,
            "bess.energy_mwh": 600.0,
            "grid.max_import_mw": 250.0,
        }
    )
    out = apply_architecture_asset_flags(deepcopy(cfg))
    assert v(out, "grid.max_import_mw") == 62.5
    assert v(out, "solar.capacity_mw") == 225.0
    assert v(out, "wind.capacity_mw") == 0.0
    assert v(out, "bess.power_mw") == 37.5
    assert v(out, "bess.energy_mwh") == 150.0


def test_open_access_mix_discom_solar():
    cfg = _cfg(
        **{
            "commercial.structure": "OPEN_ACCESS",
            "commercial.include_discom": True,
            "commercial.include_solar": True,
            "commercial.include_wind": True,
            "commercial.include_bess": False,
            "commercial.mix_discom_pct": 20.0,
            "commercial.mix_solar_pct": 50.0,
            "commercial.mix_wind_pct": 30.0,
            "solar.capacity_mw": 500.0,
            "wind.capacity_mw": 250.0,
            "bess.power_mw": 150.0,
            "bess.energy_mwh": 600.0,
            "grid.max_import_mw": 200.0,
        }
    )
    out = apply_architecture_asset_flags(deepcopy(cfg))
    assert v(out, "grid.max_import_mw") == 40.0
    assert v(out, "solar.capacity_mw") == 250.0
    assert v(out, "wind.capacity_mw") == 75.0
    assert v(out, "bess.power_mw") == 0.0
    assert v(out, "bess.energy_mwh") == 0.0


def test_validate_rejects_mix_not_summing_to_100():
    cfg = _cfg(
        **{
            "commercial.structure": "CAPTIVE",
            "commercial.include_solar": True,
            "commercial.include_wind": True,
            "commercial.include_bess": True,
            "commercial.mix_solar_pct": 50.0,
            "commercial.mix_wind_pct": 25.0,
            "commercial.mix_bess_pct": 10.0,
        }
    )
    issues = validate_config(cfg)
    assert any("must sum to 100" in i["message"] for i in issues if i["level"] == "error")


def test_validate_accepts_mix_summing_to_100():
    cfg = _cfg(
        **{
            "commercial.structure": "CAPTIVE",
            "commercial.include_solar": True,
            "commercial.include_wind": True,
            "commercial.include_bess": True,
            "commercial.mix_solar_pct": 40.0,
            "commercial.mix_wind_pct": 35.0,
            "commercial.mix_bess_pct": 25.0,
        }
    )
    issues = validate_config(cfg)
    assert not any("must sum to 100" in i["message"] for i in issues)


def test_ensure_equalizes_old_independent_mixes():
    cfg = get_default_config()
    cfg["commercial"]["structure"]["value"] = "CAPTIVE"
    cfg["commercial"]["include_discom"]["value"] = False
    cfg["commercial"]["include_solar"]["value"] = True
    cfg["commercial"]["include_wind"]["value"] = True
    cfg["commercial"]["include_bess"]["value"] = True
    # Legacy independent 100%s
    cfg["commercial"]["mix_solar_pct"]["value"] = 100.0
    cfg["commercial"]["mix_wind_pct"]["value"] = 100.0
    cfg["commercial"]["mix_bess_pct"]["value"] = 100.0
    ensure_architecture_mix_sums_to_100(cfg)
    total = (
        float(cfg["commercial"]["mix_solar_pct"]["value"])
        + float(cfg["commercial"]["mix_wind_pct"]["value"])
        + float(cfg["commercial"]["mix_bess_pct"]["value"])
    )
    assert abs(total - 100.0) < 0.05


def test_merge_equalizes_captive_defaults():
    cfg = get_default_config()
    cfg["commercial"]["structure"]["value"] = "CAPTIVE"
    cfg["commercial"]["include_discom"]["value"] = False
    merge_missing_defaults(cfg)
    total = (
        float(cfg["commercial"]["mix_solar_pct"]["value"])
        + float(cfg["commercial"]["mix_wind_pct"]["value"])
        + float(cfg["commercial"]["mix_bess_pct"]["value"])
    )
    assert abs(total - 100.0) < 0.05
