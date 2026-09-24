from config.defaults import get_default_config, recompute_calculated
from backend.simulation.profiles import generate_load, generate_solar, generate_wind
from backend.simulation.engine import run_simulation
from backend.simulation.calendar import HOURS
from backend.compliance.engine import evaluate_compliance
from backend.financial.engine import evaluate_financial


def test_load_generation_and_factor():
    cfg = recompute_calculated(get_default_config())
    load = generate_load(cfg)
    assert len(load["load_mw"]) == HOURS
    assert load["annual_mwh"] > 0
    assert abs(load["actual_load_factor_pct"] - cfg["load"]["load_factor_pct"]["value"]) < 5.0


def test_seasonal_tod_load_shape():
    """Season × day/night × weekday/weekend; mean tracks load factor."""
    cfg = recompute_calculated(get_default_config())
    cfg["load"]["load_model"]["value"] = "Seasonal TOD"
    cfg["load"]["seasonal_tod_summer_day"]["value"] = 1.20
    cfg["load"]["seasonal_tod_summer_night"]["value"] = 0.80
    cfg["load"]["seasonal_tod_rainy_day"]["value"] = 1.0
    cfg["load"]["seasonal_tod_rainy_night"]["value"] = 1.0
    cfg["load"]["seasonal_tod_winter_day"]["value"] = 1.0
    cfg["load"]["seasonal_tod_winter_night"]["value"] = 1.0
    cfg["load"]["weekday_multiplier"]["value"] = 1.0
    cfg["load"]["weekend_multiplier"]["value"] = 1.0
    cfg = recompute_calculated(cfg)
    load = generate_load(cfg)
    peak = float(cfg["load"]["peak_load_mw"]["value"])
    lf = float(cfg["load"]["load_factor_pct"]["value"]) / 100.0
    assert abs(load["load_mw"].mean() - peak * lf) < 1e-6
    from backend.simulation.calendar import get_calendar

    cal = get_calendar(start_month=1, end_month=12, leap=False)
    apr_day = [
        t for t in range(cal.hours)
        if int(cal.month[t]) + 1 == 4 and int(cal.hour_of_day[t]) == 12
    ]
    apr_night = [
        t for t in range(cal.hours)
        if int(cal.month[t]) + 1 == 4 and int(cal.hour_of_day[t]) == 0
    ]
    assert load["load_mw"][apr_day[0]] > load["load_mw"][apr_night[0]]


def test_seasonal_tod_applies_weekend_multiplier():
    cfg = recompute_calculated(get_default_config())
    cfg["load"]["weekday_multiplier"]["value"] = 1.0
    cfg["load"]["weekend_multiplier"]["value"] = 0.5
    # Neutral season/TOD so weekday effect is clear
    for k in (
        "seasonal_tod_summer_day", "seasonal_tod_summer_night",
        "seasonal_tod_rainy_day", "seasonal_tod_rainy_night",
        "seasonal_tod_winter_day", "seasonal_tod_winter_night",
    ):
        cfg["load"][k]["value"] = 1.0
    cfg = recompute_calculated(cfg)
    load = generate_load(cfg)
    from backend.simulation.calendar import get_calendar

    cal = get_calendar(start_month=1, end_month=12, leap=False)
    wd_idx = next(t for t in range(cal.hours) if int(cal.weekday[t]) < 5)
    we_idx = next(t for t in range(cal.hours) if int(cal.weekday[t]) >= 5)
    # After mean-scaling, weekend hours should sit below weekday when we=0.5
    assert load["load_mw"][we_idx] < load["load_mw"][wd_idx]


def test_solar_night_zero_and_cf():
    cfg = recompute_calculated(get_default_config())
    solar = generate_solar(cfg)
    assert len(solar["solar_mw"]) == HOURS
    assert (solar["solar_mw"] >= -1e-9).all()
    # midnight should be zero
    assert solar["solar_mw"][0] == 0.0
    assert solar["actual_cf_pct"] > 0


def test_wind_generation():
    cfg = recompute_calculated(get_default_config())
    wind = generate_wind(cfg)
    assert len(wind["wind_mw"]) == HOURS
    assert (wind["wind_mw"] >= -1e-9).all()
    assert wind["actual_cf_pct"] > 0


def test_power_balance_and_bess():
    cfg = recompute_calculated(get_default_config())
    bundle = run_simulation(cfg, structure="HYBRID")
    assert bundle.validation["power_balance_ok"] is True
    assert bundle.validation["hours"] == HOURS
    assert bundle.validation["soc_ok"] is True
    assert bundle.validation["grid_capacity_ok"] is True
    assert (bundle.dispatch.solar_mw >= -1e-9).all()
    assert bundle.kpis["annual_re_pct"] <= 100.0 + 1e-6
    assert bundle.kpis["hourly_cfe_min_pct"] <= 100.0 + 1e-6


def test_discom_zero_re_assets():
    cfg = recompute_calculated(get_default_config())
    bundle = run_simulation(cfg, structure="DISCOM")
    assert bundle.kpis["solar_mw"] == 0.0
    assert bundle.kpis["wind_mw"] == 0.0
    assert bundle.kpis["annual_re_pct"] < 1.0


def test_compliance_and_financial():
    cfg = recompute_calculated(get_default_config())
    bundle = run_simulation(cfg, structure="HYBRID")
    compliance = evaluate_compliance(bundle.config, bundle.kpis)
    fin = evaluate_financial(bundle.config, bundle.kpis, compliance, bundle.dispatch)
    assert "rpo" in compliance and "rco" in compliance and "eso" in compliance
    assert fin["cost_per_kwh"] > 0
    assert len(fin["cashflows_inr"]) == int(cfg["financial"]["project_life_yr"]["value"]) + 1


def test_re_origin_tracking():
    cfg = recompute_calculated(get_default_config())
    bundle = run_simulation(cfg, structure="HYBRID")
    assert 0 <= bundle.kpis["re_origin_stored_share_pct"] <= 100.0 + 1e-6
