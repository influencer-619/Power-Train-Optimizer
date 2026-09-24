"""Remove plant-shape UI; firm Architecture charts only."""
from pathlib import Path

p = Path("frontend/dist/assets/app.js")
t = p.read_text(encoding="utf-8")

# Replace pageSimulation chart section from toolbar blurb through charts grid
import re

# Simpler: replace distinctive blocks
old_blurb = """        Study window: ${currentModelHours()} h.
        <b>CFE / contracted delivery</b> use Architecture mix % (firm).
        Solar/Wind MW traces are <b>illustrative profiles only</b> — not used for bill, RE, or Pass/Fail."""

new_blurb = """        Study window: ${currentModelHours()} h.
        All traces are <b>Architecture contracted mix</b> (firm every hour) — no plant generation shapes."""

if old_blurb not in t:
    raise SystemExit("blurb not found")
t = t.replace(old_blurb, new_blurb)

old_grid = """  <div class="grid two" style="margin-top:1rem">
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
  </div>"""

new_grid = """  <div class="grid two" style="margin-top:1rem">
    <div class="card">
      <h3 style="margin:0">Contracted · Load / Solar / Wind (+BESS)</h3>
      <p class="muted" style="margin:0.35rem 0 0.5rem;font-size:0.82rem">Firm Architecture delivery: each hour = Load × mix %. No plant diurnal shapes.</p>
      <div class="chart-box tall" id="c-lsw"></div>
    </div>
    <div class="card">
      <h3 style="margin:0">Contracted · Load / CF / DISCOM</h3>
      <p class="muted" style="margin:0.35rem 0 0.5rem;font-size:0.82rem">CF = Load×(Solar%+Wind%+BESS%); DISCOM = Load×DISCOM%. Firm every hour.</p>
      <div class="chart-box tall" id="c-bess"></div>
    </div>
    <div class="card" style="grid-column:1 / -1">
      <h3 style="margin:0">Hourly CFE · Architecture mix</h3>
      <p class="muted" style="margin:0.35rem 0 0.5rem;font-size:0.82rem">Firm Solar%+Wind%+BESS% every hour (Pass/Fail metric).</p>
      <div class="chart-box tall" id="c-cfe"></div>
    </div>
  </div>"""

if old_grid not in t:
    raise SystemExit("chart grid not found")
t = t.replace(old_grid, new_grid)

old_charts = """      if (series.series_note) {
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
      });"""

new_charts = """      if (series.series_note) {
        hintEl.textContent = (hintEl.textContent ? hintEl.textContent + " · " : "") + series.series_note;
      }
      PTOCharts.line(document.getElementById("c-lsw"), [
        { data: series.load_mw }, { data: series.solar_mw }, { data: series.wind_mw },
      ], { title: `Contracted Solar / Wind · ${windowLabel}`, labels: ["Load", "Solar (contract)", "Wind+BESS (contract)"], yLabel: "MW", height: 280,
        colors: ["#12251c", "#b08d57", "#2f6f8f"] });
      PTOCharts.line(document.getElementById("c-bess"), [
        { data: series.load_mw },
        { data: series.cf_supply_mw || [] },
        { data: series.grid_contract_mw || [] },
      ], { title: `Contracted CF / DISCOM · ${windowLabel}`, labels: ["Load", "CF (Architecture)", "DISCOM (Architecture)"], yLabel: "MW", height: 280,
        colors: ["#12251c", "#3f6b54", "#8b2e1f"] });
      const cfeEl = document.getElementById("c-cfe");
      if (cfeEl) {
        PTOCharts.line(cfeEl, [{ data: series.hourly_cfe_pct }], {
          title: `Architecture CFE · ${windowLabel}`,
          labels: ["Hourly CFE % (firm mix)"], yLabel: "CFE %", height: 280, colors: ["#1b3d2f"]
        });
      }"""

if old_charts not in t:
    raise SystemExit("chart bind not found")
t = t.replace(old_charts, new_charts)

t = t.replace(
    'hintEl.textContent = "Full-year overview (every 6th hour). Profiles = illustrative; CFE = Architecture mix.";',
    'hintEl.textContent = "Full-year overview (every 6th hour). All series = Architecture contracted mix (firm).";',
)

p.write_text(t, encoding="utf-8")

# series_note in backend already updated next
html = Path("frontend/dist/index.html")
h = html.read_text(encoding="utf-8")
for old in ("?v=139", "?v=138", "?v=137"):
    h = h.replace(old, "?v=140")
html.write_text(h, encoding="utf-8")
print("ui ok", "Illustrative profiles" not in t or t.count("Illustrative profiles") == 0)
print("plant balancer", "plant balancer" in t)
print("v140", "?v=140" in h)
