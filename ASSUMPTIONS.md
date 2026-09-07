# Assumptions

All editable defaults live in `config/defaults/config.py`.

## Concept note values (CONCEPT_NOTE)

| Parameter | Value |
|-----------|-------|
| Grid connection | 220 kV |
| Annual RE scenario presets | 90%, 95%, 99% |
| Hourly CFE scenario presets | 90%, 95%, 99%, 100% |
| ESO FY2026-27 | 2.5% |
| ESO FY2029-30 | 4.0% |
| ESO renewable-origin stored energy | ≥ 85% |
| Model hours | 8,760 |
| Commercial structures | DISCOM, Captive, Hybrid, Open Access |
| DISCOM name reference | MSEDCL |
| RCO designated-consumer status | Unknown / Legal Review Required |

## Interpolated ESO years (DEFAULT ASSUMPTION)

| Year | Value |
|------|-------|
| FY2027-28 | 3.0% |
| FY2028-29 | 3.5% |

## Demonstration project (DEFAULT ASSUMPTION)

| Parameter | Default |
|-----------|---------|
| Project | Default Data Centre — 250 MW |
| Peak load | 250 MW |
| Load factor | 80% |
| Base load (calculated) | 200 MW |
| Solar | 450 MW @ 22% CF |
| Wind | 300 MW @ 32% CF |
| BESS | 150 MW / 600 MWh |
| Grid import | 250 MW |
| Currency | INR (₹) |

Every other numeric input (CAPEX, OPEX, tariffs, efficiencies, discount rate, etc.) is a **DEFAULT ASSUMPTION** unless marked CONCEPT_NOTE or CALCULATED. See the in-app Assumption Register.

**Warning:** Results containing default assumptions should be replaced with project-specific data before investment decisions.
