# Model Methodology (Commercial buyer path)

PowerTrain Optimizer prices **data-centre power procurement**:

1. **Bill** — Architecture mix % × DISCOM / Solar / Wind / Storage tariff stacks  
2. **Hourly CFE and charts** — TOD / availability shapes (solar not available at night; wind and BESS can be)

It is **not** a generation-plant investment or plant-sizing CAPEX model.

---

## 1. Horizon and load

- **Study period:** Start month to end month × calendar year. Model hours = days in range × 24 (non-leap full year = **8,760**).
- **Peak load:** Peak_MW = IT_load_MW × PUE (calculated).
- **Load shape:** Seasonal TOD (Summer / Rainy / Winter × day/night × weekday/weekend), then scaled to each load-factor scenario (S1-S4). Headline KPIs use **S1**.
- **Annual load (MWh):** Sum of hourly load over the study.
- Load TOD shapes **demand only**. Solar night availability comes from the **solar** profile (sunrise-sunset), not from load TOD alone.

---

## 2. Architecture mix (bill) vs hourly availability (CFE)

For each architecture, selected assets mix % **sum to 100%**:

| Architecture | Assets |
|--------------|--------|
| Captive | Solar + Wind + BESS (no DISCOM) |
| Hybrid | DISCOM + Solar + Wind + BESS |
| DISCOM baseline | Grid 100% (savings / NPV comparator only) |

### 2.1 Bill (Architecture %)

Blended ₹/kWh =

`Discom × (G/100) + Solar × (S/100) + Wind × (W/100) + Storage_tariff × (B/100)`

- DISCOM / Solar / Wind rates = sum of volumetric charge-stack lines.
- BESS = single **Storage tariff** (`excel_bess_ppa_inr_per_kwh`).
- **TARGET_POWER_PCT** and **SIMULATED_ENERGY_SHARE** both use Architecture contracted mix % for the bill (Target = Simulated on pricing).

### 2.2 Hourly delivery (shapes scaled to annual contracts)

Annual energy contracts:

- Sum Solar_t = Load_annual × Solar%/100  
- Sum Wind_t = Load_annual × Wind%/100  

Hourly shapes:

- Taken from synthetic CF curves (solar: zero outside sunrise-sunset; wind: seasonal/diurnal) or PROJECT DATA.
- Scaled so annual MWh matches the contract. **Solar remains ~0 at night.**
- If BESS mix > 0: derived storage power ~ Peak × BESS%/100 and energy ~ max(4h × power, contracted BESS MWh / days) so excess day RE can charge and discharge at night.
- DISCOM included: grid import cap ~ peak (procurement backup). Captive: grid cap = 0.

---

## 3. Annual bill, ₹/kWh, savings and NPV

- **Annual energy Rs** = annual_load_MWh × blended × 1000  
- **Annual bill ₹ Cr** = energy + demand + fixed + compliance + additional costs  
- **Power cost ₹/kWh** = Year-1 total bill / annual load kWh (TOTAL COST OF DELIVERED ENERGY — not plant LCOE)  
- **Demand charge** = Peak_MW × DISCOM%/100 × demand Rs/MW-month × 12  
- **Savings vs DISCOM** = 100% DISCOM bill - architecture bill  
- **NPV of savings** = PV of yearly savings over project life at discount rate (Year-0 plant CAPEX = 0)

---

## 4. Annual RE % and 24×7 CFE (availability)

### 4.1 Annual RE % (energy-weighted)

`RE% = (Sum RE_serving_load_t) / (Sum Load_t) × 100`

where RE_serving_load_t = direct Solar+Wind to load + RE-origin BESS discharge.

Compared to `annual_re_target_pct`. This is **not** forced equal to Architecture Solar%+Wind%+BESS% every hour.

### 4.2 Hourly CFE %

`CFE_t = Min(Load_t, Solar_t + Wind_t + RE_BESS_discharge_t) / Load_t × 100`

(If Load_t ~ 0, CFE_t is treated as 100%.)

- **Day:** solar can dominate CF supply (within shape).  
- **Night:** solar ~ 0; CFE from **wind** and/or **BESS**; otherwise CFE falls and may Fail the 24×7 rule.

**Pass rule:** every study hour >= `hourly_cfe_target_pct` (min hourly CFE >= target).

**Architecture CF %** in analytics = contracted Solar%+Wind%+BESS% (bill / mix reference). Min hourly CFE is often **below** that when night coverage is weak.

---

## 5. Carbon

- Baseline tCO₂ = load_MWh × grid EF  
- Actual tCO₂ = load_MWh × (DISCOM%/100) × grid EF  
- Carbon saved = baseline - actual  

---

## 6. Compliance

| Metric | Actual basis |
|--------|----------------|
| Annual RE | Energy-weighted RE serving load (availability) |
| Hourly CFE | Availability formula above |
| RPO/RCO | Architecture RE % of DC load (contracted obligation) |
| ESO | Contracted BESS mix % × annual load (MWh); RE-origin framing = 100% for contracted Storage |

Feasibility for Captive/Hybrid gates on RE/CFE (and Applicable RPO/ESO) — **not** on plant-profile unserved (commercial `unserved_mwh` = 0).

---

## 7. Charts and diagnostics

Hourly charts show **available** Load / Solar / Wind / BESS charge-discharge / DISCOM import and hourly CFE.

Series note: Architecture mix sets annual contract energy and the bill; CFE is availability each hour (solar ~0 at night).

---

## 8. Out of scope

Generation-plant CAPEX / OPEX / debt as commercial inputs; Optimization / Sensitivity plant invent; treating Architecture mix % as flat firm CFE every hour.
