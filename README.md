# PowerTrain Optimizer

Techno-economic **8,760-hour** simulation and optimization tool for Data Centre power architecture (Solar + Wind + BESS + Grid) with DISCOM / Captive / Hybrid / Open Access commercial structures, RPO/RCO/ESO compliance, and project economics (₹/kWh, NPV, IRR, payback).

## Quick start (development)

```bat
run_dev.bat
```

This creates a virtualenv, installs Python dependencies, starts the local FastAPI server on `127.0.0.1`, and opens the browser.

## Tests

```bat
run_tests.bat
```

## Windows EXE (no dependencies)

```bat
build_exe.bat
```

Or build **and** create a ready-to-give folder:

```bat
package_share.bat
```

Output:

```text
dist\PowerTrainOptimizer.exe
dist\PowerTrain_Share\          ← copy this whole folder to anyone
  PowerTrainOptimizer.exe
  HOW_TO_SHARE.txt
```

**Give to anyone:** they only need the EXE. Double-click on Windows 10/11 — no Python/Node/database install.

**LAN / office network:** keep the EXE running on one laptop. Others open the **Network URL** (shown under Settings, or in `ACCESS_URLS.txt`) in their browser, e.g. `http://192.168.1.45:8765/`. Same Wi‑Fi/LAN required. Allow Windows Firewall for Private networks if prompted.

- Windowed EXE — no console window.
- Default bind is `0.0.0.0` (this PC + network). Local-only: set `PTO_HOST=127.0.0.1`.
- With LAN sharing on, the app stays running until **Quit App** (closing the browser does not stop the server).
- Project data: `%LOCALAPPDATA%\PowerTrainOptimizer`.

See `docs/HOW_TO_SHARE.txt` for step-by-step sharing instructions.

## Stack

- Backend: Python, FastAPI, SQLAlchemy, SQLite, NumPy, Pandas, SciPy
- Frontend (runtime): static SPA in `frontend/dist` (served by FastAPI)
- Frontend (source): React + TypeScript + Vite + Tailwind in `frontend/` (build with npm when available)
- Packaging: PyInstaller

## Critical behaviours

- **No mandatory uploads** — 8,760 profiles are generated from parameters
- **No external DB** — embedded SQLite
- Defaults are labelled **DEFAULT ASSUMPTION**
- Concept-note values are labelled **CONCEPT_NOTE**
- Regulatory applicability is **not** auto-determined (legal review banners)

## Docs

- **`docs/PowerTrain_Optimizer_User_Guide.docx`** — full step-by-step user manual (every menu & option)
- `ARCHITECTURE.md`
- `MODEL_METHODOLOGY.md`
- `ASSUMPTIONS.md`
- `docs/API.md`

Regenerate the Word guide after config/UI changes:

```bat
.venv\Scripts\python.exe scripts\generate_user_guide.py
```
