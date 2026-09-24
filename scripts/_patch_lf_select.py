# -*- coding: utf-8 -*-
"""Make LF scenario rows selectable; drive dashboard headline KPIs from selection."""
from pathlib import Path

app = Path("frontend/dist/assets/app.js")
t = app.read_text(encoding="utf-8")

pd = t.find("function pageDashboard()")
if pd < 0:
    raise SystemExit("pageDashboard not found")
start = t.find("  const k = s.kpis || {};", pd)
marker = '\n  <div class="grid two">\n    <div class="panel" style="margin:0">\n      <div class="card-head"><h3 style="margin:0">Tariff blend'
end = t.find(marker, start)
if start < 0 or end < 0:
    raise SystemExit(f"bounds not found start={start} end={end}")

new_block = r'''  const k = s.kpis || {};
  const f = s.financial || {};
  const xt = f.excel_tariff || {};
  const carbon = f.carbon || {};
  const lfScenarios = s.lf_scenarios || f.lf_scenarios || [];
  const selectedLf = (() => {
    if (!lfScenarios.length) return null;
    const want = state.selectedLfId != null ? Number(state.selectedLfId) : Number(lfScenarios[0].id);
    return lfScenarios.find((r) => Number(r.id) === want) || lfScenarios[0];
  })();
  if (selectedLf && state.selectedLfId == null) state.selectedLfId = selectedLf.id;
  const loadMwh = Number(
    selectedLf?.annual_load_mwh ?? xt.annual_load_mwh ?? carbon.annual_load_mwh ?? k.annual_load_mwh
  ) || 0;
  const cfePct = Number(
    selectedLf?.cfe_pct ?? xt.cfe_pct ?? carbon.cfe_pct ?? xt.re_pct ?? k.annual_re_pct
  ) || 0;
  const carbonSaved = Number(
    selectedLf?.carbon_saved_tco2 ?? xt.carbon_saved_tco2 ?? carbon.carbon_saved_tco2
  ) || 0;
  const baselineT = Number(
    selectedLf?.baseline_tco2 ?? xt.baseline_tco2 ?? carbon.baseline_tco2
  ) || 0;
  const actualT = Number(
    selectedLf?.actual_tco2 ?? xt.actual_tco2 ?? carbon.actual_tco2
  ) || 0;
  const gridPct = Number(xt.grid_pct ?? 0);
  const rePct = Number(xt.re_pct ?? cfePct);
  const solarPct = Number(xt.solar_pct ?? 0);
  const windPct = Number(xt.wind_pct ?? 0);
  const bessPct = Number(xt.bess_pct ?? 0);
  const reT = s.compliance?.annual_re?.target_pct ?? state.project.config.compliance.annual_re_target_pct.value;
  const reOk = cfePct >= reT;
  const ca = s.cfe_analytics || k.cfe_analytics || {};
  const hc = s.compliance?.hourly_cfe || {};
  const hourlyMin = Number(
    selectedLf?.hourly_cfe_min_pct ?? ca.min_hourly_cfe_pct ?? k.hourly_cfe_min_pct ?? hc.min_pct
  );
  const hourlyMean = Number(
    selectedLf?.hourly_cfe_mean_pct ?? ca.mean_hourly_cfe_pct ?? k.hourly_cfe_mean_pct ?? hc.mean_pct
  );
  const hourlyTarget = Number(ca.target_pct ?? hc.target_pct ?? state.project?.config?.compliance?.hourly_cfe_target_pct?.value) || 90;
  const hourlyPass =
    selectedLf?.hourly_cfe_passed === true || selectedLf?.hourly_cfe_passed === false
      ? !!selectedLf.hourly_cfe_passed
      : (ca.passed === true || hc.status === "Pass");
  const hoursGe = Number(
    selectedLf?.hours_meeting_cfe_target_pct ?? ca.pct_hours_ge_target ?? k.hours_meeting_cfe_target_pct ?? hc.hours_meeting_pct
  );
  const longestGap = Number(
    selectedLf?.longest_continuous_deficit_hours ?? ca.longest_continuous_deficit_hours
  );
  const maxDeficit = Number(
    selectedLf?.max_cfe_deficit_pp ?? ca.max_cfe_deficit_pp
  );
  const costPerKwh = Number(selectedLf?.cost_per_kwh ?? f.cost_per_kwh) || 0;
  const annualBillCr = Number(
    selectedLf?.annual_bill_cr ?? selectedLf?.annual_energy_cr ?? xt.annual_bill_cr ?? xt.annual_energy_cr ?? 0
  ) || 0;
  const savingsCr = Number(selectedLf?.savings_vs_discom_cr ?? xt.savings_vs_discom_cr ?? 0) || 0;
  const npvCr = Number(selectedLf?.npv_cr ?? f.npv_cr) || 0;
  const costLabel = f.cost_metric_label || "ENERGY COST";
  const period = studyPeriodLabel(state.project?.config);
  const year = state.project?.config?.general?.calendar_year?.value || "";
  const archLabel = String(viewArch || s.structure || "").replaceAll("_", " ");
  const lfLabel = selectedLf ? (selectedLf.label || (`LF ${fmt(selectedLf.load_factor_pct, 0)}%`)) : "Scenario 1";
  const s1Load = Number(lfScenarios[0]?.annual_load_mwh) || loadMwh || 1;
  const lfScale = loadMwh / (s1Load || 1);

  const lfTable = lfScenarios.length
    ? `<div class="panel">
        <div class="card-head">
          <div>
            <div class="section-eyebrow">Scenarios · ${escHtml(archLabel)}</div>
            <h3 style="margin:0">Load-factor comparison</h3>
          </div>
          <span class="pill muted">${lfScenarios.length} LFs</span>
        </div>
        <p class="muted" style="margin:0 0 0.75rem;font-size:0.82rem">These LF rows are for <b>${escHtml(archLabel)}</b> only. Click a row to update headline KPIs. Selected: <b>${escHtml(lfLabel)}</b>.</p>
        <div class="table-wrap"><table class="data lf-select-table">
          <thead><tr>
            <th>Scenario</th>
            <th title="Load factor % for this scenario">LF %</th>
            <th title="DC energy (MWh) = peak × LF × study hours / 1000">Energy MWh</th>
            <th title="Energy Cost ₹/kWh = blended rate (Captive/Hybrid) or DISCOM rate">INR/kWh</th>
            <th title="Annual energy bill ₹ Cr = Energy Cost × load kWh / 1e7">Bill Cr</th>
            <th title="Year-1 savings vs 100% DISCOM bill (₹ Cr)">Savings Cr</th>
            <th title="Architecture RE mix % for this LF">RE %</th>
            <th title="Carbon saved vs 100% DISCOM baseline (tCO2)">Carbon tCO2</th>
            <th title="NPV of yearly savings vs DISCOM over project life, discounted (₹ Cr)">NPV Cr</th>
          </tr></thead>
          <tbody>
            ${lfScenarios.map((row) => {
              const sel = selectedLf && Number(row.id) === Number(selectedLf.id);
              return `<tr class="lf-row${sel ? " best-row selected-lf" : ""}" data-set-lf="${escHtml(String(row.id))}" role="button" tabindex="0" title="Show headline KPIs for ${escHtml(row.label || ("S" + row.id))}">
              <td>${escHtml(row.label || ("S" + row.id))}${sel ? ' <span class="pill muted">selected</span>' : ""}</td>
              <td class="mono">${fmt(row.load_factor_pct, 1)}</td>
              <td class="mono">${fmtEnergy(row.annual_load_mwh, 2)}</td>
              <td class="mono">${fmt(row.cost_per_kwh, 4)}</td>
              <td class="mono">${fmt(row.annual_energy_cr, 2)}</td>
              <td class="mono">${fmt(row.savings_vs_discom_cr, 2)}</td>
              <td class="mono">${fmt(row.cfe_pct, 1)}</td>
              <td class="mono">${fmtEnergy(row.carbon_saved_tco2, 0)}</td>
              <td class="mono">${fmt(row.npv_cr, 2)}</td>
            </tr>`;
            }).join("")}
          </tbody>
        </table></div>
      </div>`
    : "";

  const tipDcEnergy = `DC energy (MWh) = peak load × load factor × study hours / 1000 (${lfLabel}).`;
  const tipFromDiscom = "From DISCOM (MWh) = DC energy × DISCOM % of power / 100.";
  const tipFromRe = "From RE / PPA (MWh) = DC energy × (Solar% + Wind% + BESS%) / 100.";
  const tipCfeMix = "CFE (mix) = Architecture contracted RE share for the bill (Solar% + Wind% + BESS%). Hourly CFE Pass uses TOD availability, not this flat mix.";
  const tipCarbon = "Carbon saved (tCO2) = baseline emissions (100% DISCOM × grid EF) − actual emissions of the architecture mix.";
  const tipPowerCost = "Energy Cost (₹/kWh) = blended rate (Captive/Hybrid: Discom×G% + Solar×S% + Wind×W% + BESS×Storage%) or DISCOM stack rate. Demand/fixed/compliance are separate.";
  const tipAnnualBill = "Annual energy bill (₹ Cr) = Energy Cost ₹/kWh × annual load kWh / 1e7. Demand/fixed shown separately.";
  const tipSavings = "Savings vs DISCOM (₹ Cr/yr) = (100% DISCOM bill − architecture bill) / 1e7 for Year-1.";
  const tipNpv = "NPV of savings (₹ Cr) = present value of yearly (DISCOM bill − architecture bill) over project life, discounted at financial discount rate. Display = NPV ₹ / 1e7.";
  const tipHourlyMin = "Hourly CFE min = lowest hour in the study. Hourly CFE% = Min(Load, Solar+Wind+RE-BESS available) ÷ Load × 100 (TOD shapes). Night hours with no solar and little wind/BESS can be ~0% — this is not the flat Architecture RE mix %.";
  const tipMeanHour = "Mean hourly CFE = unweighted average of hourly CFE % across all study hours.";
  const tipHoursGe = "% of study hours where hourly CFE ≥ target. Longest gap = longest continuous streak of hours below target.";
  const tipMaxDef = "Max deficit (pp) = largest (target − hourly CFE) in percentage points among hours below target.";

  return `
  ${s.results_stale ? `<div class="banner danger">STALE RESULTS - inputs changed after this run. Click <b>Run Analysis</b> again.</div>` : ""}

  ${architectureComparePanelHtml(state.compare)}

  <div class="panel dash-detail" style="margin-top:0.85rem">
    <div class="card-head">
      <div>
        <div class="section-eyebrow">Architecture detail</div>
        <h3 style="margin:0">Showing: ${escHtml(archLabel)}</h3>
      </div>
    </div>
    <p class="muted" style="margin:0.35rem 0 0.65rem;font-size:0.85rem;line-height:1.45">
      Cards and charts below are for <b>${escHtml(archLabel)}</b> · <b>${escHtml(lfLabel)}</b>. Switch architecture tab or click an LF row to update KPIs.
    </p>
    ${architectureTabsHtml("dashboard")}
  </div>

  ${lfTable}

  <section class="dash-hero">
    <div class="dash-hero-copy">
      <p class="eyebrow">${escHtml(archLabel)} · ${escHtml(lfLabel)}</p>
      <h2>${escHtml(archLabel)} results</h2>
      <p>${escHtml(period)} ${escHtml(String(year))} · ${currentModelHours()} h study · mix × tariff / PPA stacks</p>
    </div>
    <div class="dash-hero-metrics">
      <div class="dash-hero-metric has-tip" data-tip="${escHtml(tipPowerCost)}" title="${escHtml(tipPowerCost)}">
        <div class="k">Energy Cost · ${escHtml(archLabel)}</div>
        <div class="v">₹${fmt(costPerKwh, 4)}</div>
        <div class="s">blended / DISCOM energy rate</div>
      </div>
      <div class="dash-hero-metric has-tip" data-tip="${escHtml(tipSavings)}" title="${escHtml(tipSavings)}">
        <div class="k">Savings · ${escHtml(archLabel)}</div>
        <div class="v">${fmt(savingsCr, 1)} Cr</div>
        <div class="s">vs 100% DISCOM / yr · ${escHtml(lfLabel)}</div>
      </div>
      <div class="dash-hero-metric has-tip" data-tip="${escHtml(tipCfeMix)}" title="${escHtml(tipCfeMix)}">
        <div class="k">CFE mix · ${escHtml(archLabel)}</div>
        <div class="v">${fmt(cfePct, 1)}%</div>
        <div class="s">target ${fmt(reT, 0)}% · ${reOk ? "on track" : "below"}</div>
      </div>
    </div>
  </section>

  <div class="page-section">
    <div class="section-head">
      <div>
        <div class="section-eyebrow">Energy & carbon · ${escHtml(archLabel)}</div>
        <h3>Supply and emissions</h3>
      </div>
      <p class="lede">${escHtml(archLabel)} · ${escHtml(lfLabel)} load split. Hover any card for the formula.</p>
    </div>
    <div class="kpis">
      ${kpiCard("DC energy", fmtEnergy(loadMwh, 2) + " MWh", { icon: "E", sub: `${archLabel} · ${lfLabel}`, tip: tipDcEnergy })}
      ${kpiCard("From DISCOM", fmtEnergy(loadMwh * gridPct / 100, 2) + " MWh", { icon: "G", sub: `${fmt(gridPct, 1)}% of supply`, tip: tipFromDiscom })}
      ${kpiCard("From RE / PPA", fmtEnergy(loadMwh * rePct / 100, 2) + " MWh", { icon: "R", sub: `Solar ${fmt(solarPct,0)}% · Wind ${fmt(windPct,0)}% · BESS ${fmt(bessPct,0)}%`, tip: tipFromRe })}
      ${kpiCard("CFE (mix)", fmt(cfePct, 1) + "%", { icon: "C", sub: `Target ${fmt(reT, 0)}% · ${reOk ? "On track" : "Below target"}`, trend: reOk ? "achieved" : "", progress: Math.min(100, cfePct), tip: tipCfeMix })}
      ${kpiCard("Carbon saved", fmtEnergy(carbonSaved, 0) + " tCO2", { icon: "CO2", sub: `Baseline ${fmtEnergy(baselineT, 0)} → ${fmtEnergy(actualT, 0)} tCO2`, tip: tipCarbon })}
    </div>
  </div>

  <div class="page-section">
    <div class="section-head">
      <div>
        <div class="section-eyebrow">Commercial · ${escHtml(archLabel)}</div>
        <h3>Bill and value vs DISCOM</h3>
      </div>
      <p class="lede">${escHtml(archLabel)} · ${escHtml(lfLabel)} · ${escHtml(costLabel)}</p>
    </div>
    <div class="kpis">
      ${kpiCard("Energy Cost", "₹" + fmt(costPerKwh, 4) + "/kWh", { icon: "₹", sub: `${archLabel} · ${costLabel}`, tip: tipPowerCost })}
      ${kpiCard("Annual energy bill", fmt(annualBillCr, 2) + " Cr", { icon: "Σ", sub: `${archLabel} · ${lfLabel}`, tip: tipAnnualBill })}
      ${kpiCard("Savings vs DISCOM", fmt(savingsCr, 2) + " Cr/yr", { icon: "↓", sub: `${archLabel} · vs 100% grid tariff`, tip: tipSavings })}
      ${kpiCard("NPV of savings", "₹" + fmt(npvCr, 2) + " Cr", { icon: "PV", sub: `${archLabel} · ${lfLabel}`, tip: tipNpv })}
      ${kpiCard("Hourly CFE min", (Number.isFinite(hourlyMin) ? fmt(hourlyMin, 1) : "—") + "%", { icon: "24", sub: `${archLabel} · ${hourlyPass ? "Pass" : "Fail"} · target ${fmt(hourlyTarget, 0)}%`, trend: hourlyPass ? "achieved" : "", tip: tipHourlyMin })}
    </div>
  </div>

  <div class="panel">
    <div class="card-head">
      <div>
        <div class="section-eyebrow">24×7 carbon-free · ${escHtml(archLabel)}</div>
        <h3 style="margin:0">Hourly CFE</h3>
      </div>
      ${statusPill(hourlyPass ? "Pass" : "Fail")}
    </div>
    <p class="muted" style="margin:0 0 0.75rem;font-size:0.82rem;line-height:1.45">
      ${escHtml(archLabel)} · ${escHtml(lfLabel)} · Min(Load, Solar+Wind+RE-BESS)/Load × 100 (TOD availability; solar ~0 at night).
    </p>
    <div class="kpis" style="margin:0">
      ${kpiCard("Min hour", (Number.isFinite(hourlyMin) ? fmt(hourlyMin, 1) : "—") + "%", { sub: `Target ${fmt(hourlyTarget, 0)}%`, tip: tipHourlyMin })}
      ${kpiCard("Mean hour", (Number.isFinite(hourlyMean) ? fmt(hourlyMean, 1) : "—") + "%", { sub: "Unweighted mean", tip: tipMeanHour })}
      ${kpiCard("Hours ≥ target", (Number.isFinite(hoursGe) ? fmt(hoursGe, 1) : "—") + "%", { sub: `Longest gap ${fmt(longestGap, 0)} h`, tip: tipHoursGe })}
      ${kpiCard("Max deficit", (Number.isFinite(maxDeficit) ? fmt(maxDeficit, 1) : "—") + " pp", { sub: "Largest shortfall vs target", tip: tipMaxDef })}
    </div>
    <div style="margin-top:0.85rem"><a class="btn sm secondary" href="#/hourly_cfe">Open Hourly CFE analysis</a></div>
  </div>

  <div class="grid two" style="margin-bottom:1rem">
    <div class="panel" style="margin:0">
      <div class="card-head"><h3 style="margin:0">Cost breakdown · ${escHtml(archLabel)}</h3><span class="pill muted">₹${fmt(costPerKwh,4)}/kWh · ${escHtml(lfLabel)}</span></div>
      <div id="chart-cost-donut" data-lf-scale="${lfScale}" data-cost-per-kwh="${costPerKwh}"></div>
    </div>
    <div class="panel" style="margin:0">
      <div class="card-head"><h3 style="margin:0">Power mix · ${escHtml(archLabel)}</h3><span class="pill muted">Architecture %</span></div>
      <div id="chart-mix-donut"></div>
    </div>
  </div>

'''

t = t[:start] + new_block + t[end:]

# Wire click handlers after data-set-arch block
old_arch = '''  if (state.page === "dashboard" || state.page === "hourly_cfe" || state.page === "economics") {
    document.querySelectorAll("[data-set-arch]").forEach((btn) => {
      btn.onclick = () => {
        state.detailArch = String(btn.getAttribute("data-set-arch") || "").toUpperCase();
        renderApp({ flushDom: false });
      };
    });
  }'''

new_arch = '''  if (state.page === "dashboard" || state.page === "hourly_cfe" || state.page === "economics") {
    document.querySelectorAll("[data-set-arch]").forEach((btn) => {
      btn.onclick = () => {
        state.detailArch = String(btn.getAttribute("data-set-arch") || "").toUpperCase();
        renderApp({ flushDom: false });
      };
    });
  }

  if (state.page === "dashboard") {
    document.querySelectorAll("[data-set-lf]").forEach((row) => {
      const pick = () => {
        state.selectedLfId = Number(row.getAttribute("data-set-lf"));
        renderApp({ flushDom: false });
      };
      row.onclick = pick;
      row.onkeydown = (ev) => {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          pick();
        }
      };
    });
  }'''

if old_arch not in t:
    raise SystemExit("arch handler block not found")
t = t.replace(old_arch, new_arch, 1)

# Scale cost donut by selected LF; prefer selected scenario breakdown when present
old_donut = '''  if (state.page === "dashboard") {
    const dashSim = simForArchitecture(activeDetailArchitecture()) || state.lastSim;
    if (dashSim) {
      const f = dashSim.financial || {};
      const xt = f.excel_tariff || {};
      const br = f.cost_breakdown || {};
      const costEl = document.getElementById("chart-cost-donut");
      if (costEl && Object.keys(br).length) {
        const costItemsRaw = PTOCharts.costBreakdownEntries(br);'''

new_donut = '''  if (state.page === "dashboard") {
    const dashSim = simForArchitecture(activeDetailArchitecture()) || state.lastSim;
    if (dashSim) {
      const f = dashSim.financial || {};
      const xt = f.excel_tariff || {};
      const lfRows = dashSim.lf_scenarios || f.lf_scenarios || [];
      const lfSel = lfRows.find((r) => Number(r.id) === Number(state.selectedLfId)) || lfRows[0] || null;
      const br = (lfSel && lfSel.cost_breakdown && Object.keys(lfSel.cost_breakdown).length)
        ? lfSel.cost_breakdown
        : (f.cost_breakdown || {});
      const costEl = document.getElementById("chart-cost-donut");
      const costCenter = Number(costEl?.getAttribute("data-cost-per-kwh") || lfSel?.cost_per_kwh || f.cost_per_kwh) || 0;
      if (costEl && Object.keys(br).length) {
        const costItemsRaw = PTOCharts.costBreakdownEntries(br);'''

if old_donut not in t:
    raise SystemExit("donut block start not found")
t = t.replace(old_donut, new_donut, 1)

t = t.replace(
    "centerValue: fmt(f.cost_per_kwh, 4),",
    "centerValue: fmt(costCenter, 4),",
    1,
)

# Reset selected LF on new analysis / clear detailArch reset nearby
if "state.detailArch = null;" in t and "state.selectedLfId = null;" not in t.split("state.detailArch = null;")[1][:80]:
    t = t.replace("state.detailArch = null;", "state.detailArch = null;\n  state.selectedLfId = null;", 1)

app.write_text(t, encoding="utf-8")
print("OK app.js patched")

# CSS
css = Path("frontend/dist/assets/styles.css")
c = css.read_text(encoding="utf-8")
if "tr.lf-row" not in c:
    c += """
tr.lf-row { cursor: pointer; }
tr.lf-row:hover td { background: rgba(26, 166, 160, 0.08); }
tr.selected-lf td {
  background: rgba(26, 166, 160, 0.12);
  box-shadow: inset 3px 0 0 #1aa6a0;
}
"""
    css.write_text(c, encoding="utf-8")
    print("OK css")
else:
    print("css already has lf-row")

# cache bust
idx = Path("frontend/dist/index.html")
h = idx.read_text(encoding="utf-8")
import re
h = re.sub(r"app\.js\?v=\d+", "app.js?v=153", h)
h = re.sub(r"charts\.js\?v=\d+", "charts.js?v=153", h)
h = re.sub(r"styles\.css\?v=\d+", "styles.css?v=153", h)
idx.write_text(h, encoding="utf-8")
print("v153")
