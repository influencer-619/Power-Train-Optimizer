"""Calendar index for a normal (non-leap) study period of hourly steps."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

HOURS = 8760
MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
MONTH_NAMES = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)
MONTH_LAST_DAY = MONTH_DAYS  # non-leap


@dataclass(frozen=True)
class CalendarIndex:
    hours: int
    hour_of_day: np.ndarray
    day_of_year: np.ndarray
    month: np.ndarray  # 0..11
    weekday: np.ndarray  # 0=Mon .. 6=Sun
    month_start: np.ndarray  # length 12; -1 if month absent
    start_month: int  # 1..12
    end_month: int  # 1..12


_CACHE: dict[tuple, CalendarIndex] = {}


def clamp_month(m: int) -> int:
    return max(1, min(12, int(m)))


def month_days(*, leap: bool = False) -> tuple[int, ...]:
    days = list(MONTH_DAYS)
    if leap:
        days[1] = 29
    return tuple(days)


def hours_in_month_range(start_month: int, end_month: int, *, leap: bool = False) -> int:
    sm = clamp_month(start_month)
    em = clamp_month(end_month)
    if sm > em:
        sm, em = 1, 12
    days = month_days(leap=leap)
    return int(sum(days[sm - 1 : em]) * 24)


def period_label(start_month: int, end_month: int, *, leap: bool = False) -> str:
    """Human label e.g. '01 Jan – 31 Dec'."""
    sm = clamp_month(start_month)
    em = clamp_month(end_month)
    if sm > em:
        sm, em = 1, 12
    days = month_days(leap=leap)
    return f"01 {MONTH_NAMES[sm - 1]} – {days[em - 1]:02d} {MONTH_NAMES[em - 1]}"


def _build_range(start_month: int, end_month: int, *, leap: bool = False) -> CalendarIndex:
    sm = clamp_month(start_month)
    em = clamp_month(end_month)
    if sm > em:
        sm, em = 1, 12
    days = month_days(leap=leap)
    hours = hours_in_month_range(sm, em, leap=leap)

    hod = np.empty(hours, dtype=np.int16)
    doy = np.empty(hours, dtype=np.int16)
    month = np.empty(hours, dtype=np.int8)
    weekday = np.empty(hours, dtype=np.int8)
    month_start = np.full(12, -1, dtype=np.int32)

    # Absolute day-of-year offset before start month
    day_index = int(sum(days[: sm - 1]))
    t = 0
    for m in range(sm - 1, em):
        month_start[m] = t
        for _d in range(days[m]):
            wd = day_index % 7
            for h in range(24):
                hod[t] = h
                doy[t] = day_index
                month[t] = m
                weekday[t] = wd
                t += 1
            day_index += 1
    assert t == hours
    return CalendarIndex(hours, hod, doy, month, weekday, month_start, sm, em)


def get_calendar(
    hours: int | None = HOURS,
    *,
    start_month: int | None = None,
    end_month: int | None = None,
    leap: bool = False,
) -> CalendarIndex:
    """Build (or fetch) a calendar for a full year or a contiguous month range.

    Prefer start_month/end_month when provided. If only ``hours`` is given:
    - 8760 / 8784 → full Jan–Dec (leap if 8784)
    - any other positive length → first N hours from 01 Jan (non-leap)
    """
    if start_month is not None and end_month is not None:
        sm, em = clamp_month(start_month), clamp_month(end_month)
        key = ("range", sm, em, bool(leap))
        if key not in _CACHE:
            _CACHE[key] = _build_range(sm, em, leap=leap)
        return _CACHE[key]

    h = int(hours if hours is not None else HOURS)
    if h == 8784:
        key = ("range", 1, 12, True)
        if key not in _CACHE:
            _CACHE[key] = _build_range(1, 12, leap=True)
        return _CACHE[key]
    if h == 8760:
        key = ("range", 1, 12, False)
        if key not in _CACHE:
            _CACHE[key] = _build_range(1, 12, leap=False)
        return _CACHE[key]

    if h <= 0:
        raise ValueError("Model hours must be a positive integer.")
    # Prefix of a non-leap year
    key = ("prefix", h, False)
    if key in _CACHE:
        return _CACHE[key]
    full = _build_range(1, 12, leap=False)
    if h > full.hours:
        raise ValueError(f"Model hours {h} exceeds a normal year ({full.hours}).")
    # Find end month covering hour h
    end_m = 12
    for m in range(12):
        start = int(full.month_start[m])
        end = int(full.month_start[m + 1]) if m < 11 else full.hours
        if start >= 0 and start < h <= end:
            end_m = m + 1
            break
    # Slice arrays
    hod = full.hour_of_day[:h].copy()
    doy = full.day_of_year[:h].copy()
    month = full.month[:h].copy()
    weekday = full.weekday[:h].copy()
    month_start = np.full(12, -1, dtype=np.int32)
    for m in range(end_m):
        ms = int(full.month_start[m])
        if 0 <= ms < h:
            month_start[m] = ms
    cal = CalendarIndex(h, hod, doy, month, weekday, month_start, 1, end_m)
    _CACHE[key] = cal
    return cal


def month_slices(hours: int = HOURS, cal: CalendarIndex | None = None) -> list[tuple[int, int]]:
    """Return (start, end) hour indices per calendar month (empty → (0, 0))."""
    idx = cal if cal is not None else get_calendar(hours)
    slices: list[tuple[int, int]] = []
    for m in range(12):
        where = np.where(idx.month == m)[0]
        if len(where) == 0:
            slices.append((0, 0))
        else:
            slices.append((int(where[0]), int(where[-1]) + 1))
    return slices
