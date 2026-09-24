"""Architecture mix % is contracted energy share (buyer path — no plant MW)."""

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


def test_captive_forces_discom_off():
    cfg = _cfg(
        **{
            "commercial.structure": "CAPTIVE",
            "commercial.include_discom": True,
            "commercial.include_solar": True,
            "commercial.include_wind": False,
            "commercial.include_bess": False,
            "commercial.mix_solar_pct": 100.0,
        }
    )
    out = apply_architecture_asset_flags(deepcopy(cfg))
    assert v(out, "commercial.include_discom") is False
    assert "bess" not in out
    assert "capacity_mw" not in out.get("solar", {})


def test_hybrid_keeps_discom_flag():
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
        }
    )
    out = apply_architecture_asset_flags(deepcopy(cfg))
    assert v(out, "commercial.include_discom") is True
    assert v(out, "commercial.include_solar") is True
    assert v(out, "commercial.include_bess") is True


def test_legacy_open_access_maps_to_hybrid_flags():
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
        }
    )
    cfg = merge_missing_defaults(cfg)
    cfg = recompute_calculated(cfg)
    assert v(cfg, "commercial.structure") == "HYBRID"
    out = apply_architecture_asset_flags(deepcopy(cfg))
    assert v(out, "commercial.include_discom") is True
    assert "bess" not in out


def test_validate_rejects_mix_not_summing_to_100():
    cfg = _cfg(
        **{
            "commercial.structure": "CAPTIVE",
            "commercial.include_discom": False,
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
            "commercial.include_discom": False,
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
    cfg = merge_missing_defaults(cfg)
    cfg = recompute_calculated(cfg)
    keys = ["mix_solar_pct", "mix_wind_pct", "mix_bess_pct"]
    total = sum(float(cfg["commercial"][k]["value"]) for k in keys)
    assert abs(total - 100.0) < 0.05


def test_plant_leftovers_stripped_from_defaults():
    cfg = get_default_config()
    assert "bess" not in cfg
    assert "optimization" not in cfg
    assert "capacity_mw" not in cfg["solar"]
    assert "capacity_mw" not in cfg["wind"]
    assert "capex_inr_per_mw" not in cfg["solar"]
    assert "financing_enabled" not in cfg["financial"]
    assert "max_import_mw" not in cfg["grid"]
