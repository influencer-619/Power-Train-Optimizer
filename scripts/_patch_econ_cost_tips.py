# -*- coding: utf-8 -*-
from pathlib import Path

t = Path("frontend/dist/assets/app.js").read_text(encoding="utf-8")
old = (
    "${(PTOCharts.costBreakdownEntries(f.cost_breakdown) || []).map(([k,v]) =>\n"
    '      `<tr><td>${PTOCharts.prettyCostLabel(k)}</td><td class="mono">${money(v)}</td></tr>`\n'
    '    ).join("")}'
)
new = (
    "${(PTOCharts.costBreakdownEntries(f.cost_breakdown) || []).map(([k,v]) => {\n"
    "      const tip = (PTOCharts.costFormula?.(k) || PTOCharts.prettyCostLabel(k)) + ` | ${money(v)}`;\n"
    "      return `<tr class=\"has-tip\" title=\"${escHtml(tip)}\" data-tip=\"${escHtml(tip)}\"><td>${PTOCharts.prettyCostLabel(k)}</td><td class=\"mono\">${money(v)}</td></tr>`;\n"
    '    }).join("")}'
)
if old not in t:
    raise SystemExit("econ table block not found")
Path("frontend/dist/assets/app.js").write_text(t.replace(old, new, 1), encoding="utf-8")
print("OK economics table tips")
