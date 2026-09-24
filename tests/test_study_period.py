"""Study month range drives model hours and top-bar period."""

from __future__ import annotations

from backend.simulation.calendar import hours_in_month_range, period_label, get_calendar
from backend.simulation.engine import run_simulation
from config.defaults import get_default_config, recompute_calculated, v


def test_hours_in_month_range_full_year():
    assert hours_in_month_range(1, 12) == 8760
    assert period_label(1, 12) == "01 Jan – 31 Dec"


def test_hours_in_month_range_q1():
    assert hours_in_month_range(1, 3) == 2160  # 31+28+31
    assert period_label(1, 3) == "01 Jan – 31 Mar"


def test_recompute_sets_model_hours_from_months():
    cfg = recompute_calculated(get_default_config())
    cfg["general"]["study_start_month"]["value"] = 4
    cfg["general"]["study_end_month"]["value"] = 6
    cfg["general"]["model_hours"]["source"] = "CALCULATED"
    cfg = recompute_calculated(cfg)
    assert v(cfg, "general.model_hours") == 2184  # 30+31+30


def test_manual_model_hours_preserved_until_months_change():
    cfg = recompute_calculated(get_default_config())
    cfg["general"]["model_hours"]["value"] = 4000
    cfg["general"]["model_hours"]["source"] = "USER_INPUT"
    cfg = recompute_calculated(cfg)
    assert v(cfg, "general.model_hours") == 4000
    # Changing months clears manual override only when source reset by caller;
    # backend keeps USER_INPUT if still set
    cfg["general"]["study_end_month"]["value"] = 6
    cfg = recompute_calculated(cfg)
    assert v(cfg, "general.model_hours") == 4000
    cfg["general"]["model_hours"]["source"] = "CALCULATED"
    cfg = recompute_calculated(cfg)
    assert v(cfg, "general.model_hours") == hours_in_month_range(1, 6)


def test_partial_year_simulation_runs():
    cfg = recompute_calculated(get_default_config())
    cfg["general"]["study_start_month"]["value"] = 1
    cfg["general"]["study_end_month"]["value"] = 3
    cfg["general"]["model_hours"]["source"] = "CALCULATED"
    cfg = recompute_calculated(cfg)
    bundle = run_simulation(cfg)
    assert len(bundle.dispatch.load_mw) == 2160
    cal = get_calendar(start_month=1, end_month=3)
    assert cal.hours == 2160
