# -*- coding: utf-8 -*-
"""Wire selected LF scenario into compare table, Economics, and Hourly CFE pages."""
from pathlib import Path
import re

app = Path("frontend/dist/assets/app.js")
t = app.read_text(encoding="utf-8")

HELPERS = r'''
function lfRowsFor(sim) {
  if (!sim) return [];
  return sim.lf_scenarios || sim.financial?.lf_scenarios || [];
}

function selectedLfRow(sim) {
  const rows = lfRowsFor(sim);
  if (!rows.length) return null;
  const want = state.selectedLfId != null ? Number(state.selectedLfId) : Number(rows[0].id);
  return rows.find((r) => Number(r.id) === want) || rows[0];
}

function ensureSelectedLfId(sim) {
  const row = selectedLfRow(sim);
  if (row && state.selectedLfId == null) state.selectedLfId = row.id;
  return row;
}

/** Display metrics for the currently selected load-factor scenario (falls back to primary run). */
function lfMetrics(sim) {
  const f = sim?.financial || {};
  const xt = f.excel_tariff || {};
  const k = sim?.kpis || {};
  const ca = sim?.cfe_analytics || k.cfe_analytics || {};
  const carbon = f.carbon || {};
  const hc = sim?.compliance?.hourly_cfe || {};
  const lf = selectedLfRow(sim);
  return {
    lf,
    label: lf ? (lf.label || (`LF ${fmt(lf.load_factor_pct, 0)}%`)) : "Scenario 1",
    cost_per_kwh: Number(lf?.cost_per_kwh ?? f.cost_per_kwh) || 0,
    annual_bill_cr: Number(lf?.annual_bill_cr ?? lf?.annual_energy_cr ?? xt.annual_bill_cr ?? xt.annual_energy_cr) || 0,
    annual_energy_cr: Number(lf?.annual_energy_cr ?? xt.annual_energy_cr) || 0,
    savings_vs_discom_cr: Number(lf?.savings_vs_discom_cr ?? xt.savings_vs_discom_cr) || 0,
    npv_cr: Number(lf?.npv_cr ?? f.npv_cr) || 0,
    cfe_pct: Number(lf?.cfe_pct ?? xt.cfe_pct ?? carbon.cfe_pct ?? xt.re_pct ?? k.annual_re_pct) || 0,
    carbon_saved_tco2: Number(lf?.carbon_saved_tco2 ?? xt.carbon_saved_tco2 ?? carbon.carbon_saved_tco2) || 0,
    annual_load_mwh: Number(lf?.annual_load_mwh ?? xt.annual_load_mwh ?? carbon.annual_load_mwh ?? k.annual_load_mwh) || 0,
    blended_rate: Number(lf?.blended_rate_inr_per_kwh ?? xt.blended_rate_inr_per_kwh) || 0,
    discom_only_cr: Number(xt.discom_only_cr) || 0,
    hourly_cfe_min_pct: Number(lf?.hourly_cfe_min_pct ?? ca.min_hourly_cfe_pct ?? k.hourly_cfe_min_pct ?? hc.min_pct),
    hourly_cfe_mean_pct: Number(lf?.hourly_cfe_mean_pct ?? ca.mean_hourly_cfe_pct ?? k.hourly_cfe_mean_pct ?? hc.mean_pct),
    hours_meeting_cfe_target_pct: Number(lf?.hours_meeting_cfe_target_pct ?? ca.pct_hours_ge_target ?? k.hours_meeting_cfe_target_pct ?? hc.hours_meeting_pct),
    longest_continuous_deficit_hours: Number(lf?.longest_continuous_deficit_hours ?? ca.longest_continuous_deficit_hours),
    max_cfe_deficit_pp: Number(lf?.max_cfe_deficit_pp ?? ca.max_cfe_deficit_pp),
    hourly_cfe_passed: (lf?.hourly_cfe_passed === true || lf?.hourly_cfe_passed === false)
      ? !!lf.hourly_cfe_passed
      : (ca.passed === true || hc.status === "Pass"),
    cost_breakdown: (lf?.cost_breakdown && Object.keys(lf.cost_breakdown).length)
      ? lf.cost_breakdown
      : (f.cost_breakdown || {}),
  };
}

function lfScenarioPickerHtml(sim) {
  const rows = lfRowsFor(sim);
  if (!rows.length) return "";
  ensureSelectedLfId(sim);
  const sel = selectedLfRow(sim);
  return `<div class="lf-picker" style="margin:0.65rem 0 0.85rem">
    <div class="section-eyebrow">Load-factor scenario</div>
    <div class="tabs arch-detail-tabs" style="margin-top:0.4rem;flex-wrap:wrap">
      ${rows.map((r) => {
        const on = sel && Number(r.id) === Number(sel.id);
        return `<button type="button" class="tab ${on ? "active" : ""}" data-set-lf="${escHtml(String(r.id))}" aria-pressed="${on}">${escHtml(r.label || ("S" + r.id))}</button>`;
      }).join("")}
    </div>
    <p class="muted" style="margin:0.4rem 0 0;font-size:0.8rem">KPIs and compare tables follow this LF. Selected: <b>${escHtml(sel?.label || "")}</b>.</p>
  </div>`;
}

'''

anchor = "function simForArchitecture(key) {"
if "function lfMetrics(" in t:
    print("helpers already present — refreshing helpers block")
    # replace existing helpers if present
    start = t.find("function lfRowsFor(sim)")
    end = t.find("function architectureTabsHtml")
    if start > 0 and end > start:
        # find what to keep — actually insert before architectureTabsHtml
        pass
else:
    # insert after activeDetailArchitecture function
    mark = "function architectureTabsHtml(pageKey) {"
    if mark not in t:
        raise SystemExit("architectureTabsHtml not found")
    t = t.replace(mark, HELPERS + mark, 1)
    print("OK inserted helpers")

# If helpers were half-added, ensure lfMetrics exists
if "function lfMetrics(" not in t:
    mark = "function architectureTabsHtml(pageKey) {"
    t = t.replace(mark, HELPERS + mark, 1)
    print("OK re-inserted helpers")

# --- Side-by-side compare cells ---
old_rows = '''  const rows = [
    {
      label: "Energy Cost ₹/kWh",
      tip: "Captive/Hybrid: blended rate (Discom×G% + Solar×S% + Wind×W% + BESS×Storage%). DISCOM: DISCOM stack rate. Annual energy bill = this × load kWh.",
      cell: (a) => `₹${fmt(a.financial?.cost_per_kwh, 4)}`,
    },
    {
      label: "Annual bill ₹ Cr",
      tip: "Annual energy bill ₹ Cr = Energy Cost ₹/kWh × annual load kWh / 1e7. Demand/fixed shown separately.",
      cell: (a) => fmt((a.financial?.excel_tariff?.annual_bill_cr ?? a.financial?.excel_tariff?.annual_energy_cr ?? (a.financial?.total_annual_cost_inr || 0) / 1e7), 2),
    },
    {
      label: "Savings vs DISCOM ₹ Cr/yr",
      tip: "Year-1 (100% DISCOM bill − architecture bill) / 1e7. DISCOM column is 0 by definition.",
      cell: (a, k) => (k === "DISCOM" ? "—" : fmt(a.financial?.excel_tariff?.savings_vs_discom_cr ?? 0, 2)),
    },
    {
      label: "NPV of savings ₹ Cr",
      tip: "Present value of yearly savings vs DISCOM over project life. DISCOM NPV is baseline (typically 0).",
      cell: (a, k) => (k === "DISCOM" ? "—" : fmt(a.financial?.npv_cr, 2)),
    },
    {
      label: "RE mix %",
      tip: "Architecture RE share for the bill (Solar%+Wind%+BESS%). Hourly CFE uses TOD availability.",
      cell: (a, k) => {
        if (k === "DISCOM") return "0%*";
        const xt = a.financial?.excel_tariff || {};
        const pct = Number(xt.cfe_pct ?? xt.re_pct ?? a.kpis?.annual_re_pct) || 0;
        return `${fmt(pct, 1)}%`;
      },
    },
    {
      label: "Hourly CFE min %",
      tip: "Min hourly CFE from TOD availability (solar ~0 at night).",
      cell: (a, k) => (k === "DISCOM" ? "0%*" : `${fmt(a.kpis?.hourly_cfe_min_pct ?? a.cfe_analytics?.min_hourly_cfe_pct, 1)}%`),
    },
    {
      label: "Carbon saved tCO2",
      tip: "Baseline (100% DISCOM) − actual architecture emissions.",
      cell: (a, k) => {
        if (k === "DISCOM") return "—";
        const c = a.financial?.carbon || a.financial?.excel_tariff || {};
        return fmt(c.carbon_saved_tco2 ?? 0, 0);
      },
    },
  ];'''

new_rows = '''  const lfNote = (() => {
    const sample = arches.HYBRID || arches.CAPTIVE || Object.values(arches)[0];
    ensureSelectedLfId(sample);
    return selectedLfRow(sample)?.label || "Scenario 1";
  })();
  const rows = [
    {
      label: "Energy Cost ₹/kWh",
      tip: "Captive/Hybrid: blended rate (Discom×G% + Solar×S% + Wind×W% + BESS×Storage%). DISCOM: DISCOM stack rate. Annual energy bill = this × load kWh.",
      cell: (a) => `₹${fmt(lfMetrics(a).cost_per_kwh, 4)}`,
    },
    {
      label: "Annual bill ₹ Cr",
      tip: "Annual energy bill ₹ Cr = Energy Cost ₹/kWh × annual load kWh / 1e7. Demand/fixed shown separately.",
      cell: (a) => fmt(lfMetrics(a).annual_bill_cr, 2),
    },
    {
      label: "Savings vs DISCOM ₹ Cr/yr",
      tip: "Year-1 (100% DISCOM bill − architecture bill) / 1e7. DISCOM column is 0 by definition.",
      cell: (a, k) => (k === "DISCOM" ? "—" : fmt(lfMetrics(a).savings_vs_discom_cr, 2)),
    },
    {
      label: "NPV of savings ₹ Cr",
      tip: "Present value of yearly savings vs DISCOM over project life. DISCOM NPV is baseline (typically 0).",
      cell: (a, k) => (k === "DISCOM" ? "—" : fmt(lfMetrics(a).npv_cr, 2)),
    },
    {
      label: "RE mix %",
      tip: "Architecture RE share for the bill (Solar%+Wind%+BESS%). Hourly CFE uses TOD availability.",
      cell: (a, k) => (k === "DISCOM" ? "0%*" : `${fmt(lfMetrics(a).cfe_pct, 1)}%`),
    },
    {
      label: "Hourly CFE min %",
      tip: "Min hourly CFE from TOD availability (solar ~0 at night).",
      cell: (a, k) => (k === "DISCOM" ? "0%*" : `${fmt(lfMetrics(a).hourly_cfe_min_pct, 1)}%`),
    },
    {
      label: "Carbon saved tCO2",
      tip: "Baseline (100% DISCOM) − actual architecture emissions.",
      cell: (a, k) => (k === "DISCOM" ? "—" : fmtEnergy(lfMetrics(a).carbon_saved_tco2, 0)),
    },
  ];'''

if old_rows not in t:
    raise SystemExit("compare rows block not found")
t = t.replace(old_rows, new_rows, 1)
print("OK compare rows")

old_cmp_note = '''    <p class="muted" style="margin:0 0 0.75rem;font-size:0.82rem;line-height:1.45">
      This table compares both architectures from the same Run Analysis. Scroll down and use the <b>CAPTIVE</b> / <b>HYBRID</b> tabs for one architecture’s full detail.
    </p>'''
new_cmp_note = '''    <p class="muted" style="margin:0 0 0.75rem;font-size:0.82rem;line-height:1.45">
      Metrics for load-factor <b>${escHtml(lfNote)}</b> (change LF in the table below or on Economics / Hourly CFE). Scroll down for one architecture’s full detail.
    </p>'''
if old_cmp_note not in t:
    raise SystemExit("compare note not found")
t = t.replace(old_cmp_note, new_cmp_note, 1)
print("OK compare note")

# --- Economics compare ---
old_econ_rows = '''  const rows = [
    { label: "Energy Cost ₹/kWh", tip: "Captive/Hybrid: blended rate (Discom×G% + Solar×S% + Wind×W% + BESS×Storage%). DISCOM: DISCOM stack rate. Annual energy bill = this × load kWh.", cell: (a) => `₹${fmt(a.financial?.cost_per_kwh, 4)}` },
    { label: "Annual bill ₹ Cr", tip: "Annual energy bill ₹ Cr = Energy Cost ₹/kWh × annual load kWh / 1e7. Demand/fixed shown separately.", cell: (a) => fmt((a.financial?.excel_tariff?.annual_bill_cr ?? a.financial?.excel_tariff?.annual_energy_cr ?? (a.financial?.total_annual_cost_inr || 0) / 1e7), 2) },
    { label: "Savings vs DISCOM ₹ Cr/yr", tip: "Year-1 bill savings vs 100% DISCOM baseline.", cell: (a) => fmt(a.financial?.excel_tariff?.savings_vs_discom_cr ?? 0, 2) },
    { label: "NPV of savings ₹ Cr", tip: "Discounted lifetime savings vs DISCOM.", cell: (a) => fmt(a.financial?.npv_cr, 2) },
    { label: "Blended ₹/kWh", tip: "Discom×G% + Solar×S% + Wind×W% + BESS×Storage tariff.", cell: (a) => `₹${fmt(a.financial?.excel_tariff?.blended_rate_inr_per_kwh, 4)}` },
    { label: "Mix G|S|W|B %", tip: "Architecture percentage of power.", cell: (a) => {
      const xt = a.financial?.excel_tariff || {};
      return `${fmt(xt.grid_pct, 0)}|${fmt(xt.solar_pct, 0)}|${fmt(xt.wind_pct, 0)}|${fmt(xt.bess_pct, 0)}`;
    } },
  ];'''

new_econ_rows = '''  const rows = [
    { label: "Energy Cost ₹/kWh", tip: "Captive/Hybrid: blended rate. DISCOM: DISCOM stack rate.", cell: (a) => `₹${fmt(lfMetrics(a).cost_per_kwh, 4)}` },
    { label: "Annual bill ₹ Cr", tip: "Annual energy bill for the selected LF scenario.", cell: (a) => fmt(lfMetrics(a).annual_bill_cr, 2) },
    { label: "Savings vs DISCOM ₹ Cr/yr", tip: "Year-1 bill savings vs 100% DISCOM baseline.", cell: (a) => fmt(lfMetrics(a).savings_vs_discom_cr, 2) },
    { label: "NPV of savings ₹ Cr", tip: "Discounted lifetime savings vs DISCOM.", cell: (a) => fmt(lfMetrics(a).npv_cr, 2) },
    { label: "Blended ₹/kWh", tip: "Discom×G% + Solar×S% + Wind×W% + BESS×Storage tariff.", cell: (a) => `₹${fmt(lfMetrics(a).blended_rate || a.financial?.excel_tariff?.blended_rate_inr_per_kwh, 4)}` },
    { label: "Mix G|S|W|B %", tip: "Architecture percentage of power.", cell: (a) => {
      const xt = a.financial?.excel_tariff || {};
      return `${fmt(xt.grid_pct, 0)}|${fmt(xt.solar_pct, 0)}|${fmt(xt.wind_pct, 0)}|${fmt(xt.bess_pct, 0)}`;
    } },
  ];'''

if old_econ_rows not in t:
    raise SystemExit("econ compare rows not found")
t = t.replace(old_econ_rows, new_econ_rows, 1)
print("OK econ compare")

# --- Hourly CFE compare ---
old_cfe_rows = '''  const rows = [
    { label: "Annual CFE %", tip: "sum Min(Load, CF supply) / sum Load × 100.", cell: (a) => {
      const ca = a.cfe_analytics || a.kpis?.cfe_analytics || {};
      return `${fmt(ca.annual_cfe_pct ?? a.kpis?.annual_cfe_pct, 1)}%`;
    } },
    { label: "Min hourly CFE %", tip: "Minimum hourly CFE from TOD availability (Solar+Wind+RE-BESS). Night solar ≈ 0.", cell: (a) => {
      const ca = a.cfe_analytics || {};
      const hc = a.compliance?.hourly_cfe || {};
      return `${fmt(ca.min_hourly_cfe_pct ?? a.kpis?.hourly_cfe_min_pct ?? hc.min_pct, 1)}%`;
    } },
    { label: "Mean hourly CFE %", tip: "Unweighted mean of hourly CFE %.", cell: (a) => {
      const ca = a.cfe_analytics || {};
      const hc = a.compliance?.hourly_cfe || {};
      return `${fmt(ca.mean_hourly_cfe_pct ?? a.kpis?.hourly_cfe_mean_pct ?? hc.mean_pct, 1)}%`;
    } },
    { label: "Hours ≥ target %", tip: "Share of study hours meeting hourly CFE target.", cell: (a) => {
      const ca = a.cfe_analytics || {};
      const hc = a.compliance?.hourly_cfe || {};
      return `${fmt(ca.pct_hours_ge_target ?? a.kpis?.hours_meeting_cfe_target_pct ?? hc.hours_meeting_pct, 1)}%`;
    } },
    { label: "Longest deficit h", tip: "Longest continuous streak below target.", cell: (a) => fmt((a.cfe_analytics || {}).longest_continuous_deficit_hours, 0) },
    { label: "Pass / Fail", tip: "Vs hourly CFE target and pass mode.", cell: (a) => {
      const ca = a.cfe_analytics || {};
      const hc = a.compliance?.hourly_cfe || {};
      const pass = ca.passed === true || hc.status === "Pass";
      return statusPill(pass ? "Pass" : "Fail");
    } },
  ];'''

new_cfe_rows = '''  const rows = [
    { label: "Annual CFE / RE mix %", tip: "Architecture RE mix for the bill (selected LF).", cell: (a) => `${fmt(lfMetrics(a).cfe_pct, 1)}%` },
    { label: "Min hourly CFE %", tip: "Minimum hourly CFE from TOD availability (Solar+Wind+RE-BESS). Night solar ≈ 0.", cell: (a) => `${fmt(lfMetrics(a).hourly_cfe_min_pct, 1)}%` },
    { label: "Mean hourly CFE %", tip: "Unweighted mean of hourly CFE %.", cell: (a) => `${fmt(lfMetrics(a).hourly_cfe_mean_pct, 1)}%` },
    { label: "Hours ≥ target %", tip: "Share of study hours meeting hourly CFE target.", cell: (a) => `${fmt(lfMetrics(a).hours_meeting_cfe_target_pct, 1)}%` },
    { label: "Longest deficit h", tip: "Longest continuous streak below target.", cell: (a) => fmt(lfMetrics(a).longest_continuous_deficit_hours, 0) },
    { label: "Pass / Fail", tip: "Vs hourly CFE target and pass mode.", cell: (a) => statusPill(lfMetrics(a).hourly_cfe_passed ? "Pass" : "Fail") },
  ];'''

if old_cfe_rows not in t:
    raise SystemExit("cfe compare rows not found")
t = t.replace(old_cfe_rows, new_cfe_rows, 1)
print("OK cfe compare")

# --- pageEconomics KPIs ---
old_econ_kpis = '''  return `
  ${compareBlock}
  ${architectureTabsHtml("economics")}
  <div class="grid kpis">
    ${kpiCard("Energy Cost ₹/kWh", "₹"+fmt(f.cost_per_kwh,4), { sub: `${archKey} · ${f.cost_metric_label || "ENERGY COST"}`, tip: "Captive/Hybrid: blended rate. DISCOM: DISCOM stack rate. Annual energy bill = Energy Cost × load kWh." })}
    ${kpiCard("Annual energy bill", xt ? fmt(xt.annual_bill_cr ?? xt.annual_energy_cr, 2) + " ₹ Cr" : money(f.total_annual_cost_inr), { tip: "Annual energy bill ₹ Cr = Energy Cost × load kWh / 1e7. Demand/fixed are separate." })}
    ${kpiCard("Savings vs DISCOM", xt ? fmt(xt.savings_vs_discom_cr, 2) + " ₹ Cr/yr" : "-", { tip: "Year-1 savings vs 100% DISCOM baseline." })}
    ${kpiCard("NPV of savings", "₹"+fmt(f.npv_cr,2)+" Cr", { sub: "vs 100% DISCOM power bill", tip: "Discounted lifetime savings vs DISCOM for this architecture." })}
  </div>'''

new_econ_kpis = '''  const m = lfMetrics(s);
  return `
  ${compareBlock}
  ${architectureTabsHtml("economics")}
  ${lfScenarioPickerHtml(s)}
  <div class="grid kpis">
    ${kpiCard("Energy Cost ₹/kWh", "₹"+fmt(m.cost_per_kwh,4), { sub: `${archKey} · ${m.label} · ${f.cost_metric_label || "ENERGY COST"}`, tip: "Captive/Hybrid: blended rate. DISCOM: DISCOM stack rate. Annual energy bill = Energy Cost × load kWh." })}
    ${kpiCard("Annual energy bill", fmt(m.annual_bill_cr, 2) + " ₹ Cr", { sub: `${archKey} · ${m.label}`, tip: "Annual energy bill ₹ Cr = Energy Cost × load kWh / 1e7. Demand/fixed are separate." })}
    ${kpiCard("Savings vs DISCOM", fmt(m.savings_vs_discom_cr, 2) + " ₹ Cr/yr", { tip: "Year-1 savings vs 100% DISCOM baseline." })}
    ${kpiCard("NPV of savings", "₹"+fmt(m.npv_cr,2)+" Cr", { sub: `${m.label} · vs 100% DISCOM`, tip: "Discounted lifetime savings vs DISCOM for this architecture." })}
  </div>'''

if old_econ_kpis not in t:
    raise SystemExit("econ kpis block not found")
t = t.replace(old_econ_kpis, new_econ_kpis, 1)
print("OK econ kpis")

# Update excel block annual charges / savings to use m
t = t.replace(
    "<tr><td>Total energy charges</td><td class=\"mono\">${fmt(xt.annual_energy_cr, 2)} ₹ Cr/year</td></tr>\n"
    "            <tr><td>Total energy charges (Discom only)</td><td class=\"mono\">${fmt(xt.discom_only_cr, 2)} ₹ Cr/year</td></tr>\n"
    "            <tr><td>Savings</td><td class=\"mono\"><b>${fmt(xt.savings_vs_discom_cr, 2)} ₹ Cr/year</b></td></tr>",
    "<tr><td>Total energy charges</td><td class=\"mono\">${fmt(m.annual_energy_cr, 2)} ₹ Cr/year · ${escHtml(m.label)}</td></tr>\n"
    "            <tr><td>Total energy charges (Discom only)</td><td class=\"mono\">${fmt(xt.discom_only_cr, 2)} ₹ Cr/year</td></tr>\n"
    "            <tr><td>Savings</td><td class=\"mono\"><b>${fmt(m.savings_vs_discom_cr, 2)} ₹ Cr/year</b></td></tr>",
    1,
)
print("OK econ excel charges")

# Cost breakdown on economics — use m.cost_breakdown
t = t.replace(
    "${(PTOCharts.costBreakdownEntries(f.cost_breakdown) || []).map(([k,v]) => {",
    "${(PTOCharts.costBreakdownEntries(m.cost_breakdown) || []).map(([k,v]) => {",
    1,
)
print("OK econ breakdown")

# --- pageHourlyCfe detail KPIs ---
old_hourly_head = '''  const mixCfe = Number(s.financial?.excel_tariff?.cfe_pct ?? s.financial?.carbon?.cfe_pct ?? s.financial?.excel_tariff?.re_pct);
  const formula = ca.formula || k.cfe_formula ||
    "Hourly CFE% = Min(Hourly Load, Hourly Carbon-Free Supply) / Hourly Load x 100. Carbon-Free Supply = Solar_available + Wind_available + RE-origin BESS discharge (TOD/availability; solar ~0 at night)";
  const hodRows = perf.hourly_of_day || [];
  const dailyRows = perf.daily || [];
  const monthlyRows = perf.monthly || [];
  return `
  ${s.results_stale ? `<div class="banner danger">⚠ STALE RESULTS - inputs changed after this run. Click <b>Run Analysis</b> again.</div>` : ""}
  ${compareBlock}
  ${architectureTabsHtml("hourly_cfe")}
  <div class="card" style="margin-bottom:0.85rem">
    <div class="card-head">
      <h3 style="margin:0">24x7 Carbon-Free Energy (CFE) — ${escHtml(archKey)}</h3>
      ${statusPill(passed ? "Pass" : "Fail")}
    </div>'''

new_hourly_head = '''  const m = lfMetrics(s);
  const mixCfe = Number(m.cfe_pct);
  const passedLf = m.hourly_cfe_passed;
  const formula = ca.formula || k.cfe_formula ||
    "Hourly CFE% = Min(Hourly Load, Hourly Carbon-Free Supply) / Hourly Load x 100. Carbon-Free Supply = Solar_available + Wind_available + RE-origin BESS discharge (TOD/availability; solar ~0 at night)";
  const hodRows = perf.hourly_of_day || [];
  const dailyRows = perf.daily || [];
  const monthlyRows = perf.monthly || [];
  return `
  ${s.results_stale ? `<div class="banner danger">⚠ STALE RESULTS - inputs changed after this run. Click <b>Run Analysis</b> again.</div>` : ""}
  ${compareBlock}
  ${architectureTabsHtml("hourly_cfe")}
  ${lfScenarioPickerHtml(s)}
  <div class="card" style="margin-bottom:0.85rem">
    <div class="card-head">
      <h3 style="margin:0">24x7 Carbon-Free Energy (CFE) — ${escHtml(archKey)} · ${escHtml(m.label)}</h3>
      ${statusPill(passedLf ? "Pass" : "Fail")}
    </div>'''

if old_hourly_head not in t:
    raise SystemExit("hourly head not found")
t = t.replace(old_hourly_head, new_hourly_head, 1)
print("OK hourly head")

# Replace first KPI block on hourly page to use m for min/mean/hours
old_hourly_kpis = '''  <div class="kpis">
    ${kpiCard("Annual CFE", fmt(ca.annual_cfe_pct ?? annual.cfe_pct ?? k.annual_cfe_pct, 1) + "%", { sub: ca.annual_cfe_definition || "sum Min(Load, CF supply) / sum Load", tip: "Energy-weighted annual CFE for this architecture." })}
    ${kpiCard("Min hourly CFE", fmt(ca.min_hourly_cfe_pct ?? k.hourly_cfe_min_pct ?? hc.min_pct, 1) + "%", { sub: "Lowest hour in study", tip: "Lowest hour: Min(Load, Solar+Wind+RE-BESS available) ÷ Load. Night with no solar and little wind/BESS can be 0% — not the flat RE mix %." })}
    ${kpiCard("Mean hourly CFE", fmt(ca.mean_hourly_cfe_pct ?? k.hourly_cfe_mean_pct ?? hc.mean_pct, 1) + "%", { sub: "Unweighted mean", tip: "Unweighted mean of hourly CFE %." })}
    ${kpiCard("Median / P95", fmt(ca.median_hourly_cfe_pct ?? k.hourly_cfe_median_pct, 1) + "% / " + fmt(ca.p95_hourly_cfe_pct ?? k.hourly_cfe_p95_pct, 1) + "%", { sub: "Distribution" })}
    ${kpiCard("Hours >= target", fmt(ca.pct_hours_ge_target ?? k.hours_meeting_cfe_target_pct ?? hc.hours_meeting_pct, 1) + "%", { sub: `${fmt(ca.hours_ge_target ?? k.hours_meeting_cfe_target, 0)} of ${fmt(ca.hours_total ?? currentModelHours(), 0)} h` })}
    ${kpiCard("Longest deficit", fmt(ca.longest_continuous_deficit_hours, 0) + " h", { sub: "Continuous hours below target" })}
    ${kpiCard("Max / mean deficit", fmt(ca.max_cfe_deficit_pp, 1) + " / " + fmt(ca.mean_cfe_deficit_pp, 1) + " pp", { sub: "Shortfall vs target" })}
    ${kpiCard("Pass actual", fmt(ca.actual_for_pass_mode_pct ?? hc.actual_pct, 1) + "%", { sub: escHtml(mode) })}
  </div>'''

new_hourly_kpis = '''  <div class="kpis">
    ${kpiCard("RE mix / CFE %", fmt(m.cfe_pct, 1) + "%", { sub: `${m.label} · Architecture mix`, tip: "Architecture RE mix for the bill at this LF." })}
    ${kpiCard("Min hourly CFE", fmt(m.hourly_cfe_min_pct, 1) + "%", { sub: `${m.label} · Lowest hour`, tip: "Lowest hour: Min(Load, Solar+Wind+RE-BESS available) ÷ Load. Night with no solar and little wind/BESS can be 0%." })}
    ${kpiCard("Mean hourly CFE", fmt(m.hourly_cfe_mean_pct, 1) + "%", { sub: `${m.label} · Unweighted mean`, tip: "Unweighted mean of hourly CFE %." })}
    ${kpiCard("Median / P95", fmt(ca.median_hourly_cfe_pct ?? k.hourly_cfe_median_pct, 1) + "% / " + fmt(ca.p95_hourly_cfe_pct ?? k.hourly_cfe_p95_pct, 1) + "%", { sub: "Distribution (scenario 1 series)" })}
    ${kpiCard("Hours >= target", fmt(m.hours_meeting_cfe_target_pct, 1) + "%", { sub: `${m.label}` })}
    ${kpiCard("Longest deficit", fmt(m.longest_continuous_deficit_hours, 0) + " h", { sub: "Continuous hours below target" })}
    ${kpiCard("Max deficit", fmt(m.max_cfe_deficit_pp, 1) + " pp", { sub: "Largest shortfall vs target" })}
    ${kpiCard("Pass / Fail", passedLf ? "Pass" : "Fail", { sub: `${m.label} · ${escHtml(mode)}` })}
  </div>
  <p class="muted" style="margin:0.5rem 0 0;font-size:0.8rem">Headline KPIs follow the selected LF. Heatmap / duration charts use the primary scenario hourly series (shape is the same; scale follows LF).</p>'''

if old_hourly_kpis not in t:
    raise SystemExit("hourly kpis not found")
t = t.replace(old_hourly_kpis, new_hourly_kpis, 1)
print("OK hourly kpis")

# Extend LF click handler to economics + hourly_cfe
old_lf_handler = '''  if (state.page === "dashboard") {
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

new_lf_handler = '''  if (state.page === "dashboard" || state.page === "economics" || state.page === "hourly_cfe") {
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

if old_lf_handler not in t:
    raise SystemExit("lf handler not found")
t = t.replace(old_lf_handler, new_lf_handler, 1)
print("OK lf handler pages")

# Economics chart paint — use selected LF breakdown
old_econ_chart = '''  if (state.page === "economics" && (simForArchitecture(activeDetailArchitecture()) || state.lastSim)) {
    const s = simForArchitecture(activeDetailArchitecture()) || state.lastSim;
    const f = s.financial;'''

# find and patch cost chart to use lfMetrics
if old_econ_chart in t:
    t = t.replace(
        old_econ_chart,
        '''  if (state.page === "economics" && (simForArchitecture(activeDetailArchitecture()) || state.lastSim)) {
    const s = simForArchitecture(activeDetailArchitecture()) || state.lastSim;
    const mEcon = lfMetrics(s);
    const f = { ...s.financial, cost_breakdown: mEcon.cost_breakdown, cost_per_kwh: mEcon.cost_per_kwh };''',
        1,
    )
    print("OK econ chart metrics")
else:
    print("WARN econ chart block not found")

app.write_text(t, encoding="utf-8")

# cache
idx = Path("frontend/dist/index.html")
h = idx.read_text(encoding="utf-8")
h = re.sub(r"app\.js\?v=\d+", "app.js?v=155", h)
h = re.sub(r"charts\.js\?v=\d+", "charts.js?v=155", h)
h = re.sub(r"styles\.css\?v=\d+", "styles.css?v=155", h)
idx.write_text(h, encoding="utf-8")
print("v155")

# brace check
import subprocess
subprocess.check_call(["python", "scripts/_check_js_braces.py"])
print("braces OK")
