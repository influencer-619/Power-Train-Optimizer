"""Optional project-data hourly profiles (8760) with validation."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

import numpy as np

from backend.paths import data_dir
from config.defaults import DEFAULT_ASSUMPTION, USER_INPUT


ALLOWED_HOURS = (8760, 8784)


def profile_store_dir(project_id: int) -> Path:
    p = data_dir() / "profiles" / f"project_{project_id}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def validate_hourly_series(
    values: list[float] | np.ndarray,
    *,
    name: str,
    timestamps: list[str] | None = None,
    allow_negative: bool = False,
    expected_hours: int = 8760,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    arr = np.asarray(values, dtype=float).reshape(-1)

    if expected_hours not in ALLOWED_HOURS:
        errors.append(f"{name}: expected_hours must be 8760 or 8784 (got {expected_hours}).")
    if len(arr) != expected_hours:
        errors.append(f"{name}: expected exactly {expected_hours} hourly values, got {len(arr)}.")
    if np.any(~np.isfinite(arr)):
        bad = int(np.sum(~np.isfinite(arr)))
        errors.append(f"{name}: {bad} missing/NaN/Inf values.")
    if not allow_negative and np.any(arr < -1e-9):
        errors.append(f"{name}: negative values are not allowed ({int(np.sum(arr < -1e-9))} hours).")

    if timestamps is not None:
        if len(timestamps) != len(arr):
            errors.append(f"{name}: timestamp count ({len(timestamps)}) != value count ({len(arr)}).")
        else:
            seen = set()
            dups = 0
            for ts in timestamps:
                if ts in seen:
                    dups += 1
                seen.add(ts)
            if dups:
                errors.append(f"{name}: {dups} duplicate timestamps.")
            # Leap-year hint
            if expected_hours == 8760 and any("02-29" in str(t) for t in timestamps):
                warnings.append(f"{name}: timestamps include 29 Feb but model_hours=8760 — confirm leap handling.")
            if expected_hours == 8784 and not any("02-29" in str(t) for t in timestamps):
                warnings.append(f"{name}: model_hours=8784 but no 29 Feb timestamps detected.")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "hours": int(len(arr)),
        "min": float(np.nanmin(arr)) if len(arr) else None,
        "max": float(np.nanmax(arr)) if len(arr) else None,
        "mean": float(np.nanmean(arr)) if len(arr) else None,
        "source_badge": "PROJECT DATA" if len(errors) == 0 else "INVALID",
    }


def parse_csv_hourly(text: str, value_column: str | None = None) -> tuple[list[float], list[str] | None]:
    """Parse CSV with optional timestamp column + value column."""
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        # plain single column
        lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        return [float(x.split(",")[-1]) for x in lines], None

    fields = [f.strip() for f in reader.fieldnames]
    ts_col = None
    for cand in ("timestamp", "datetime", "time", "date"):
        for f in fields:
            if f.lower() == cand:
                ts_col = f
                break
    val_col = value_column
    if val_col is None:
        for f in fields:
            if f != ts_col:
                val_col = f
                break
    values = []
    stamps = [] if ts_col else None
    for row in reader:
        values.append(float(row[val_col]))
        if stamps is not None:
            stamps.append(str(row[ts_col]))
    return values, stamps


def save_project_profile(
    project_id: int,
    kind: str,
    values: list[float],
    *,
    timestamps: list[str] | None = None,
    units: str = "MW",
    meta: dict | None = None,
) -> dict[str, Any]:
    kind = kind.lower()
    if kind not in ("load", "solar", "wind"):
        raise ValueError("kind must be load, solar, or wind")
    expected = len(values)
    report = validate_hourly_series(values, name=kind, timestamps=timestamps, expected_hours=expected if expected in ALLOWED_HOURS else 8760)
    if not report["ok"]:
        return {"ok": False, "validation": report}

    dest = profile_store_dir(project_id) / f"{kind}.npz"
    np.savez_compressed(
        dest,
        values=np.asarray(values, dtype=float),
        timestamps=np.array(timestamps or [], dtype=object),
        units=np.array([units]),
        meta=np.array([json.dumps(meta or {})]),
    )
    meta_path = profile_store_dir(project_id) / f"{kind}.meta.json"
    meta_path.write_text(
        json.dumps(
            {
                "kind": kind,
                "hours": len(values),
                "units": units,
                "source": "PROJECT DATA",
                "source_class": USER_INPUT,
                "validation": report,
                "meta": meta or {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"ok": True, "validation": report, "path": str(dest), "source_badge": "PROJECT DATA"}


def load_project_profile(project_id: int, kind: str) -> dict[str, Any] | None:
    path = profile_store_dir(project_id) / f"{kind.lower()}.npz"
    if not path.exists():
        return None
    data = np.load(path, allow_pickle=True)
    values = data["values"].astype(float)
    stamps = data["timestamps"].tolist() if "timestamps" in data and len(data["timestamps"]) else None
    return {
        "values": values,
        "timestamps": stamps,
        "units": str(data["units"][0]) if "units" in data else "MW",
        "source_badge": "PROJECT DATA",
    }


def clear_project_profile(project_id: int, kind: str) -> bool:
    base = profile_store_dir(project_id)
    removed = False
    for p in (base / f"{kind}.npz", base / f"{kind}.meta.json"):
        if p.exists():
            p.unlink()
            removed = True
    return removed


def list_project_profiles(project_id: int) -> dict[str, Any]:
    out: dict[str, Any] = {}
    base = profile_store_dir(project_id)
    for kind in ("load", "solar", "wind"):
        meta_path = base / f"{kind}.meta.json"
        npz_path = base / f"{kind}.npz"
        if meta_path.exists():
            out[kind] = json.loads(meta_path.read_text(encoding="utf-8"))
            out[kind]["imported"] = True
            out[kind]["path"] = str(npz_path) if npz_path.exists() else None
        else:
            out[kind] = {"kind": kind, "imported": False, "source": "SYNTHETIC"}
    return out


def profile_source_badge(config: dict, kind: str) -> str:
    """Return SYNTHETIC or PROJECT DATA from config flags."""
    key = f"{kind}_profile_source"
    section = config.get(kind, {})
    if key in section and isinstance(section[key], dict):
        return str(section[key].get("value") or "SYNTHETIC")
    # also allow general flags
    g = config.get("general", {})
    alt = f"{kind}_profile_source"
    if alt in g and isinstance(g[alt], dict):
        return str(g[alt].get("value") or "SYNTHETIC")
    return "SYNTHETIC"
