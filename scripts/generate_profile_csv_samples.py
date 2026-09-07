"""Generate 8,760-hour sample CSV profile templates for Profiles upload."""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIRS = [
    ROOT / "frontend" / "dist" / "samples",
    ROOT / "docs" / "samples",
]


def _timestamps_8760(year: int = 2025) -> list[str]:
    # 2025 is not a leap year → 8760 hours
    start = datetime(year, 1, 1, 0, 0, 0)
    return [(start + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%S") for h in range(8760)]


def _load_mw(h: int) -> float:
    """Example data-centre load ~200 MW base with mild diurnal + weekend dip."""
    hour = h % 24
    dow = (h // 24) % 7  # 0=Thu for 2025-01-01; treat 5,6 as weekend-ish
    diurnal = 1.0 + 0.06 * math.sin((hour - 14) / 24 * 2 * math.pi)
    weekend = 0.97 if dow >= 5 else 1.0
    return round(200.0 * diurnal * weekend, 3)


def _solar_mw(h: int) -> float:
    """Example solar MW shape for ~450 MW plant (daylight only)."""
    hour = h % 24
    # Day length approx; zero outside 6–18
    if hour < 6 or hour >= 18:
        return 0.0
    # Raised cosine peak at 12
    x = (hour - 6) / 12.0  # 0..1
    shape = math.sin(math.pi * x) ** 1.4
    # Mild seasonal via day-of-year
    doy = h // 24
    seasonal = 0.85 + 0.25 * math.sin((doy - 80) / 365 * 2 * math.pi)
    return round(450.0 * 0.55 * shape * seasonal, 3)  # ~CF order of magnitude


def _wind_mw(h: int) -> float:
    """Example wind MW for ~300 MW plant with monthly + diurnal variation."""
    doy = h // 24
    hour = h % 24
    month = datetime(2025, 1, 1).replace()  # noqa — use day index
    # Approximate month from doy
    m = 1 + min(11, doy // 30)
    month_factor = {
        1: 0.70, 2: 0.75, 3: 0.82, 4: 0.92, 5: 1.10, 6: 1.35,
        7: 1.45, 8: 1.25, 9: 1.05, 10: 0.88, 11: 0.78, 12: 0.72,
    }[m]
    diurnal = 1.0 + 0.12 * math.sin((hour - 3) / 24 * 2 * math.pi)
    noise = 1.0 + 0.08 * math.sin(h * 0.37) * math.cos(h * 0.11)
    return round(max(0.0, 300.0 * 0.32 * month_factor * diurnal * noise), 3)


def write_csv(path: Path, kind: str, stamps: list[str], values: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("timestamp,mw\n")
        for ts, v in zip(stamps, values):
            f.write(f"{ts},{v}\n")
    print(f"Wrote {path} ({len(values)} rows)")


def write_readme(path: Path) -> None:
    path.write_text(
        """PowerTrain Optimizer — Profile CSV templates (Model 2.0)
========================================================

Use these files on the Profiles page (Load / Solar / Wind).

Format (required)
-----------------
- Header row: timestamp,mw
- Exactly 8,760 data rows for a non-leap year (or 8,784 for leap year)
- timestamp: unique hourly stamps (ISO recommended), e.g. 2025-01-01T00:00:00
- mw: non-negative number (megawatts). No blanks, no text, no NaN.

How to fill
-----------
1. Download the matching template (load / solar / wind).
2. Keep the timestamp column as-is (or replace with your own unique hourly stamps).
3. Replace the mw column with your project data (same row count).
4. Save as CSV (UTF-8).
5. On Profiles: Choose file → Upload CSV.

Notes
-----
- Sample mw values are EXAMPLE shapes for a ~250 MW data centre / 450 MW solar / 300 MW wind.
  Replace them with your measured or forecast series before investment decisions.
- Invalid files are rejected — the app will not silently fall back to synthetic data
  when profile_source is PROJECT DATA.
- Solar night hours should typically be 0 MW.
- Load must stay > 0 in hours the facility operates (model hours = 8760).

Files
-----
- load_profile_template_8760.csv
- solar_profile_template_8760.csv
- wind_profile_template_8760.csv
""",
        encoding="utf-8",
    )


def main() -> None:
    stamps = _timestamps_8760(2025)
    assert len(stamps) == 8760
    series = {
        "load_profile_template_8760.csv": [_load_mw(h) for h in range(8760)],
        "solar_profile_template_8760.csv": [_solar_mw(h) for h in range(8760)],
        "wind_profile_template_8760.csv": [_wind_mw(h) for h in range(8760)],
    }
    for out in OUT_DIRS:
        out.mkdir(parents=True, exist_ok=True)
        write_readme(out / "README_profile_csv.txt")
        for name, values in series.items():
            write_csv(out / name, name, stamps, values)


if __name__ == "__main__":
    main()
