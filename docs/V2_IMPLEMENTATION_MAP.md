# PowerTrain Optimizer V2 — Implementation Map (from V1 audit)

Model version target: evolve from `1.0.0` without breaking existing projects.  
Schema today: `SCHEMA_VERSION = 1`.  
Date of audit: 2026-09-04.

## V1 architecture (preserve)

| Layer | Location | Notes |
|-------|----------|-------|
| Launcher / EXE | `backend/launcher.py`, `PowerTrainOptimizer.spec` | Windowed EXE, heartbeat shutdown |
| API | `backend/main.py` | FastAPI + static SPA |
| DB | `backend/models/db_models.py`, `backend/database/init_db.py` | SQLite, `ProjectInput` canonical JSON |
| Profiles | `backend/simulation/profiles.py` | Synthetic only today |
| Dispatch | `backend/simulation/dispatch.py` | Fixed priority RE→BESS→curtail→discharge→grid |
| Simulation | `backend/simulation/engine.py` | KPIs + monthly + CFE heatmap |
| Validation | `backend/simulation/validation.py` | Config + hourly power balance |
| Compliance | `backend/compliance/engine.py` | RE / CFE modes / RPO / RCO / ESO |
| Financial | `backend/financial/engine.py` | Cost stack, NPV/IRR/payback, incremental vs DISCOM |
| Optimization | `backend/optimization/engine.py` | Full 8760 per candidate already; binding strings |
| Services | `backend/services/run_service.py` | Sim / opt / compare / sensitivity |
| Reports | `backend/reports/excel_pdf.py` | Excel + PDF |
| UI | `frontend/dist/assets/{app,charts,styles}.*` | Packaged SPA (not React rebuild) |

## Key KPI formulas (as implemented)

- **Annual RE %** = Σ `re_serving_load_mw` / Σ `load_mw` × 100  
- **Hourly CFE %** = `re_serving_load[t] / load[t]` × 100  
- **Curtailment %** = Σ curtail / Σ (solar+wind) × 100  
- **BESS utilization %** = min(100, (Σ discharge / energy_mwh) / 365 × 100)  
- **₹/kWh** = total annual cost / (load_mwh × 1000) — labelled as cost of delivered energy, not formal LCOE  

## Documented vs code discrepancies

1. Config `priority_1…5` do **not** change dispatch order (labels only).  
2. Financing/tax config fields are **unused** in cashflows.  
3. ESO RE-origin uses **charge share**, not SOC time-average.  
4. Dashboard can show “Feasible/Recommended” without compliance Pass.  
5. No config hash / stale-result detection.  
6. NPZ does not persist all origin/balance columns.  
7. No energy ledger API or UI.  
8. No project-data profile import.

## V2 phase plan

| Phase | Scope |
|-------|--------|
| 1 | Energy ledger + stronger validation + tests + config fingerprint |
| 2 | CFE analytics + feasibility status + binding constraints (sim) |
| 3 | Optimization explainability + ensure final full-8760 validation |
| 4 | Incremental economics clarity + labels |
| 5 | Project-data profile mode (optional upload) |
| 6 | Dashboard redesign + Avaada semantic colors |
| 7 | Reports + User Guide |
| 8 | Regression + EXE |

## Phase status

| Phase | Status |
|-------|--------|
| 0 Audit + map | Done — this file |
| 1 Energy ledger + validation + fingerprint | Done (model 2.0.0) |
| 2 CFE analytics + feasibility + binding | Done |
| 3 Optimization explainability | Done |
| 4 Incremental economics clarity | Done |
| 5 Project-data profiles | Done |
| 6 Dashboard redesign | Done |
| 7 Reports + User Guide | Done |
| 8 Regression + EXE | Done |

### Phase 2–8 delivered (summary)

- `backend/compliance/cfe_analytics.py` — duration curve, deficit streaks, pass-mode metrics  
- `backend/compliance/feasibility.py` — FEASIBLE / NOT FEASIBLE / INCOMPLETE / LEGAL REVIEW / MODEL ERROR; `can_recommend` only when FEASIBLE  
- `backend/optimization/explain.py` — why-winner + marginal steps; wired into opt engine + `/api/analysis/marginal`  
- Project profile CSV import (`profiles_project.py`) + API upload/list/clear; `profile_source` SYNTHETIC|PROJECT DATA  
- Stale-result detection via `input_version`; dashboard banners + feasibility/data-quality cards  
- Excel/PDF: Energy Ledger, Data Quality, Feasibility, incremental vs DISCOM  
- UI: Profiles page, economics incremental panel, opt explainability, no false RECOMMENDED  
- Tests: `tests/test_v2_phases.py` + energy ledger suite  

### Phase 1 delivered

- `backend/simulation/energy_ledger.py` — annual/monthly flows + reconciliation  
- `backend/simulation/fingerprint.py` — SHA-256 config hash  
- Explicit solar/wind→load/BESS/curtail + BESS origin splits in `dispatch.py`  
- Stronger `validate_dispatch` (energy balance, SOC, finite) → raises MODEL ERROR  
- Richer BESS KPIs (duration, losses, origin discharge, utilization definition)  
- API `GET /api/simulation/{id}/ledger` + UI **Energy Ledger** page  
- Tests: `tests/test_energy_ledger.py` (+ existing regression) — 15 passed  
- `MODEL_VERSION = 2.0.0`
