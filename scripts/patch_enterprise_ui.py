"""Patch frontend app.js for enterprise dashboard."""
from __future__ import annotations

import re
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "frontend" / "dist" / "assets" / "app.js"
text = path.read_text(encoding="utf-8")

shell_new = r'''function shell(content) {
  const p = state.project;
  const structure = (p.config?.commercial?.structure?.value || "HYBRID").replaceAll("_", " ");
  const year = p.config?.general?.calendar_year?.value || 2026;
  const collapsed = !!state.sidebarCollapsed;
  return `
  <div class="shell ${collapsed ? "collapsed" : ""}">
    <aside class="sidebar">
      <div class="logo">
        <div class="logo-mark">⚡</div>
        <div class="logo-text"><strong>PowerTrain</strong><span>Optimizer</span></div>
      </div>
      <div class="nav">
        ${NAV_GROUPS.map((g) => `
          <div class="nav-group">${g.title}</div>
          ${g.items.map(([id, label, ico]) => {
            const href = id === "start" ? "#/start" : `#/${id}`;
            const active = state.page === id ? "active" : "";
            return `<a href="${href}" class="${active}"><span class="nav-ico">${ico}</span><span>${label}</span></a>`;
          }).join("")}
        `).join("")}
      </div>
      <div class="side-foot">
        <div class="side-foot-meta">Model ${p.model_version || "1.0.0"}</div>
        <div class="side-foot-meta db-ok"><span class="dot"></span>Database Connected</div>
        <button class="btn ghost sm" id="btn-collapse" style="margin-top:0.6rem;width:100%;justify-content:center;background:transparent;color:#c5d9ce;border-color:rgba(255,255,255,0.15)">${collapsed ? "»" : "Collapse"}</button>
      </div>
    </aside>
    <main class="main">
      <div class="app-topbar">
        <div class="top-left">
          <div>
            <div class="eyebrow" style="margin:0">Project</div>
            <h1>${p.name}</h1>
          </div>
          <span class="pill arch">${structure} Architecture</span>
          <span class="pill muted">${pageTitle(state.page)}</span>
        </div>
        <div class="top-right">
          <button class="btn" id="btn-run-sim">Run 8760 Simulation</button>
          <span class="chip">01 Jan – 31 Dec ${year}</span>
          <button class="icon-btn" title="Theme" id="btn-theme">☾</button>
          <button class="icon-btn" title="Notifications">🔔</button>
          <div class="avatar" title="Analyst">AD</div>
        </div>
      </div>
      ${p.has_default_assumptions
        ? `<div class="banner">⚠ DEFAULT ASSUMPTIONS IN USE — Review and replace project-specific inputs before investment decisions.</div>`
        : `<div class="banner ok">✓ PROJECT INPUTS CONFIGURED</div>`}
      <div class="banner legal">${(state.defaultsMeta && state.defaultsMeta.applicability_banner) || "Legal/regulatory applicability requires validation."}</div>
      ${content}
    </main>
  </div>`;
}

function kpiCard(label, value, opts = {}) {
  const sub = opts.sub ? `<div class="sub ${opts.trend || ""}">${opts.sub}</div>` : "";
  const bar = opts.progress != null
    ? `<div class="progress-mini"><span style="width:${Math.max(0, Math.min(100, opts.progress))}%"></span></div>`
    : "";
  return `<div class="card kpi">
    <div class="kpi-top">
      <div class="label">${label}</div>
      <div class="kpi-ico">${opts.icon || "•"}</div>
    </div>
    <div class="value">${value}</div>
    ${sub}${bar}
  </div>`;
}

function statusPill(text) {
  const t = String(text || "");
  if (/pass|achieved|best|feasible|completed/i.test(t)) return `<span class="pill ok">${t}</span>`;
  if (/legal|review|unknown/i.test(t)) return `<span class="pill warn">${t}</span>`;
  if (/fail|not/i.test(t)) return `<span class="pill danger">${t}</span>`;
  return `<span class="pill muted">${t}</span>`;
}
'''

text2, n = re.subn(
    r"function shell\(content\) \{.*?function kpiCard\(label, value\) \{\n  return `<div class=\"card kpi\"><div class=\"label\">\$\{label\}</div><div class=\"value\">\$\{value\}</div></div>`;\n\}\n",
    shell_new + "\n",
    text,
    count=1,
    flags=re.S,
)
print("shell/kpi replace", n)
if n != 1:
    raise SystemExit("shell replace failed")

dash_path = Path(__file__).resolve().parent / "_dash_snippet.js"
# keep dashboard inline below
dash_new = Path(__file__).with_name("_page_dashboard.js")
# We'll embed directly

DASH = r'''function pageDashboard() {
  const s = state.lastSim;
  if (!s) {
    return `<div class="card empty-dash">
      <h2>Executive Dashboard</h2>
      <p class="muted">Run an 8,760-hour simulation to populate KPIs, energy charts, cost mix and architecture comparison.</p>
      <button class="btn" id="btn-run-sim-dash">Run 8760 Simulation</button>
    </div>`;
  }
  const k = s.kpis;
  const f = s.financial;
  const r = s.recommendation;
  const reT = s.compliance?.annual_re?.target_pct ?? state.project.config.compliance.annual_re_target_pct.value;
  const cfeT = s.compliance?.hourly_cfe?.target_pct ?? state.project.config.compliance.hourly_cfe_target_pct.value;
  const reOk = k.annual_re_pct >= reT;
  const cfeOk = k.hourly_cfe_min_pct >= cfeT;
  const util = k.bess_utilization_pct ?? 0;

  return `
  <div class="kpis">
    ${kpiCard("Annual RE", fmt(k.annual_re_pct) + "%", { icon: "♻", sub: `Target ${fmt(reT,0)}% · ${reOk ? "Achieved" : "Gap"}`, progress: Math.min(100, k.annual_re_pct) })}
    ${kpiCard("Hourly CFE (min)", fmt(k.hourly_cfe_min_pct) + "%", { icon: "◷", sub: `Target ${fmt(cfeT,0)}% · ${cfeOk ? "Achieved" : "Below"}`, progress: Math.min(100, k.hourly_cfe_min_pct) })}
    ${kpiCard("Grid Import", fmt(k.grid_gwh, 3) + " GWh", { icon: "⬡", sub: "Annual wheeled/imported energy" })}
    ${kpiCard("BESS", fmt(k.bess_mw, 0) + " / " + fmt(k.bess_mwh, 0) + " MWh", { icon: "🔋", sub: `Utilization ${fmt(util,1)}%`, progress: util })}
    ${kpiCard("Curtailment", fmt(k.curtailment_pct) + "%", { icon: "↘", sub: "Of renewable generation" })}
    ${kpiCard("Cost", "₹" + fmt(f.cost_per_kwh, 4) + "/kWh", { icon: "₹", sub: "Total annualised / load" })}
    ${kpiCard("NPV", "₹" + fmt(f.npv_cr, 2) + " Cr", { icon: "Σ", sub: "Project cash-flow NPV" })}
    ${kpiCard("IRR", f.irr_pct == null ? "—" : fmt(f.irr_pct) + "%", { icon: "%", sub: "Project IRR" })}
    ${kpiCard("Payback", f.payback_years == null ? "—" : fmt(f.payback_years, 1) + " yr", { icon: "⌛", sub: "Simple payback" })}
  </div>

  <div class="grid dash-main" style="margin-bottom:0.85rem">
    <div class="card">
      <div class="card-head"><h3>Monthly Energy Balance</h3><span class="pill muted">MWh</span></div>
      <div class="chart-box tall" id="chart-month"></div>
    </div>
    <div class="card">
      <div class="card-head"><h3>Hourly CFE Heatmap</h3><span class="pill muted">Month × Hour</span></div>
      <div class="chart-box tall" id="chart-heat"></div>
    </div>
  </div>

  <div class="grid dash-mid" style="margin-bottom:0.85rem">
    <div class="card">
      <div class="card-head"><h3>Cost Breakdown</h3><span class="pill muted">₹/kWh ${fmt(f.cost_per_kwh,4)}</span></div>
      <div id="chart-cost-donut"></div>
    </div>
    <div class="card">
      <div class="card-head"><h3>Energy Mix</h3><span class="pill muted">Generation & supply</span></div>
      <div id="chart-mix-donut"></div>
    </div>
    <div class="card reco">
      <div class="card-head">
        <div>
          <div class="eyebrow">Recommended Architecture</div>
          <h3 style="font-size:1.45rem;margin:0.15rem 0;color:#fff">${r.architecture}</h3>
        </div>
        <span class="pill ok">Feasible</span>
      </div>
      <div class="spec-grid">
        <div class="spec"><div class="k">Solar</div><div class="v">${fmt(r.solar_mw,0)} MW</div></div>
        <div class="spec"><div class="k">Wind</div><div class="v">${fmt(r.wind_mw,0)} MW</div></div>
        <div class="spec"><div class="k">BESS</div><div class="v">${fmt(r.bess_mw,0)} / ${fmt(r.bess_mwh,0)}</div></div>
        <div class="spec"><div class="k">Grid</div><div class="v">${fmt(r.grid_mw,0)} MW</div></div>
      </div>
      <div class="kpi-mini-row">
        <span class="kpi-mini">RE ${fmt(r.annual_re_pct)}%</span>
        <span class="kpi-mini">CFE ${fmt(r.hourly_cfe_pct)}%</span>
        <span class="kpi-mini">₹${fmt(r.cost_per_kwh,4)}/kWh</span>
      </div>
      <div class="insight"><b>Key insight.</b> ${r.why}</div>
    </div>
  </div>

  <div class="grid dash-bottom">
    <div class="card">
      <div class="card-head">
        <h3>Scenario Comparison</h3>
        <button class="btn sm ghost" id="btn-dash-compare">Refresh</button>
      </div>
      <div id="dash-compare"><p class="muted">Loading architecture comparison…</p></div>
    </div>
    <div class="card">
      <div class="card-head"><h3>Compliance Status</h3></div>
      <div class="comp-list">
        <div class="comp-item"><span>RPO</span>${statusPill(s.compliance.rpo.status)}</div>
        <div class="comp-item"><span>RCO</span>${statusPill(s.compliance.rco.status)}</div>
        <div class="comp-item"><span>ESO</span>${statusPill(s.compliance.eso.status)}</div>
        <div class="comp-item"><span>Annual RE</span>${statusPill(s.compliance.annual_re.status)}</div>
        <div class="comp-item"><span>Hourly CFE</span>${statusPill(s.compliance.hourly_cfe.status)}</div>
      </div>
      <div style="margin-top:0.75rem"><a class="btn sm secondary" href="#/compliance">View Compliance Details</a></div>
    </div>
    <div class="card">
      <div class="card-head"><h3>Recent Runs</h3></div>
      <div class="run-list" id="dash-runs">
        <div class="run-item">
          <div><div class="name">8760 Simulation #${s.id || "—"}</div><div class="when">${s.created_at ? new Date(s.created_at).toLocaleString() : "Latest run"}</div></div>
          <div>${statusPill("Completed")}<div class="muted" style="font-size:0.75rem;margin-top:0.25rem">₹${fmt(f.cost_per_kwh,4)}/kWh</div></div>
        </div>
        ${state.opt?.result ? `<div class="run-item">
          <div><div class="name">Optimization #${state.opt.id}</div><div class="when">${state.opt.status}</div></div>
          <div>${statusPill(state.opt.status === "completed" ? "Completed" : state.opt.status)}</div>
        </div>` : `<div class="run-item"><div><div class="name">Optimization</div><div class="when">Not run yet</div></div><div><a class="btn sm ghost" href="#/optimization">Open</a></div></div>`}
      </div>
    </div>
  </div>`;
}
'''

text3, n2 = re.subn(
    r"function pageDashboard\(\) \{.*?^\}\n\nfunction pageSetup",
    DASH + "\n\nfunction pageSetup",
    text2,
    count=1,
    flags=re.S | re.M,
)
print("dashboard replace", n2)
if n2 != 1:
    raise SystemExit("dashboard replace failed")

marker = 'if (state.page === "dashboard" && state.lastSim)'
idx = text3.find(marker)
if idx < 0:
    raise SystemExit("dashboard bind marker missing")

# find end of that block: next "  if (state.page === \"economics\""
end = text3.find('  if (state.page === "economics"', idx)
if end < 0:
    raise SystemExit("economics bind marker missing")

new_bind = r'''  const collapseBtn = document.getElementById("btn-collapse");
  if (collapseBtn) collapseBtn.onclick = () => { state.sidebarCollapsed = !state.sidebarCollapsed; renderApp(); };

  const dashRun = document.getElementById("btn-run-sim-dash");
  if (dashRun) dashRun.onclick = () => document.getElementById("btn-run-sim")?.click();

  async function loadDashCompare() {
    const box = document.getElementById("dash-compare");
    if (!box) return;
    try {
      const cmp = state.compare || await api("/api/compare/architectures", { method: "POST", body: JSON.stringify({ project_id: state.project.id }) });
      state.compare = cmp;
      const arches = cmp.architectures;
      const keys = Object.keys(arches);
      const best = cmp.best;
      box.innerHTML = `<div class="table-wrap"><table><thead><tr>
        <th>Scenario</th><th>Annual RE</th><th>CFE min</th><th>Cost</th><th>NPV Cr</th><th>IRR</th><th>Payback</th><th>Status</th>
      </tr></thead><tbody>
      ${keys.map((k) => {
        const a = arches[k];
        const isBest = k === best;
        const status = isBest ? "Best" : (a.kpis.unserved_mwh > 1e-3 ? "Not Achieved" : "Achieved");
        return `<tr class="${isBest ? "best-row" : ""}">
          <td>${k}</td>
          <td>${fmt(a.kpis.annual_re_pct,1)}%</td>
          <td>${fmt(a.kpis.hourly_cfe_min_pct,1)}%</td>
          <td>₹${fmt(a.financial.cost_per_kwh,4)}</td>
          <td>${fmt(a.financial.npv_cr,2)}</td>
          <td>${a.financial.irr_pct==null?"—":fmt(a.financial.irr_pct,1)+"%"}</td>
          <td>${a.financial.payback_years==null?"—":fmt(a.financial.payback_years,1)}</td>
          <td>${statusPill(status)}</td>
        </tr>`;
      }).join("")}
      </tbody></table></div>`;
    } catch (e) {
      box.innerHTML = `<p class="muted">${e.message}</p>`;
    }
  }

  if (state.page === "dashboard" && state.lastSim) {
    const months = state.lastSim.monthly.map((m) => m.month);
    PTOCharts.stacked(document.getElementById("chart-month"), months, {
      Solar: state.lastSim.monthly.map((m) => m.solar_mwh),
      Wind: state.lastSim.monthly.map((m) => m.wind_mwh),
      "BESS Discharge": state.lastSim.monthly.map((m) => m.bess_discharge_mwh),
      "Grid Import": state.lastSim.monthly.map((m) => m.grid_mwh),
      Curtailment: state.lastSim.monthly.map((m) => m.curtailment_mwh),
    }, {
      colors: ["#d4a017", "#3d9b6a", "#3a8fbf", "#6b7c85", "#c45c3e"],
      yLabel: "Energy (MWh)",
      height: 300,
    });
    PTOCharts.heatmap(document.getElementById("chart-heat"), state.lastSim.heatmap_cfe, { height: 300 });

    const br = state.lastSim.financial.cost_breakdown;
    const costItems = Object.entries(br).map(([k, v]) => ({
      label: PTOCharts.prettyCostLabel(k),
      value: Number(v),
      display: "₹" + Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 }),
    }));
    PTOCharts.donut(document.getElementById("chart-cost-donut"), costItems, {
      centerLabel: "₹/kWh",
      centerValue: fmt(state.lastSim.financial.cost_per_kwh, 4),
      colors: ["#d4a017","#3d9b6a","#3a8fbf","#0f3d2e","#6b7c85","#9a6b14","#2a7a9b","#c45c3e","#5a7a6a","#8a5a12"],
    });

    const k = state.lastSim.kpis;
    const mixItems = [
      { label: "Solar", value: k.annual_solar_mwh || 0, color: "#d4a017" },
      { label: "Wind", value: k.annual_wind_mwh || 0, color: "#3d9b6a" },
      { label: "BESS discharge", value: k.bess_discharge_mwh || 0, color: "#3a8fbf" },
      { label: "Grid", value: (k.grid_gwh || 0) * 1000, color: "#6b7c85" },
    ];
    const mixTotalGwh = mixItems.reduce((a, d) => a + d.value, 0) / 1000;
    PTOCharts.donut(document.getElementById("chart-mix-donut"), mixItems, {
      centerLabel: "Total",
      centerValue: fmt(mixTotalGwh, 2) + " GWh",
    });

    loadDashCompare();
    const btnCmp = document.getElementById("btn-dash-compare");
    if (btnCmp) btnCmp.onclick = async () => {
      state.compare = null;
      btnCmp.disabled = true;
      await loadDashCompare();
      btnCmp.disabled = false;
    };
  }

'''

text4 = text3[:idx] + new_bind + text3[end:]
path.write_text(text4, encoding="utf-8")
print("Wrote", path, "bytes", path.stat().st_size)
