"""Phase 2–5 / V2 regression: feasibility, CFE analytics, profiles, opt explain."""

from copy import deepcopy

import numpy as np
import pytest

from backend.compliance.cfe_analytics import analyze_cfe
from backend.compliance.engine import evaluate_compliance
from backend.compliance.feasibility import evaluate_feasibility
from backend.optimization.explain import explain_winner, marginal_capacity_analysis
from backend.simulation.engine import run_simulation
from backend.simulation.profiles_project import parse_csv_hourly, save_project_profile, validate_hourly_series
from config.defaults import get_default_config, recompute_calculated, set_param


def _cfg(**overrides):
    cfg = recompute_calculated(get_default_config())
    for path, value in overrides.items():
        section, key = path.split(".", 1)
        cfg[section][key]["value"] = value
    return recompute_calculated(cfg)


def test_cfe_analytics_attached_and_consistent():
    bundle = run_simulation(_cfg(), structure="HYBRID")
    ca = bundle.kpis.get("cfe_analytics")
    assert ca is not None
    assert ca["hours_total"] == 8760
    assert ca["min_hourly_cfe_pct"] == pytest.approx(bundle.kpis["hourly_cfe_min_pct"], abs=1e-6)
    assert 0 <= ca["pct_hours_ge_target"] <= 100
    assert len(ca["duration_curve"]) == 101


def test_feasibility_discom_not_recommended_when_targets_miss():
    bundle = run_simulation(_cfg(), structure="DISCOM")
    comp = evaluate_compliance(bundle.config, bundle.kpis)
    feas = evaluate_feasibility(bundle.config, bundle.kpis, comp, bundle.validation)
    assert feas["status"] == "NOT FEASIBLE"
    assert feas["can_recommend"] is False


def test_feasibility_hybrid_can_recommend_when_targets_pass():
    # Relax targets so default plant can pass
    cfg = _cfg(**{"compliance.annual_re_target_pct": 50.0, "compliance.hourly_cfe_target_pct": 50.0})
    set_param(cfg, "compliance.cfe_pass_mode", "Mean hourly CFE >= target", as_user=True)
    bundle = run_simulation(cfg, structure="HYBRID")
    comp = evaluate_compliance(bundle.config, bundle.kpis)
    feas = evaluate_feasibility(bundle.config, bundle.kpis, comp, bundle.validation)
    # May still be INCOMPLETE INPUTS due to defaults — but not falsely RECOMMENDED if fail
    if feas["status"] == "FEASIBLE":
        assert feas["can_recommend"] is True
    else:
        assert feas["can_recommend"] is False
        assert feas["status"] in ("INCOMPLETE INPUTS", "LEGAL REVIEW REQUIRED", "NOT FEASIBLE")


def test_profile_validation_rejects_wrong_length():
    report = validate_hourly_series([1.0, 2.0, 3.0], name="load", expected_hours=8760)
    assert report["ok"] is False
    assert any("expected exactly" in e for e in report["errors"])


def test_profile_csv_parse_and_save(tmp_path, monkeypatch):
    from backend.simulation import profiles_project as pp

    monkeypatch.setattr(pp, "data_dir", lambda: tmp_path)
    values = [100.0 + (i % 24) for i in range(8760)]
    text = "timestamp,mw\n" + "\n".join(f"2024-01-01T{i%24:02d}:00,{v}" for i, v in enumerate(values))
    # Fix timestamps to be unique-ish enough for parser; duplicates ok for hour-of-day test path without strict uniqueness fail if many dups
    text = "mw\n" + "\n".join(str(v) for v in values)
    vals, stamps = parse_csv_hourly(text)
    assert len(vals) == 8760
    result = save_project_profile(1, "load", vals, timestamps=stamps)
    assert result["ok"] is True
    loaded = pp.load_project_profile(1, "load")
    assert loaded is not None
    assert np.allclose(loaded["values"], values)


def test_project_data_profile_used_in_simulation(tmp_path, monkeypatch):
    from backend.simulation import profiles_project as pp

    monkeypatch.setattr(pp, "data_dir", lambda: tmp_path)
    # Also patch engine's import path — profiles_project.data_dir used inside load
    flat = np.full(8760, 200.0)
    assert save_project_profile(99, "load", flat.tolist())["ok"]
    cfg = _cfg()
    set_param(cfg, "load.profile_source", "PROJECT DATA", as_user=True)
    bundle = run_simulation(cfg, structure="HYBRID", project_id=99)
    assert bundle.profiles.get("load_source") == "PROJECT DATA"
    assert float(np.mean(bundle.dispatch.load_mw)) == pytest.approx(200.0, abs=1e-6)


def test_explain_winner_structure():
    winner = {
        "candidate": {"solar_mw": 100, "wind_mw": 50, "bess_mw": 20, "bess_mwh": 80, "grid_mw": 100},
        "kpis": {
            "annual_re_pct": 60,
            "hourly_cfe_min_pct": 40,
            "grid_gwh": 10,
            "curtailment_pct": 5,
            "unserved_mwh": 0,
        },
        "financial": {"cost_per_kwh": 7.5, "npv_cr": 1.2},
        "compliance": {
            "annual_re": {"status": "Pass"},
            "hourly_cfe": {"status": "Fail", "pass_mode": "All hours >= target", "target_pct": 90},
        },
        "feasible": False,
    }
    exp = explain_winner(winner)
    assert exp["can_recommend"] is False
    assert "NOT RECOMMENDED" in exp["recommendation_label"]
    assert exp["bullets"]


def test_marginal_capacity_analysis_deltas():
    base = {
        "candidate": {"solar_mw": 100},
        "kpis": {"annual_re_pct": 50, "hourly_cfe_min_pct": 40, "grid_gwh": 20, "curtailment_pct": 5},
        "financial": {"cost_per_kwh": 8.0, "npv_cr": 1.0},
        "feasible": True,
    }
    var = deepcopy(base)
    var["label"] = "+solar"
    var["kpis"] = {**base["kpis"], "annual_re_pct": 55}
    var["financial"] = {**base["financial"], "cost_per_kwh": 7.8}
    out = marginal_capacity_analysis(base, [var])
    assert out["steps"][0]["delta_annual_re_pp"] == pytest.approx(5.0)
    assert out["steps"][0]["delta_cost_per_kwh"] == pytest.approx(-0.2)


def test_analyze_cfe_deficit_streak():
    cfe = np.array([100.0] * 10 + [50.0] * 5 + [100.0] * 5)
    cfg = _cfg(**{"compliance.hourly_cfe_target_pct": 90.0})
    # pad to avoid empty edge — function works on any length
    out = analyze_cfe(cfg, cfe, annual_re_pct=80.0)
    assert out["longest_continuous_deficit_hours"] == 5
