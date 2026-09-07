# Architecture

## Runtime

```text
PowerTrainOptimizer.exe / run_dev.bat
        ↓
backend.launcher
        ↓
SQLite init (idempotent; data/ or %LOCALAPPDATA%\PowerTrainOptimizer)
        ↓
FastAPI (127.0.0.1) — wait until /api/health ready
        ↓
Serves frontend/dist + /api/*  →  opens browser
        ↓
Browser UI heartbeats (/api/heartbeat)
        ↓
Quit App / tab close → /api/shutdown (or heartbeat timeout) → process exits
```

Packaged EXE is windowed (`console=False`): no CMD window. The launcher watchdog exits if the UI stops heartbeating.

## Backend packages

| Package | Role |
|---------|------|
| `config/defaults` | Single source of defaults + assumption metadata |
| `backend/simulation` | Load/solar/wind profiles, dispatch, validation |
| `backend/compliance` | RE%, CFE, RPO, RCO, ESO |
| `backend/financial` | Cost stack, NPV/IRR/payback |
| `backend/optimization` | Staged capacity screening + ranking |
| `backend/services` | Projects, runs, sensitivity, compare |
| `backend/reports` | Excel / PDF |
| `backend/database` | SQLAlchemy + migrations/seed |

## Data

- Canonical project inputs: `project_inputs.payload_json`
- Section tables mirror JSON for schema completeness
- Hourly arrays: `data/runs/sim_*.npz` (not 8,760 SQL rows)
- Writable DB never forced into Program Files when frozen

## Frontend

- Packaged UI: `frontend/dist` static SPA (works without Node)
- Optional React rebuild: `frontend/` Vite app when npm is present
