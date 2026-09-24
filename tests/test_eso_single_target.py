from backend.compliance.engine import evaluate_eso
from config.defaults import get_default_config, recompute_calculated


def test_eso_single_target():
    cfg = recompute_calculated(get_default_config())
    assert "eso_target_pct" in cfg["compliance"]
    assert "eso_fy2026_27_pct" not in cfg["compliance"]
    assert "eso_active_year" not in cfg["compliance"]
    cfg["compliance"]["eso_applicability"]["value"] = "Applicable"
    cfg["compliance"]["eso_target_pct"]["value"] = 2.5
    cfg["compliance"]["eso_re_origin_min_pct"]["value"] = 85.0
    # Architecture BESS mix 1% of 1000 MWh = 10 MWh vs required 25 → Fail
    kpis = {
        "annual_load_mwh": 1000.0,
        "simulated_mix_bess_pct": 1.0,
        "target_mix_bess_pct": 1.0,
    }
    out = evaluate_eso(cfg, kpis)
    assert abs(out["target_pct"] - 2.5) < 1e-9
    assert abs(out["required_storage_mwh"] - 25.0) < 1e-9
    assert abs(out["actual_storage_energy_mwh"] - 10.0) < 1e-9
    assert out["actual_basis"] == "architecture_mix"
    assert out["status"] == "Fail"
    assert "trajectory" not in out
    assert "active_year" not in out


def test_eso_pass_when_bess_mix_meets_target():
    cfg = recompute_calculated(get_default_config())
    cfg["compliance"]["eso_applicability"]["value"] = "Applicable"
    cfg["compliance"]["eso_target_pct"]["value"] = 2.5
    kpis = {"annual_load_mwh": 1000.0, "simulated_mix_bess_pct": 5.0}
    out = evaluate_eso(cfg, kpis)
    assert out["status"] == "Pass"
    assert abs(out["actual_storage_energy_mwh"] - 50.0) < 1e-9
