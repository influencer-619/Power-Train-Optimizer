# -*- coding: utf-8 -*-
from pathlib import Path
import re

app = Path("frontend/dist/assets/app.js")
t = app.read_text(encoding="utf-8")

old = """        const costItemsRaw = PTOCharts.costBreakdownEntries(br);
        const costTotal = costItemsRaw.reduce((a, [, v]) => a + v, 0) || 1;
        const costItems = costItemsRaw.map(([k, v]) => ({
          label: PTOCharts.prettyCostLabel(k),
          value: v,
          display: `₹${fmt(v / 1e7, 2)} Cr | ${fmt((v / costTotal) * 100, 1)}%`,
        }));
        PTOCharts.donut(costEl, costItems, {
          size: 240,
          centerLabel: "₹/kWh",
          centerValue: fmt(f.cost_per_kwh, 4),
          colors: ["#f0b429","#1aa6a0","#3b82c4","#0b2a4a","#7b8794","#b7791f","#2f7db8","#e26d5a","#5a7a6a","#8a5a12"],
        });"""

new = """        const costItemsRaw = PTOCharts.costBreakdownEntries(br);
        const costTotal = costItemsRaw.reduce((a, [, v]) => a + v, 0) || 1;
        const gPct = Number(xt.grid_pct) || 0;
        const sPct = Number(xt.solar_pct) || 0;
        const wPct = Number(xt.wind_pct) || 0;
        const bPct = Number(xt.bess_pct) || 0;
        const gRate = Number(xt.discom_rate_inr_per_kwh) || 0;
        const sRate = Number(xt.solar_rate_inr_per_kwh) || 0;
        const wRate = Number(xt.wind_rate_inr_per_kwh) || 0;
        const bRate = Number(xt.bess_rate_inr_per_kwh) || 0;
        const costTipByKey = {
          grid_energy_inr: `DISCOM energy ₹ = Annual load (MWh) × ${fmt(gPct,1)}% × ₹${fmt(gRate,4)}/kWh × 1,000`,
          solar_energy_or_ann_inr: `Solar energy ₹ = Annual load (MWh) × ${fmt(sPct,1)}% × ₹${fmt(sRate,4)}/kWh × 1,000`,
          wind_energy_or_ann_inr: `Wind energy ₹ = Annual load (MWh) × ${fmt(wPct,1)}% × ₹${fmt(wRate,4)}/kWh × 1,000`,
          bess_energy_inr: `BESS energy ₹ = Annual load (MWh) × ${fmt(bPct,1)}% × Storage ₹${fmt(bRate,4)}/kWh × 1,000`,
          demand_inr: `Demand ₹ = Peak_MW × DISCOM ${fmt(gPct,1)}% × demand ₹/MW-month × 12`,
          fixed_inr: `Fixed ₹ = annual fixed charge (+ meter / LD if configured)`,
          compliance_inr: `Compliance ₹ = RPO/RCO + ESO buyout (when Applicable)`,
          additional_costs_inr: `Additional ₹ = Project Setup → Financial additional annual costs`,
        };
        const costItems = costItemsRaw.map(([k, v]) => {
          const base = PTOCharts.costFormula?.(k) || costTipByKey[k] || "";
          const tip = (costTipByKey[k] || base) + ` | Amount: ₹${fmt(v / 1e7, 2)} Cr (${fmt((v / costTotal) * 100, 1)}% of bill)`;
          return {
            label: PTOCharts.prettyCostLabel(k),
            value: v,
            tip,
            display: `₹${fmt(v / 1e7, 2)} Cr | ${fmt((v / costTotal) * 100, 1)}%`,
          };
        });
        PTOCharts.donut(costEl, costItems, {
          size: 240,
          centerLabel: "₹/kWh",
          centerValue: fmt(f.cost_per_kwh, 4),
          centerTip: `₹/kWh = Year-1 total bill ÷ annual load kWh | Blended energy = Discom×${fmt(gPct,1)}% + Solar×${fmt(sPct,1)}% + Wind×${fmt(wPct,1)}% + BESS×${fmt(bPct,1)}% (+ demand + fixed)`,
          colors: ["#f0b429","#1aa6a0","#3b82c4","#0b2a4a","#7b8794","#b7791f","#2f7db8","#e26d5a","#5a7a6a","#8a5a12"],
          footnote: "Hover a slice or legend row to see the formula",
        });"""

if old not in t:
    raise SystemExit("cost donut block not found")
t = t.replace(old, new, 1)

# Power mix donut tips too
old2 = """        PTOCharts.donut(mixEl, mixItems.map((d) => ({
          ...d,
          display: `${fmt(d.value, 1)}%`,
        })), {
          size: 240,
          centerLabel: "CFE",
          centerValue: fmt(Number(xt.cfe_pct ?? xt.re_pct) || 0, 1) + "%",
          colors: mixItems.map((d) => d.color),
        });"""
new2 = """        PTOCharts.donut(mixEl, mixItems.map((d) => ({
          ...d,
          display: `${fmt(d.value, 1)}%`,
          tip: `${d.label} Architecture mix ${fmt(d.value, 1)}% — used for the bill (Load × mix% × that source ₹/kWh). Hourly CFE uses TOD availability, not this flat %.`,
        })), {
          size: 240,
          centerLabel: "CFE",
          centerValue: fmt(Number(xt.cfe_pct ?? xt.re_pct) || 0, 1) + "%",
          centerTip: "Architecture CF mix % = Solar% + Wind% + BESS% (bill / contract). Hourly CFE Pass uses TOD availability.",
          colors: mixItems.map((d) => d.color),
          footnote: "Hover a slice or legend row to see how mix % is used",
        });"""
if old2 not in t:
    print("WARN: mix donut block not found")
else:
    t = t.replace(old2, new2, 1)
    print("OK mix tips")

app.write_text(t, encoding="utf-8")

idx = Path("frontend/dist/index.html")
h = idx.read_text(encoding="utf-8")
h2 = re.sub(r"charts\.js\?v=\d+", "charts.js?v=145", h)
h2 = re.sub(r"app\.js\?v=\d+", "app.js?v=145", h2)
h2 = re.sub(r"styles\.css\?v=\d+", "styles.css?v=145", h2)
idx.write_text(h2, encoding="utf-8")
print("OK app.js + index v=145")
