"""Synthetic 8,760-hour load, solar and wind profile generators."""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from backend.simulation.calendar import HOURS, get_calendar, hours_in_month_range
from config.defaults import v, v_opt


def _calendar_for(config: dict, hours: int):
    """Prefer study month range when hours match; else fall back to hours-based calendar."""
    try:
        sm = int(v(config, "general.study_start_month"))
        em = int(v(config, "general.study_end_month"))
        if hours == hours_in_month_range(sm, em, leap=False):
            return get_calendar(start_month=sm, end_month=em, leap=False)
        if hours == 8784 and sm == 1 and em == 12:
            return get_calendar(start_month=1, end_month=12, leap=True)
    except Exception:
        pass
    return get_calendar(hours)


def _month_factors(section: dict, prefix: str) -> np.ndarray:
    return np.array([float(section[f"{prefix}{i}"]["value"]) for i in range(1, 13)], dtype=float)


# Month index 0..11 → Indian season: Winter, Summer, Monsoon, Post-monsoon
# Winter Dec–Feb | Summer Mar–May | Monsoon Jun–Sep | Post-monsoon Oct–Nov
_SEASON_BY_MONTH = np.array([0, 0, 1, 1, 1, 2, 2, 2, 2, 3, 3, 0], dtype=int)
_SEASON_KEYS = ("seasonal_winter", "seasonal_summer", "seasonal_monsoon", "seasonal_post_monsoon")


def _season_factors_12(section: dict, legacy_prefix: str | None = None) -> np.ndarray:
    """Return length-12 month multipliers from 4 seasonal factors (or legacy 12-month keys)."""
    if all(k in section for k in _SEASON_KEYS):
        seasons = np.array([float(section[k]["value"]) for k in _SEASON_KEYS], dtype=float)
        return seasons[_SEASON_BY_MONTH]
    if legacy_prefix:
        try:
            return _month_factors(section, legacy_prefix)
        except Exception:
            pass
    return np.ones(12, dtype=float)


def _parse_month_list(raw: str, fallback: list[int]) -> list[int]:
    out: list[int] = []
    for part in str(raw or "").replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            m = int(part)
        except ValueError:
            continue
        if 1 <= m <= 12:
            out.append(m)
    return out or list(fallback)


def _seasonal_tod_shape(config: dict, cal) -> np.ndarray:
    """Season (Summer/Rainy/Winter) × TOD day/night × weekday/weekend multipliers."""
    summer_m = set(_parse_month_list(str(v(config, "load.seasonal_tod_summer_months")), [3, 4, 5]))
    rainy_m = set(_parse_month_list(str(v(config, "load.seasonal_tod_rainy_months")), [6, 7, 8, 9]))
    winter_m = set(_parse_month_list(str(v(config, "load.seasonal_tod_winter_months")), [10, 11, 12, 1, 2]))
    day_start = int(v(config, "load.seasonal_tod_day_start_hour"))
    day_end = int(v(config, "load.seasonal_tod_day_end_hour"))
    if day_end <= day_start:
        day_start, day_end = 8, 20

    mult = {
        "summer": (
            float(v(config, "load.seasonal_tod_summer_day")),
            float(v(config, "load.seasonal_tod_summer_night")),
        ),
        "rainy": (
            float(v(config, "load.seasonal_tod_rainy_day")),
            float(v(config, "load.seasonal_tod_rainy_night")),
        ),
        "winter": (
            float(v(config, "load.seasonal_tod_winter_day")),
            float(v(config, "load.seasonal_tod_winter_night")),
        ),
    }
    try:
        wd = float(v(config, "load.weekday_multiplier"))
    except Exception:
        wd = 1.0
    try:
        we = float(v(config, "load.weekend_multiplier"))
    except Exception:
        we = 1.0

    shape = np.ones(cal.hours, dtype=float)
    for t in range(cal.hours):
        month = int(cal.month[t]) + 1  # calendar stores 0..11
        hod = int(cal.hour_of_day[t])
        if month in summer_m:
            season = "summer"
        elif month in rainy_m:
            season = "rainy"
        elif month in winter_m:
            season = "winter"
        else:
            season = "winter"
        is_day = day_start <= hod < day_end
        day_m, night_m = mult[season]
        tod = day_m if is_day else night_m
        day_type = wd if int(cal.weekday[t]) < 5 else we
        shape[t] = tod * day_type
    return shape


def generate_load(config: dict, hours: int = HOURS) -> dict:
    cal = _calendar_for(config, hours)
    hours = cal.hours
    peak = float(v(config, "load.peak_load_mw"))
    lf = float(v(config, "load.load_factor_pct")) / 100.0
    operating = int(v(config, "load.operating_hours"))

    # Sole product load shape: Seasonal TOD (+ weekday/weekend)
    shape = _seasonal_tod_shape(config, cal)
    avg = peak * lf
    if shape.mean() <= 0:
        shape = np.ones(hours, dtype=float)
    load = shape / shape.mean() * avg
    if load.max() > peak + 1e-9 and load.max() != load.mean():
        avg_now = load.mean()
        if load.max() > avg_now:
            load = avg_now + (load - avg_now) * (peak - avg_now) / (load.max() - avg_now)
    load = np.clip(load, 0.0, None)

    if operating < hours:
        load[operating:] = 0.0

    annual_mwh = float(load.sum())
    actual_lf = float(load.mean() / peak) if peak > 0 else 0.0
    return {
        "load_mw": load,
        "annual_mwh": annual_mwh,
        "actual_load_factor_pct": actual_lf * 100.0,
        "peak_mw": float(load.max()),
    }


def _scale_to_cf(raw: np.ndarray, capacity: float, cf: float) -> np.ndarray:
    if capacity <= 0 or cf <= 0:
        return np.zeros_like(raw)
    out = raw.astype(float).copy()
    target_mean = capacity * cf
    for _ in range(8):
        m = out.mean()
        if m <= 1e-12:
            break
        out *= target_mean / m
        out = np.clip(out, 0.0, capacity)
    return out


def generate_solar(config: dict, hours: int = HOURS, capacity_override: float | None = None) -> dict:
    cal = _calendar_for(config, hours)
    hours = cal.hours
    capacity = float(capacity_override if capacity_override is not None else v_opt(config, "solar.capacity_mw", 1.0) or 1.0)
    if capacity <= 0:
        capacity = 1.0
    cf = float(v(config, "solar.capacity_factor_pct")) / 100.0
    sunrise = float(v(config, "solar.sunrise_hour"))
    sunset = float(v(config, "solar.sunset_hour"))
    peak_h = float(v(config, "solar.peak_generation_hour"))
    variability = float(v(config, "solar.hourly_variability"))
    seed = int(v(config, "general.random_seed"))
    seasonal = _season_factors_12(config["solar"], legacy_prefix="seasonal_")

    hod = cal.hour_of_day.astype(float)
    daylight = (hod >= sunrise) & (hod < sunset)
    span = max(sunset - sunrise, 1e-6)
    sigma = span / 4.0
    bell = np.exp(-0.5 * ((hod - peak_h) / sigma) ** 2)
    bell = np.where(daylight, bell, 0.0)
    bell *= seasonal[cal.month]

    rng = np.random.default_rng(seed + 17)
    noise = 1.0 + variability * rng.uniform(-1.0, 1.0, size=hours)
    bell = np.where(daylight, bell * noise, 0.0)
    bell = np.clip(bell, 0.0, None)

    gen = _scale_to_cf(bell, capacity, cf)
    gen = np.where(daylight, gen, 0.0)
    annual = float(gen.sum())
    actual_cf = annual / (capacity * hours) * 100.0 if capacity > 0 else 0.0
    return {
        "solar_mw": gen,
        "annual_mwh": annual,
        "actual_cf_pct": actual_cf,
        "capacity_mw": capacity,
    }


def generate_wind(config: dict, hours: int = HOURS, capacity_override: float | None = None) -> dict:
    cal = _calendar_for(config, hours)
    hours = cal.hours
    capacity = float(capacity_override if capacity_override is not None else v_opt(config, "wind.capacity_mw", 1.0) or 1.0)
    if capacity <= 0:
        capacity = 1.0
    cf = float(v(config, "wind.capacity_factor_pct")) / 100.0
    variability = float(v(config, "wind.hourly_variability"))
    seed = int(v(config, "general.random_seed"))
    monthly = _season_factors_12(config["wind"], legacy_prefix="month_")

    base = monthly[cal.month].astype(float)
    # Mild diurnal preference for afternoon/evening without forcing zeros
    hod = cal.hour_of_day.astype(float)
    diurnal = 0.85 + 0.15 * np.sin((hod - 6.0) / 24.0 * 2.0 * np.pi)
    raw = base * diurnal

    rng = np.random.default_rng(seed + 91)
    noise = 1.0 + variability * rng.uniform(-1.0, 1.0, size=hours)
    raw = np.clip(raw * noise, 0.0, None)

    gen = _scale_to_cf(raw, capacity, cf)
    annual = float(gen.sum())
    actual_cf = annual / (capacity * hours) * 100.0 if capacity > 0 else 0.0
    return {
        "wind_mw": gen,
        "annual_mwh": annual,
        "actual_cf_pct": actual_cf,
        "capacity_mw": capacity,
    }


@lru_cache(maxsize=32)
def cached_shapes(seed: int, hours: int, solar_key: str, wind_key: str, load_key: str):
    """Placeholder cache key helper — profiles are rebuilt via engine cache."""
    return seed, hours, solar_key, wind_key, load_key
