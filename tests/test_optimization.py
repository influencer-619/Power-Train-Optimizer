from config.defaults import get_default_config, recompute_calculated, set_param
from backend.optimization.engine import run_optimization


def test_optimization_returns_structure():
    cfg = recompute_calculated(get_default_config())
    set_param(cfg, "optimization.search_mode", "Quick", as_user=True)
    set_param(cfg, "optimization.enforce_re_target", False, as_user=True)
    set_param(cfg, "commercial.structure", "HYBRID", as_user=True)
    result = run_optimization(cfg)
    assert result["status"] in ("completed", "no_feasible", "cancelled")
    assert "candidates_evaluated" in result
    if result["status"] == "completed":
        assert result["winner"] is not None
        assert result["winner"]["financial"]["cost_per_kwh"] > 0
        # not a hard-coded vanity number
        assert result["recommendation"]["cost_per_kwh"] == result["winner"]["financial"]["cost_per_kwh"]
