# -*- coding: utf-8 -*-
"""Replace in-app Assumptions + Methodology with detailed buyer-path copy."""
from pathlib import Path

p = Path("frontend/dist/assets/app.js")
t = p.read_text(encoding="utf-8")

start = t.find("function pageAssumptions() {")
end = t.find("function pageSettings() {")
if start < 0 or end < 0 or end <= start:
    raise SystemExit(f"markers not found start={start} end={end}")

new = r'''function pageAssumptions() {
  const rows = state.project.assumptions || [];
  const cfg = state.project?.config || {};
  const blend = cfg.commercial?.cost_blend_basis?.value || "TARGET_POWER_PCT";
  const mixG = fmt(cfg.commercial?.mix_discom_pct?.value, 0);
  const mixS = fmt(cfg.commercial?.mix_solar_pct?.value, 0);
  const mixW = fmt(cfg.commercial?.mix_wind_pct?.value, 0);
  const mixB = fmt(cfg.commercial?.mix_bess_pct?.value, 0);
  const lf1 = fmt(cfg.load?.load_factor_s1_pct?.value ?? cfg.load?.load_factor_pct?.value, 0);
  const lf2 = fmt(cfg.load?.load_factor_s2_pct?.value, 0);
  const lf3 = fmt(cfg.load?.load_factor_s3_pct?.value, 0);
  const lf4 = fmt(cfg.load?.load_factor_s4_pct?.value, 0);
  const storage = fmt(cfg.commercial?.excel_bess_ppa_inr_per_kwh?.value, 4);
  const period = studyPeriodLabel(cfg);
  const year = cfg.general?.calendar_year?.value || "";
  const reT = fmt(cfg.compliance?.annual_re_target_pct?.value, 0);
  const cfeT = fmt(cfg.compliance?.hourly_cfe_target_pct?.value, 0);
  const ef = fmt(cfg.compliance?.grid_emission_factor_tco2_per_mwh?.value, 2);
  const rpoT = fmt(cfg.compliance?.rpo_rco_target_pct?.value, 0);
  const esoT = fmt(cfg.compliance?.eso_target_pct?.value, 1);
  return `
  <div class="panel">
    <div class="section-eyebrow">Assumptions</div>
    <h3 style="margin:0 0 0.5rem">Active project assumptions</h3>
    <p class="muted" style="margin:0 0 0.85rem;font-size:0.88rem;line-height:1.5">
      Live register of parameters that drive <b>Captive</b> and <b>Hybrid</b> (both entered in Project Setup; one <b>Run Analysis</b> evaluates both).
      The data centre is an <b>energy consumer</b>: Solar / Wind / BESS / DISCOM are <b>contracted Architecture mix %</b> at fixed ₹/kWh.
      Delivery is <b>firm every hour</b> (Load × mix %) — <b>no plant generation shapes</b>, no plant MW / CAPEX / OPEX / SOC.
      <b>DISCOM</b> is the 100% grid savings baseline only — not a selectable architecture.
    </p>
    <div class="kpis" style="margin:0">
      ${kpiCard("Study period", `${period} ${year}`.trim(), { sub: `${currentModelHours()} model hours` })}
      ${kpiCard("Cost blend", String(blend).replaceAll("_", " "), { sub: "Both bases = Architecture contracted mix %" })}
      ${kpiCard("Active mix G|S|W|B", `${mixG}|${mixS}|${mixW}|${mixB} %`, { sub: "Contracted shares (sum 100%)" })}
      ${kpiCard("Storage tariff", `₹${storage}/kWh`, { sub: "BESS ₹/kWh only — no plant size" })}
      ${kpiCard("Load factors", `${lf1} / ${lf2} / ${lf3} / ${lf4} %`, { sub: "S1–S4 · headline KPIs use S1" })}
      ${kpiCard("Tracked params", String(rows.length), { sub: "Filter / search in the register" })}
    </div>
  </div>

  <div class="panel">
    <div class="card-head"><div>
      <div class="section-eyebrow">How to read this page</div>
      <h3 style="margin:0">Source tags</h3>
    </div></div>
    <div class="table-wrap"><table class="data">
      <thead><tr><th>Source</th><th>Meaning</th></tr></thead>
      <tbody>
        <tr><td>${badge("CONCEPT_NOTE")}</td><td>Stated in the product concept note (still editable unless locked).</td></tr>
        <tr><td>${badge("DEFAULT_ASSUMPTION")}</td><td>Starter value — replace with your project data before decisions.</td></tr>
        <tr><td>${badge("USER_INPUT")}</td><td>Value you entered or saved from Project Setup.</td></tr>
        <tr><td>${badge("CALCULATED")}</td><td>Derived by the model (e.g. peak = IT × PUE, stack totals). Not manually edited.</td></tr>
      </tbody>
    </table></div>
  </div>

  <div class="panel">
    <div class="card-head"><div>
      <div class="section-eyebrow">Input groups</div>
      <h3 style="margin:0">What you configure in Project Setup</h3>
    </div></div>
    <div class="table-wrap"><table class="data">
      <thead><tr><th>Group</th><th>What it controls</th><th>Notes</th></tr></thead>
      <tbody>
        <tr><td><b>General / study period</b></td><td>Start–end month, calendar year, model hours</td><td>Top bar study period drives ${currentModelHours()} h analysis.</td></tr>
        <tr><td><b>Load</b></td><td>IT load, PUE, peak, Seasonal TOD, LF S1–S4</td><td>Peak = IT × PUE. Four LF scenarios; KPIs use S1. Load shape is for DC demand only.</td></tr>
        <tr><td><b>Architecture — Captive</b></td><td>Solar / Wind / BESS flags, mix %, Solar/Wind stacks, Storage tariff</td><td>No DISCOM. Mix = contracted energy shares (sum 100%). Firm hourly delivery.</td></tr>
        <tr><td><b>Architecture — Hybrid</b></td><td>DISCOM + Solar / Wind / BESS flags, mix %, all stacks</td><td>DISCOM share is contracted grid %. Baseline savings use 100% DISCOM elsewhere.</td></tr>
        <tr><td><b>Charge stacks</b></td><td>DISCOM / Solar / Wind ₹/kWh line items</td><td>Totals are calculated. BESS = <b>Storage tariff</b> only.</td></tr>
        <tr><td><b>Cost blend basis</b></td><td>TARGET_POWER_PCT vs SIMULATED_ENERGY_SHARE</td><td>Both = Architecture contracted mix % × rates (Target = Simulated).</td></tr>
        <tr><td><b>Compliance</b></td><td>Annual RE ${reT}%, hourly CFE ${cfeT}%, RPO/RCO ${rpoT}%, ESO ${esoT}%, grid EF ${ef}</td><td>Project Setup → Compliance. Actuals use Architecture mix (firm).</td></tr>
        <tr><td><b>Financial (results)</b></td><td>Discount rate, electricity / RE escalation, project life</td><td>NPV of savings vs DISCOM. No generation-plant debt / CAPEX.</td></tr>
      </tbody>
    </table></div>
  </div>

  <div class="panel">
    <div class="card-head"><div>
      <div class="section-eyebrow">Firm delivery</div>
      <h3 style="margin:0">What “no plant shapes” means</h3>
    </div></div>
    <ul style="margin:0.35rem 0 0;padding-left:1.15rem;font-size:0.9rem;line-height:1.55">
      <li><b>Every hour:</b> Solar_MW = Load × Solar%/100; Wind_MW = Load × Wind%/100; DISCOM_MW = Load × DISCOM%/100.</li>
      <li><b>BESS:</b> Mix % × Storage tariff on the bill; BESS% counts in RE/CFE. No BESS plant MW/MWh or SOC.</li>
      <li><b>Night:</b> Solar contract share continues (does not drop to zero). CFE stays at Solar%+Wind%+BESS%.</li>
      <li><b>Removed:</b> Plant CF curves, plant curtailment/SOC charts, plant CAPEX/OPEX/MW fields.</li>
    </ul>
  </div>

  <div class="panel">
    <div class="card-head"><div>
      <div class="section-eyebrow">Results</div>
      <h3 style="margin:0">What drives Dashboard / Economics / Hourly CFE</h3>
    </div></div>
    <ul style="margin:0.35rem 0 0;padding-left:1.15rem;font-size:0.9rem;line-height:1.55">
      <li><b>Both architectures</b> — Captive and Hybrid in one Run Analysis. Tabs only switch detail view.</li>
      <li><b>Blended ₹/kWh</b> — Discom×G% + Solar×S% + Wind×W% + (BESS×Storage tariff if selected).</li>
      <li><b>Target vs Simulated</b> — Both = Architecture contracted mix %.</li>
      <li><b>Annual RE / CFE / RPO</b> — Solar% + Wind% + BESS% (firm).</li>
      <li><b>24×7 CFE Pass</b> — Every hour ≥ target ${cfeT}% (flat firm mix ⇒ min = mean = RE%).</li>
      <li><b>ESO</b> — Required = load × ESO%; actual = load × BESS mix %.</li>
      <li><b>Carbon</b> — Baseline = load × EF; actual = load × DISCOM% × EF; saved = baseline − actual.</li>
      <li><b>Feasibility</b> — Gates on RE/CFE (and Applicable RPO/ESO) — not on plant-profile unserved.</li>
    </ul>
  </div>

  <div class="panel">
    <div class="card-head"><h3 style="margin:0">Assumption register</h3></div>
    <p class="muted" style="margin:0 0 0.65rem;font-size:0.82rem">Search or filter by source. Plant CAPEX / OPEX / MW leftovers are excluded. Descriptions match Project Setup help.</p>
    <div class="row"><label>Filter <select id="assump-filter"><option value="">All</option>
      <option>CONCEPT_NOTE</option><option>DEFAULT_ASSUMPTION</option><option>USER_INPUT</option><option>CALCULATED</option>
    </select></label>
    <input id="assump-q" placeholder="Search parameter" style="flex:1;padding:0.4rem;border:1px solid var(--line);border-radius:7px" /></div>
    <div class="table-wrap" style="margin-top:0.8rem"><table>
      <thead><tr><th>Parameter</th><th>Value</th><th>Unit</th><th>Source</th><th>Description</th></tr></thead>
      <tbody id="assump-body">${rows.map(r => `<tr data-src="${r.source}" data-p="${r.parameter}"><td>${r.parameter}</td><td class="mono">${fmtValue(r.value)}</td><td>${r.unit}</td><td>${badge(r.source)}</td><td>${r.description}</td></tr>`).join("")}</tbody>
    </table></div>
  </div>`;
}

function pageMethodology() {
  const hours = currentModelHours();
  const sm = Math.max(1, Math.min(12, Number(state.project?.config?.general?.study_start_month?.value) || 1));
  const em = Math.max(1, Math.min(12, Number(state.project?.config?.general?.study_end_month?.value) || 12));
  const period = studyPeriodLabel(state.project?.config);
  const year = state.project?.config?.general?.calendar_year?.value || "-";
  const studyYr = Number(state.project?.config?.load?.study_years?.value);
  const studyYrTxt = Number.isFinite(studyYr) ? fmt(studyYr, 2) : fmt((em - sm + 1) / 12, 2);
  const ef = Number(state.project?.config?.compliance?.grid_emission_factor_tco2_per_mwh?.value) || 0.82;
  const blend = state.project?.config?.commercial?.cost_blend_basis?.value || "TARGET_POWER_PCT";
  const reT = fmt(state.project?.config?.compliance?.annual_re_target_pct?.value, 0);
  const cfeT = fmt(state.project?.config?.compliance?.hourly_cfe_target_pct?.value, 0);
  const rpoT = fmt(state.project?.config?.compliance?.rpo_rco_target_pct?.value, 0);
  const esoT = fmt(state.project?.config?.compliance?.eso_target_pct?.value, 1);
  return `
  <div class="panel">
    <div class="section-eyebrow">Methodology</div>
    <h3 style="margin:0 0 0.35rem">Model methodology (V${state.project.model_version || "2.0.0"})</h3>
    <p class="muted" style="margin:0;font-size:0.88rem;line-height:1.5">
      Detailed rules for the commercial data-centre <b>buyer</b> path: Captive and Hybrid procurement as
      <b>Architecture mix % × tariff / PPA stacks</b>, with <b>firm hourly delivery</b> (no plant generation shapes).
      Full reference also lives in <code>MODEL_METHODOLOGY.md</code> and <code>ASSUMPTIONS.md</code>.
    </p>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">1. Product scope</h3>
    <p><b>Viewpoint:</b> You buy power for a data centre (DISCOM + Solar / Wind / BESS PPAs). Outputs: power bill, RE/CFE mix, 24×7 CFE Pass/Fail, carbon saved, savings / NPV vs 100% DISCOM.</p>
    <p><b>Architectures:</b> Configure <b>Captive</b> and <b>Hybrid</b> in Project Setup. One <b>Run Analysis</b> evaluates both as equals. DISCOM column = 100% grid baseline only.</p>
    <p><b>In scope:</b> Study period, load (IT / PUE / Seasonal TOD / LF S1–S4), Architecture flags + mix % (sum 100%), charge stacks, Storage tariff, Compliance, discount / escalation for NPV of savings.</p>
    <p><b>Out of scope:</b> Generation-plant CAPEX / OPEX / debt, plant MW–MWh sizing, plant SOC / curtailment as commercial metrics, Optimization / Sensitivity plant invent.</p>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">2. Study period &amp; load</h3>
    <p><b>Period:</b> <b>${period} ${year}</b>. Model hours = days × 24 = <b>${hours} h</b>. Study years ≈ <b>${studyYrTxt} yr</b>.</p>
    <p><b>Peak:</b> Peak_MW = IT_load_MW × PUE (calculated).</p>
    <p><b>DC load shape:</b> Seasonal TOD multipliers, then scaled to each LF scenario. This shapes <b>demand only</b> — not Solar/Wind plant CF.</p>
    <p><b>LF scenarios:</b> S1–S4 in one run; headline KPIs use <b>S1</b>.</p>
    <p><b>Annual load (MWh):</b> Σ hourly load (scenario LF applied).</p>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">3. Architecture mix &amp; firm delivery</h3>
    <p><b>Mix %:</b> Selected assets sum to 100%.</p>
    <ul style="margin:0.35rem 0 0.75rem;padding-left:1.15rem;line-height:1.5">
      <li><b>Captive:</b> Solar + Wind + BESS (no DISCOM).</li>
      <li><b>Hybrid:</b> DISCOM + Solar + Wind + BESS.</li>
    </ul>
    <p><b>Firm hourly contracts (no plant shapes):</b></p>
    <p class="mono" style="margin:0.35rem 0 0.5rem;font-size:0.88rem">Solar_t = Load_t × Solar%/100<br>Wind_t = Load_t × Wind%/100<br>DISCOM_t = Load_t × DISCOM%/100</p>
    <p>BESS% is billed at Storage tariff and counted in RE/CFE; there is <b>no BESS plant MW/MWh/SOC</b>. Night solar contract share does <b>not</b> go to zero.</p>
    <p><b>Rates:</b> DISCOM / Solar / Wind = sum of stack lines; BESS = Storage tariff only.</p>
    <p class="mono" style="margin:0.35rem 0 0;font-size:0.9rem">Blended = Discom×(G/100) + Solar×(S/100) + Wind×(W/100) + Storage×(B/100)</p>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">4. Cost blend — Target = Simulated</h3>
    <p>Current setting: <code>${escHtml(String(blend))}</code></p>
    <div class="table-wrap" style="margin:0.65rem 0"><table class="data">
      <thead><tr><th>Basis</th><th>How shares are set</th><th>When to use</th></tr></thead>
      <tbody>
        <tr><td><b>TARGET_POWER_PCT</b></td><td>Bill uses Architecture mix % (G|S|W|B).</td><td>Default — contracted mix pricing.</td></tr>
        <tr><td><b>SIMULATED_ENERGY_SHARE</b></td><td>Same as Target (contracted mix %). No plant MW inventing.</td><td>Equals Target on the buyer path.</td></tr>
      </tbody>
    </table></div>
    <p><b>Economics Target | Simulated (Grid | RE):</b> Both show Architecture Grid% | RE% (Solar+Wind+BESS) and match by design.</p>
    <p><b>Demand charge:</b> Peak_MW × DISCOM% × demand ₹/MW-month × 12.</p>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">5. Annual bill, ₹/kWh, savings &amp; NPV</h3>
    <ul style="margin:0;padding-left:1.15rem;line-height:1.55">
      <li><b>Annual energy ₹</b> = annual_load_MWh × blended_₹/kWh × 1000.</li>
      <li><b>Annual bill ₹ Cr</b> = annual energy ₹ / 1e7 (+ demand / fixed / compliance / additional lines if set).</li>
      <li><b>Power cost ₹/kWh</b> = Year-1 total bill ÷ annual load kWh (buyer TOTAL COST OF DELIVERED ENERGY — not plant LCOE).</li>
      <li><b>Savings vs DISCOM (₹ Cr/yr)</b> = (100% DISCOM bill − architecture bill) / 1e7.</li>
      <li><b>NPV of savings (₹ Cr)</b> = PV of yearly savings over project life at discount rate (÷ 1e7). Year-0 plant CAPEX = 0.</li>
    </ul>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">6. Annual RE %, 24×7 CFE &amp; carbon</h3>
    <p><b>Architecture RE / CFE mix:</b></p>
    <p class="mono" style="margin:0.35rem 0 0.65rem;font-size:0.88rem">RE% = Solar% + Wind% + BESS%</p>
    <p>Compared to annual RE target <b>${reT}%</b>. Same value every hour (firm).</p>
    <p><b>24×7 Hourly CFE:</b></p>
    <p class="mono" style="margin:0.35rem 0 0.65rem;font-size:0.88rem">CFE% = Min(Load, Load × (Solar%+Wind%+BESS%)/100) / Load × 100</p>
    <p><b>Pass:</b> every hour ≥ target <b>${cfeT}%</b> ⇔ min hourly CFE ≥ ${cfeT}%. With firm mix, min = mean = RE%.</p>
    <p><b>Carbon:</b> Baseline = load_MWh × EF (<b>${fmt(ef, 2)}</b>). Actual = load × (DISCOM%/100) × EF. Saved = baseline − actual.</p>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">7. Compliance &amp; feasibility</h3>
    <p>Edited under <b>Project Setup → Compliance</b>.</p>
    <ul style="margin:0.35rem 0 0.75rem;padding-left:1.15rem;line-height:1.55">
      <li><b>RPO/RCO:</b> Target ${rpoT}% of DC load; actual = Architecture RE % (Solar+Wind+BESS).</li>
      <li><b>ESO:</b> Target ${esoT}% of load; actual storage MWh = load × BESS mix % (contracted).</li>
      <li><b>Hourly CFE:</b> As in §6.</li>
      <li><b>Feasibility:</b> RE/CFE (and Applicable RPO/ESO). Plant-profile unserved is ignored on the buyer path.</li>
    </ul>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">8. Dashboard, Economics &amp; charts</h3>
    <p><b>Dashboard / Economics:</b> Captive vs Hybrid compare; tabs switch detail. No Status ranking of architectures.</p>
    <p><b>Hourly charts:</b> Contracted Load / Solar / Wind(+BESS) / CF / DISCOM and firm CFE only — no plant SOC or plant curtailment series.</p>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">9. Workflow</h3>
    <ol style="margin:0;padding-left:1.2rem;line-height:1.55;font-size:0.9rem">
      <li>Create or Open project → set study period in the top bar.</li>
      <li>Project Setup: Load → Architecture for Captive and Hybrid (flags, mix 100%, stacks, Storage tariff) → Compliance.</li>
      <li>Save Project (.pto.zip) as needed.</li>
      <li><b>Run Analysis</b> — both architectures refresh.</li>
      <li>Dashboard compare → CAPTIVE / HYBRID tabs → Economics / Hourly CFE → Reports.</li>
      <li>Use <b>Assumptions</b> to audit sources; this page for formulas.</li>
    </ol>
  </div>

  <div class="panel">
    <p class="muted" style="margin:0;font-size:0.88rem;line-height:1.45">
      The Assumptions register lists live parameters (CONCEPT_NOTE / DEFAULT / USER / CALCULATED).
      Plant CAPEX / OPEX / MW leftovers are excluded. See also ASSUMPTIONS.md and MODEL_METHODOLOGY.md in the repository.
    </p>
  </div>`;
}

'''

t = t[:start] + new + t[end:]
p.write_text(t, encoding="utf-8")

html = Path("frontend/dist/index.html")
h = html.read_text(encoding="utf-8")
for o in ("?v=141", "?v=140", "?v=139"):
    h = h.replace(o, "?v=142")
html.write_text(h, encoding="utf-8")
print("replaced", "Firm delivery" in t, "pageAssumptions" in t, "v142", "?v=142" in h)
