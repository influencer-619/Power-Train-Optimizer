# Model Methodology

## Horizon

Normal year: **8,760** hours. Leap-year support is reserved for **8,784** hours (not enabled by default).

## Load

Parameterized shape (flat / diurnal / weekday-weekend / seasonal / custom) scaled so mean ≈ peak × load factor, compressed if needed so max ≤ peak.

## Solar

Daylight-only Gaussian diurnal shape × seasonal factors × deterministic noise, scaled to target capacity factor and clipped to capacity. Night = 0.

## Wind

Monthly factors × mild diurnal × deterministic noise, scaled to CF, clipped to capacity.

## Dispatch (rule-based default)

Each hour:

1. Renewable serves load  
2. Excess RE charges BESS (SOC / power limits, charge efficiency)  
3. Remaining RE curtailed  
4. BESS discharges on deficit (SOC / power limits, discharge efficiency)  
5. Grid serves residual (≤ available import capacity)

Optional grid charging if enabled.

### SOC

\[
SOC_t = SOC_{t-1} + Charge_t - Discharge_t
\]

subject to \(SOC_{min} \le SOC_t \le SOC_{max}\).
Charge and discharge are each limited by `bess.power_mw`. Conversion efficiency is modelled as ideal (100%).

### Power balance

\[
Solar_t + Wind_t + Discharge_t + Grid_t = Load_t + Charge_t + Curtailment_t (+ Unserved_t)
\]

Validated each hour within tolerance.

## Renewable-origin tracking

Charge increments RE-origin / grid-origin SOC buckets. Discharge depletes proportionally. ESO checks RE-origin share of stored energy (≥ 85% from concept note when applicable).

## Annual RE %

\[
\frac{\sum RE\_serving\_load_t}{\sum Load_t} \times 100
\]

## Hourly CFE %

\[
CFE_t = \frac{RE\_serving\_load_t}{Load_t} \times 100
\]

Pass modes: all hours ≥ target | mean ≥ target | share of hours ≥ target.

Energy-weighted mean CFE equals annual RE%; unweighted mean and minimum generally differ.

## Commercial cost

Structure-specific stacking of grid energy (incl. TOD), demand/fixed charges, RE energy tariffs, network charges, OPEX, annualized CAPEX (CRF), compliance costs.

## Financials

Year-0 CAPEX (if included), escalated annual costs, BESS replacement, residual value. NPV at discount rate. IRR via Newton/bisection. Incremental NPV/IRR/payback vs DISCOM baseline.

## Optimization

Staged:

1. Capacity candidate set (Quick / Standard / Thorough)  
2. 8,760 dispatch per candidate  
3. Feasibility (unserved / RE / CFE flags)  
4. Economic evaluation  
5. Rank by objective; local neighborhood refine; return top 10  

Optional LP dispatch (SciPy HiGHS, weekly blocks) when selected.
