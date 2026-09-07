"""Calendar index for a normal (non-leap) year of 8,760 hours."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

HOURS = 8760
MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
MONTH_NAMES = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


@dataclass(frozen=True)
class CalendarIndex:
    hours: int
    hour_of_day: np.ndarray
    day_of_year: np.ndarray
    month: np.ndarray  # 0..11
    weekday: np.ndarray  # 0=Mon .. 6=Sun
    month_start: np.ndarray


_CACHE: dict[int, CalendarIndex] = {}


def get_calendar(hours: int = HOURS) -> CalendarIndex:
    if hours not in (8760, 8784):
        raise ValueError("Only 8760 (normal) or 8784 (leap) hours are supported.")
    if hours in _CACHE:
        return _CACHE[hours]
    if hours == 8784:
        days = list(MONTH_DAYS)
        days[1] = 29
        month_days = tuple(days)
    else:
        month_days = MONTH_DAYS

    hod = np.empty(hours, dtype=np.int16)
    doy = np.empty(hours, dtype=np.int16)
    month = np.empty(hours, dtype=np.int8)
    weekday = np.empty(hours, dtype=np.int8)
    month_start = np.zeros(12, dtype=np.int32)

    t = 0
    day_index = 0
    for m, nd in enumerate(month_days):
        month_start[m] = t
        for _d in range(nd):
            wd = day_index % 7
            for h in range(24):
                hod[t] = h
                doy[t] = day_index
                month[t] = m
                weekday[t] = wd
                t += 1
            day_index += 1
    assert t == hours
    idx = CalendarIndex(hours, hod, doy, month, weekday, month_start)
    _CACHE[hours] = idx
    return idx


def month_slices(hours: int = HOURS) -> list[tuple[int, int]]:
    cal = get_calendar(hours)
    slices = []
    for m in range(12):
        start = int(cal.month_start[m])
        end = int(cal.month_start[m + 1]) if m < 11 else hours
        slices.append((start, end))
    return slices
