# API

Base URL: `http://127.0.0.1:<port>/api`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health + model version |
| POST | `/heartbeat` | UI keepalive (EXE exits if heartbeats stop) |
| POST | `/shutdown` | Request graceful process exit (Quit App / tab close) |
| GET | `/defaults` | Default config + banners |
| GET/POST | `/projects` | List / create |
| GET/PUT/DELETE | `/projects/{id}` | Project meta |
| GET/PUT | `/projects/{id}/inputs` | Full config |
| POST | `/simulation/run` | Run 8,760 simulation |
| GET | `/simulation/{id}` | Results |
| GET | `/simulation/{id}/ledger` | Annual + monthly energy ledger + reconciliation |
| GET | `/simulation/{id}/series` | Chart series |
| POST | `/optimization/run` | Start optimization |
| GET | `/optimization/{id}` | Poll status/result |
| POST | `/optimization/{id}/cancel` | Cancel |
| GET/POST/PUT/DELETE | `/scenarios` | Scenario CRUD |
| POST | `/sensitivity/run` | Tornado + matrix |
| POST | `/compare/architectures` | DISCOM/Captive/Hybrid/OA |
| POST | `/reports/excel` | Excel export |
| POST | `/reports/pdf` | PDF export |
| POST | `/projects/{id}/backup` | Project zip |
| POST | `/projects/restore` | Restore zip |
| GET | `/settings` | App settings |
