"""Label/cleanup UI copy for Architecture vs illustrative profiles."""
from pathlib import Path

p = Path("frontend/dist/assets/app.js")
t = p.read_text(encoding="utf-8")

old_page = '''function pageSimulation() {
  const monthOpts = MONTH_NAMES.map((n, i) => `<option value="${i + 1}">${n}</option>`).join("");
  return `
  <div class="card series-toolbar">
    <div class="series-toolbar-head">
      <h3 style="margin:0">Hourly charts</h3>
      <p class="muted" style="margin:0.25rem 0 0;font-size:0.9rem">Pick a time window, then show the hourly dispatch for that period (${currentModelHours()} h study).</p>
    </div>
    <div class="row series-controls" style="margin-top:0.85rem">
      <label class="series-field">Time window
        <select id="series-view">
          <option value="year">Full year (overview)</option>
          <option value="month">One month</option>
          <option value="week">One week</option>
          <option value="day">One day (24 hours)</option>
        </select>
      </label>
      <label class="series-field" id="wrap-series-month" hidden>Month
        <select id="series-month">${monthOpts}</select>
      </label>
      <label class="series-field" id="wrap-series-dom" hidden>Day of month
        <input id="series-dom" type="number" min="1" max="31" value="29" style="width:4.5rem">
      </label>
      <button class="btn" id="btn-load-series">Show charts</button>
    </div>
    <p class="muted" id="series-hint" style="margin:0.65rem 0 0;font-size:0.88rem;line-height:1.45"></p>
  </div>
  <div class="grid two" style="margin-top:1rem">
    <div class="card"><h3>Load / Solar / Wind</h3><div class="chart-box tall" id="c-lsw"></div></div>
    <div class="card"><h3>BESS Charge / Discharge / SOC</h3><div class="chart-box tall" id="c-bess"></div></div>
    <div class="card"><h3>Grid / Curtailment</h3><div class="chart-box tall" id="c-grid"></div></div>
    <div class="card"><h3>Hourly CFE</h3><div class="chart-box tall" id="c-cfe"></div></div>
  </div>
  ${state.lastSim ? `<div class="card" style="margin-top:1rem"><h3>Monthly Energy Balance</h3>
    <div class="table-wrap"><table><thead><tr>${Object.keys(state.lastSim.monthly[0]).map(k=>`<th>${k}</th>`).join("")}</tr></thead>
    <tbody>${state.lastSim.monthly.map(r=>`<tr>${Object.values(r).map(v=>`<td>${typeof v==='number'?fmt(v,2):v}</td>`).join("")}</tr>`).join("")}</tbody></table></div>
  </div>` : ""}`;
}'''

new_page = '''function pageSimulation() {
  const monthOpts = MONTH_NAMES.map((n, i) => `<option value="${i + 1}">${n}</option>`).join("");
  const monthlyCols = ["month", "load_mwh", "re_pct", "cfe_mean_pct"];
  const monthlyHead = monthlyCols.map((k) => {
    const label = ({ month: "Month", load_mwh: "Load MWh", re_pct: "Architecture RE %", cfe_mean_pct: "CFE mean %" })[k] || k;
    return `<th>${label}</th>`;
  }).join("");
  const monthlyBody = state.lastSim
    ? state.lastSim.monthly.map((r) =>
        `<tr>${monthlyCols.map((k) => {
          const v = r[k];
          return `<td>${typeof v === "number" ? fmt(v, 2) : (v ?? "—")}</td>`;
        }).join("")}</tr>`
      ).join("")
    : "";
  return `
  <div class="card series-toolbar">
    <div class="series-toolbar-head">
      <h3 style="margin:0">Hourly charts</h3>
      <p class="muted" style="margin:0.25rem 0 0;font-size:0.9rem">
        Study window: ${currentModelHours()} h.
        <b>CFE / contracted delivery</b> use Architecture mix % (firm).
        Solar/Wind MW traces are <b>illustrative profiles only</b> — not used for bill, RE, or Pass/Fail.
      </p>
    </div>
    <div class="row series-controls" style="margin-top:0.85rem">
      <label class="series-field">Time window
        <select id="series-view">
          <option value="year">Full year (overview)</option>
          <option value="month">One month</option>
          <option value="week">One week</option>
          <option value="day">One day (24 hours)</option>
        </select>
      </label>
      <label class="series-field" id="wrap-series-month" hidden>Month
        <select id="series-month">${monthOpts}</select>
      </label>
      <label class="series-field" id="wrap-series-dom" hidden>Day of month
        <input id="series-dom" type="number" min="1" max="31" value="29" style="width:4.5rem">
      </label>
      <button class="btn" id="btn-load-series">Show charts</button>
    </div>
    <p class="muted" id="series-hint" style="margin:0.65rem 0 0;font-size:0.88rem;line-height:1.45"></p>
  </div>
  <div class="grid two" style="margin-top:1rem">
    <div class="card">
      <h3 style="margin:0">Illustrative profiles · Load / Solar / Wind</h3>
      <p class="muted" style="margin:0.35rem 0 0.5rem;font-size:0.82rem">Generation shapes for context only (solar may be 0 at night). Not contracted delivery.</p>
      <div class="chart-box tall" id="c-lsw"></div>
    </div>
    <div class="card">
      <h3 style="margin:0">Contracted delivery · Load / CF / DISCOM</h3>
      <p class="muted" style="margin:0.35rem 0 0.5rem;font-size:0.82rem">Architecture mix: CF = Load×(Solar%+Wind%+BESS%); DISCOM = remainder. Firm every hour.</p>
      <div class="chart-box tall" id="c-bess"></div>
    </div>
    <div class="card">
      <h3 style="margin:0">Illustrative · profile grid / curtailment</h3>
      <p class="muted" style="margin:0.35rem 0 0.5rem;font-size:0.82rem">Plant-balancer diagnostic only — not used for bill or feasibility on the buyer path.</p>
      <div class="chart-box tall" id="c-grid"></div>
    </div>
    <div class="card">
      <h3 style="margin:0">Hourly CFE · Architecture mix</h3>
      <p class="muted" style="margin:0.35rem 0 0.5rem;font-size:0.82rem">Firm Solar%+Wind%+BESS% every hour (Pass/Fail metric).</p>
      <div class="chart-box tall" id="c-cfe"></div>
    </div>
  </div>
  ${state.lastSim ? `<div class="card" style="margin-top:1rem">
    <h3 style="margin:0">Monthly summary (Architecture)</h3>
    <p class="muted" style="margin:0.35rem 0 0.65rem;font-size:0.85rem">RE % and CFE are Architecture mix — flat across months when mix does not change.</p>
    <div class="table-wrap"><table><thead><tr>${monthlyHead}</tr></thead>
    <tbody>${monthlyBody}</tbody></table></div>
  </div>` : ""}`;
}'''

if old_page not in t:
    raise SystemExit("pageSimulation block not found")
t = t.replace(old_page, new_page)

old_charts = '''      PTOCharts.line(document.getElementById("c-lsw"), [
        { data: series.load_mw }, { data: series.solar_mw }, { data: series.wind_mw },
      ], { title: `Load / Solar / Wind - ${windowLabel}`, labels: ["Load", "Solar", "Wind"], yLabel: "MW", height: 280,
        colors: ["#12251c", "#b08d57", "#2f6f8f"] });
      PTOCharts.line(document.getElementById("c-bess"), [
        { data: series.charge_mw }, { data: series.discharge_mw }, { data: series.soc_mwh },
      ], { labels: ["Charge MW", "Discharge MW", "SOC MWh"], yLabel: "MW / MWh", height: 280,
        colors: ["#3f6b54", "#8b2e1f", "#b08d57"] });
      PTOCharts.line(document.getElementById("c-grid"), [
        { data: series.grid_mw }, { data: series.curtailment_mw },
      ], { labels: ["Grid import", "Curtailment"], yLabel: "MW", height: 280,
        colors: ["#1b3d2f", "#b08d57"] });
      PTOCharts.line(document.getElementById("c-cfe"), [{ data: series.hourly_cfe_pct }], {
        labels: ["Hourly CFE %"], yLabel: "CFE %", height: 280, colors: ["#1b3d2f"]
      });'''

new_charts = '''      if (series.series_note) {
        hintEl.textContent = (hintEl.textContent ? hintEl.textContent + " · " : "") + series.series_note;
      }
      PTOCharts.line(document.getElementById("c-lsw"), [
        { data: series.load_mw }, { data: series.solar_mw }, { data: series.wind_mw },
      ], { title: `Illustrative profiles · ${windowLabel}`, labels: ["Load", "Solar (profile)", "Wind (profile)"], yLabel: "MW", height: 280,
        colors: ["#12251c", "#b08d57", "#2f6f8f"] });
      PTOCharts.line(document.getElementById("c-bess"), [
        { data: series.load_mw },
        { data: series.cf_supply_mw || [] },
        { data: series.grid_contract_mw || [] },
      ], { title: `Contracted delivery · ${windowLabel}`, labels: ["Load", "CF (Architecture)", "DISCOM (Architecture)"], yLabel: "MW", height: 280,
        colors: ["#12251c", "#3f6b54", "#8b2e1f"] });
      PTOCharts.line(document.getElementById("c-grid"), [
        { data: series.grid_mw }, { data: series.curtailment_mw },
      ], { title: `Illustrative plant balancer · ${windowLabel}`, labels: ["Profile grid import", "Profile curtailment"], yLabel: "MW", height: 280,
        colors: ["#1b3d2f", "#b08d57"] });
      PTOCharts.line(document.getElementById("c-cfe"), [{ data: series.hourly_cfe_pct }], {
        title: `Architecture CFE · ${windowLabel}`,
        labels: ["Hourly CFE % (firm mix)"], yLabel: "CFE %", height: 280, colors: ["#1b3d2f"]
      });'''

if old_charts not in t:
    raise SystemExit("chart bind block not found")
t = t.replace(old_charts, new_charts)

old_cmp = '''          ${["solar_mw","wind_mw","bess_mw","bess_mwh","grid_mw","annual_re_pct","hourly_cfe_min_pct","grid_gwh","curtailment_pct","bess_utilization_pct"].map((m) =>
            `<tr><td>${m}</td>${keys.map((k) => `<td class="mono">${fmt(arches[k].kpis[m],2)}</td>`).join("")}</tr>`).join("")}'''

new_cmp = '''          ${[
            ["simulated_mix_grid_pct", "DISCOM mix %"],
            ["simulated_mix_solar_pct", "Solar mix %"],
            ["simulated_mix_wind_pct", "Wind mix %"],
            ["simulated_mix_bess_pct", "BESS mix %"],
            ["annual_re_pct", "Architecture RE %"],
            ["hourly_cfe_min_pct", "Hourly CFE min %"],
          ].map(([m, label]) =>
            `<tr><td>${label}</td>${keys.map((k) => `<td class="mono">${fmt(arches[k].kpis[m],2)}</td>`).join("")}</tr>`).join("")}'''

if old_cmp not in t:
    raise SystemExit("compare metrics block not found")
t = t.replace(old_cmp, new_cmp)

# Hints that still say plant dispatch for series toolbar default
t = t.replace(
    'hintEl.textContent = "Shows the full year as an overview (every 6th hour). No month or day needed.";',
    'hintEl.textContent = "Full-year overview (every 6th hour). Profiles = illustrative; CFE = Architecture mix.";',
)

p.write_text(t, encoding="utf-8")

html = Path("frontend/dist/index.html")
h = html.read_text(encoding="utf-8")
for old in ("?v=138", "?v=137", "?v=136", "?v=135"):
    h = h.replace(old, "?v=139")
html.write_text(h, encoding="utf-8")
print("ok", "?v=139" in h)
print("pageSimulation", "Illustrative profiles" in t)
print("firm chart", "CF (Architecture)" in t)
print("compare", "Architecture RE %" in t)
