# Assumptions

All editable defaults live in `config/defaults/config.py`. PowerTrain Optimizer is a **data-centre buyer** model:

- **Bill** = Architecture mix % × DISCOM / Solar / Wind / Storage tariff stacks
- **Hourly CFE and charts** = TOD / availability (solar ~ 0 at night; wind and BESS can serve)

Generation-plant CAPEX / OPEX / MW as commercial product inputs are **out of scope**.

---

## 1. Product framing (buyer)

| Idea | Assumption |
|------|------------|
| Viewpoint | DC consumes power; Solar / Wind / BESS / DISCOM are **contracted shares**, not owned plant CAPEX |
| Architecture mix % | Selected assets sum to **100%**. Sets **annual contract energy** and the **bill blend** |
| Bill blend | Discom × G% + Solar × S% + Wind × W% + Storage × B% (stack totals for G/S/W; Storage tariff for BESS) |
| Target vs Simulated (bill) | Both use Architecture contracted mix % on the buyer path |
| Hourly Solar / Wind | Synthetic CF shapes or PROJECT DATA, **scaled** so annual MWh = Load_annual × mix%/100 |
| Solar at night | Shape is ~ **0** outside sunrise-sunset (not firm Solar% every hour) |
| Load TOD | Seasonal day/night bands shape **demand**; solar availability uses solar sunrise/sunset (and optional PROJECT DATA) |
| BESS (bill) | Storage tariff ₹/kWh × BESS mix % only |
| BESS (hourly CFE) | If BESS mix > 0, model **derives** storage power/energy so day RE can charge and night can discharge |
| Hourly CFE | Min(Load, Solar_t + Wind_t + RE-origin BESS discharge_t) / Load × 100 |
| Annual RE % | Energy-weighted: sum RE serving load / sum Load × 100 (availability — not flat Architecture %) |
| Architectures | **Captive** and **Hybrid** analysed equally every Run Analysis. **DISCOM** = 100% grid baseline only |

---

## 2. Concept note values (CONCEPT_NOTE)

| Parameter | Value |
|-----------|-------|
| Grid connection (label) | 220 kV |
| Annual RE target (default) | 90% — vs **energy-weighted** RE serving load |
| Hourly CFE target (default) | 90% — Pass = **every hour** >= target (availability series) |
| Hourly CFE formula | Min(Load, Solar + Wind + RE-BESS) / Load × 100 |
| ESO target (single) | 2.5% of annual load as contracted BESS mix energy |
| ESO RE-origin (obligation) | Contracted BESS treated as 100% RE-origin for ESO framing |
| Model hours | Study period days × 24 (full year = 8,760) |
| Structures | DISCOM (baseline), Captive, Hybrid, Open Access (legacy) |
| DISCOM name reference | MSEDCL |
| RPO/RCO | Single integrated target % of DC load — **Architecture RE mix** for obligation |

---

## 3. Demonstration project (DEFAULT ASSUMPTION)

| Parameter | Default role |
|-----------|----------------|
| Project | Starter Default Data Centre — replace before decisions |
| IT load / PUE to Peak | Peak_MW = IT × PUE (calculated) |
| Load factor scenarios | S1-S4; headline KPIs use **S1** |
| Load Seasonal TOD | Summer / Rainy / Winter × day/night × weekday/weekend |
| Solar profile | Synthetic diurnal (sunrise-sunset, CF%) or PROJECT DATA CSV |
| Wind profile | Synthetic seasonal/diurnal or PROJECT DATA CSV |
| Architecture mix | Captive / Hybrid mix % (selected assets sum to 100%) |
| Charge stacks | DISCOM / Solar / Wind line items; BESS = Storage tariff |
| Currency | INR (₹) |

**Hidden / retired from register:** generation-plant CAPEX/OPEX, plant MW as commercial inputs, Optimization plant invent.

**Warning:** Replace DEFAULT_ASSUMPTION tariffs, mix %, load, profiles, and compliance targets with project data before board decisions.

---

## 4. What you configure (Project Setup groups)

| Group | Controls | Notes |
|-------|----------|-------|
| General / study period | Start-end month, year, model hours | Top bar period drives analysis hours |
| Load | IT, PUE, peak, Seasonal TOD, LF S1-S4 | Demand shape only |
| Solar / Wind | CF %, sunrise/sunset (solar), variability, profile source | Shapes for **hourly** availability; annual MWh from mix % |
| Architecture — Captive | Solar / Wind / BESS flags + mix % + stacks + Storage tariff | No DISCOM |
| Architecture — Hybrid | DISCOM + Solar / Wind / BESS flags + mix % + stacks | DISCOM % is contracted grid share |
| Charge stacks | DISCOM / Solar / Wind ₹/kWh lines | Totals calculated |
| Cost blend basis | TARGET_POWER_PCT / SIMULATED_ENERGY_SHARE | Both = Architecture mix % for the **bill** |
| Compliance | Annual RE, hourly CFE, RPO/RCO, ESO, grid EF | RE/CFE actuals = availability; RPO = Architecture mix |
| Financial | Discount rate, escalations, project life | NPV of **savings vs DISCOM** |

---

## 5. Source tags (in-app Assumptions register)

| Source | Meaning |
|--------|---------|
| CONCEPT_NOTE | Stated in product concept (editable unless locked) |
| DEFAULT_ASSUMPTION | Starter value — replace before decisions |
| USER_INPUT | Entered or saved from Project Setup |
| CALCULATED | Derived (e.g. peak = IT × PUE, stack totals, derived BESS size) |

---

## 6. Results driven by these assumptions

| Output | Driven by |
|--------|-----------|
| ₹/kWh, annual bill, savings, NPV | Architecture mix % × tariffs |
| Target / Simulated (Economics) | Architecture Grid% / RE% (bill shares) |
| Annual RE %, hourly CFE, heatmap | TOD / availability dispatch |
| Architecture CF % (analytics card) | Contracted Solar%+Wind%+BESS% (bill mix — not forced hourly) |
| RPO/RCO | Architecture RE mix |
| ESO | Contracted BESS mix × annual load |
| Charts | Available Solar / Wind / BESS / DISCOM each hour |
