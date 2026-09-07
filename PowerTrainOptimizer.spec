# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

# Keep hiddenimports lean — full scipy/numpy submodule collection slows cold start.
hidden = (
    collect_submodules("uvicorn")
    + collect_submodules("backend")
    + collect_submodules("config")
)

a = Analysis(
    ["backend/launcher.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("frontend/dist", "frontend/dist"),
        ("config", "config"),
    ],
    hiddenimports=hidden
    + [
        "backend.main",
        "backend.database.init_db",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "numpy",
        "scipy",
        "scipy.optimize",
        "pandas",
        "sqlalchemy",
        "openpyxl",
        "reportlab",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PyQt5", "PySide2", "IPython", "notebook"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="PowerTrainOptimizer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
