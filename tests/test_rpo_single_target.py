from backend.compliance.engine import evaluate_rpo_rco
from config.defaults import get_default_config, recompute_calculated


def test_rpo_rco_integrated_defaults():
    cfg = recompute_calculated(get_default_config())
    assert "rpo_rco_target_pct" in cfg["compliance"]
    assert "rpo_rco_applicability" in cfg["compliance"]
    assert "rpo_target_pct" not in cfg["compliance"]
    assert "rco_target_pct" not in cfg["compliance"]
    assert "rpo_applicability" not in cfg["compliance"]
    assert "rco_applicability" not in cfg["compliance"]


def test_rpo_rco_architecture_mix():
    cfg = recompute_calculated(get_default_config())
    cfg["compliance"]["rpo_rco_applicability"]["value"] = "Applicable"
    cfg["compliance"]["rpo_rco_target_pct"]["value"] = 40.0
    cfg["compliance"]["rpo_rco_compliance_route"]["value"] = "Buyout"
    cfg["commercial"]["mix_solar_pct"]["value"] = 30.0
    cfg["commercial"]["mix_wind_pct"]["value"] = 20.0
    cfg["commercial"]["mix_bess_pct"]["value"] = 0.0
    kpis = {
        "annual_load_mwh": 1000.0,
        "re_serving_load_mwh": 100.0,
        "annual_re_pct": 10.0,
        "target_mix_solar_pct": 30.0,
        "target_mix_wind_pct": 20.0,
        "target_mix_bess_pct": 0.0,
    }
    out = evaluate_rpo_rco(cfg, kpis)
    assert out["metric"] == "RPO/RCO"
    assert out["actual_basis"] == "architecture_mix"
    assert abs(out["actual_pct"] - 50.0) < 1e-9
    assert out["status"] == "Pass"
    assert abs(out["gap_mwh"]) < 1e-9


def test_rpo_rco_zero_mix_fail():
    """Zero Architecture RE mix → RPO uses mix (not profile dispatch)."""
    cfg = recompute_calculated(get_default_config())
    cfg["compliance"]["rpo_rco_applicability"]["value"] = "Applicable"
    cfg["compliance"]["rpo_rco_target_pct"]["value"] = 50.0
    for key in ("mix_solar_pct", "mix_wind_pct", "mix_bess_pct"):
        cfg["commercial"][key]["value"] = 0.0
    kpis = {
        "annual_load_mwh": 1000.0,
        "annual_re_pct": 0.0,
        "simulated_mix_re_pct": 0.0,
        "re_serving_load_mwh": 400.0,  # must be ignored
        "annual_solar_mwh": 300.0,
        "annual_wind_mwh": 100.0,
        "target_mix_solar_pct": 0.0,
        "target_mix_wind_pct": 0.0,
        "target_mix_bess_pct": 0.0,
    }
    out = evaluate_rpo_rco(cfg, kpis)
    assert out["actual_basis"] == "architecture_mix"
    assert abs(out["actual_pct"]) < 1e-9
    assert abs(out["gap_mwh"] - 500.0) < 1e-9
    assert out["status"] == "Fail"
    assert out["compliance_cost_inr"] > 0
