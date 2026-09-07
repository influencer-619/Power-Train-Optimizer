"""Synthetic 8,760-hour load, solar and wind profile generators."""

from __future__ import annotations

from functools import lru_cache

import numpy as np

from backend.simulation.calendar import HOURS, get_calendar
from config.defaults import v


def _month_factors(section: dict, prefix: str) -> np.ndarray:
    return np.array([float(section[f"{prefix}{i}"]["value"]) for i in range(1, 13)], dtype=float)


def generate_load(config: dict, hours: int = HOURS) -> dict:
    cal = get_calendar(hours)
    peak = float(v(config, "load.peak_load_mw"))
    lf = float(v(config, "load.load_factor_pct")) / 100.0
    model = str(v(config, "load.load_model"))
    operating = int(v(config, "load.operating_hours"))

    shape = np.ones(hours, dtype=float)

    if model in ("Daily Pattern", "Custom Parameterized", "Weekday/Weekend", "Seasonal"):
        hour_mult = np.array(
            [float(config["load"][f"hour_multiplier_{h}"]["value"]) for h in range(24)],
            dtype=float,
        )
        if model != "Weekday/Weekend" or True:
            if model in ("Daily Pattern", "Custom Parameterized", "Seasonal"):
                shape *= hour_mult[cal.hour_of_day]

    if model in ("Weekday/Weekend", "Custom Parameterized"):
        wd = float(v(config, "load.weekday_multiplier"))
        we = float(v(config, "load.weekend_multiplier"))
        shape *= np.where(cal.weekday < 5, wd, we)

    if model in ("Seasonal", "Custom Parameterized"):
        month_mult = _month_factors(config["load"], "month_multiplier_")
        shape *= month_mult[cal.month]

    if model == "Flat":
        load = np.full(hours, peak * lf, dtype=float)
    else:
        avg = peak * lf
        if shape.mean() <= 0:
            shape = np.ones(hours, dtype=float)
        load = shape / shape.mean() * avg
        if load.max() > peak + 1e-9 and load.max() != load.mean():
            # Compress peaks toward average so max == peak while preserving mean if possible
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
    cal = get_calendar(hours)
    capacity = float(capacity_override if capacity_override is not None else v(config, "solar.capacity_mw"))
    cf = float(v(config, "solar.capacity_factor_pct")) / 100.0
    sunrise = float(v(config, "solar.sunrise_hour"))
    sunset = float(v(config, "solar.sunset_hour"))
    peak_h = float(v(config, "solar.peak_generation_hour"))
    variability = float(v(config, "solar.hourly_variability"))
    seed = int(v(config, "general.random_seed"))
    seasonal = _month_factors(config["solar"], "seasonal_")

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
    cal = get_calendar(hours)
    capacity = float(capacity_override if capacity_override is not None else v(config, "wind.capacity_mw"))
    cf = float(v(config, "wind.capacity_factor_pct")) / 100.0
    variability = float(v(config, "wind.hourly_variability"))
    seed = int(v(config, "general.random_seed"))
    monthly = _month_factors(config["wind"], "month_")

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
