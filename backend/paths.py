"""Writable paths. Frozen EXE uses LocalAppData; development uses ./data."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def install_dir() -> Path:
    if frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def resource_dir() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return install_dir()


def data_dir() -> Path:
    if frozen():
        root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        path = root / "PowerTrainOptimizer"
    else:
        path = install_dir() / "data"
    path.mkdir(parents=True, exist_ok=True)
    (path / "runs").mkdir(exist_ok=True)
    (path / "backups").mkdir(exist_ok=True)
    (path / "logs").mkdir(exist_ok=True)
    (path / "exports").mkdir(exist_ok=True)
    return path


def db_path() -> Path:
    return data_dir() / "powertrain.db"


def frontend_dir() -> Path:
    bundled = resource_dir() / "frontend" / "dist"
    if (bundled / "index.html").exists():
        return bundled
    return install_dir() / "frontend" / "dist"
