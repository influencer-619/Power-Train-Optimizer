"""Four load-factor scenarios collected for one analysis."""

from copy import deepcopy

import pytest

from backend.simulation.engine import run_simulation
from backend.simulation.lf_scenarios import apply_scenario_load_factor, load_factor_scenario_values
from config.defaults import get_default_config, recompute_calculated, v


def test_four_load_factor_scenarios_defaults():
    cfg = recompute_calculated(get_default_config())
    rows = load_factor_scenario_values(cfg)
    assert len(rows) == 4
    assert [lf for _, lf in rows] == [70.0, 80.0, 90.0, 100.0]
    # Primary LF synced from scenario 1
    assert abs(float(v(cfg, "load.load_factor_pct")) - 70.0) < 1e-9


def test_load_factor_s1_drives_base_load():
    cfg = recompute_calculated(get_default_config())
    cfg["load"]["load_factor_s1_pct"]["value"] = 50.0
    cfg = recompute_calculated(cfg)
    peak = float(v(cfg, "load.peak_load_mw"))
    assert abs(float(v(cfg, "load.base_load_mw")) - peak * 0.5) < 1e-6


def test_apply_scenario_lf_not_clobbered_by_s1():
    """Regression: recompute used to force every scenario back to S1 LF."""
    cfg = recompute_calculated(get_default_config())
    assert float(v(cfg, "load.load_factor_s1_pct")) == pytest.approx(70.0)
    cfg100 = apply_scenario_load_factor(deepcopy(cfg), 100.0)
    assert float(v(cfg100, "load.load_factor_pct")) == pytest.approx(100.0)
    peak = float(v(cfg100, "load.peak_load_mw"))
    assert float(v(cfg100, "load.base_load_mw")) == pytest.approx(peak * 1.0)


def test_lf_scenarios_produce_different_energy():
    cfg = recompute_calculated(get_default_config())
    loads = []
    for lf in (70.0, 100.0):
        cfg_i = apply_scenario_load_factor(deepcopy(cfg), lf)
        bundle = run_simulation(cfg_i, structure="HYBRID")
        loads.append(float(bundle.kpis["annual_load_mwh"]))
    assert loads[1] > loads[0] * 1.2
    assert loads[1] / loads[0] == pytest.approx(100.0 / 70.0, rel=0.05)
