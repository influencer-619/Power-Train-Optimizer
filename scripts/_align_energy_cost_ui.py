# -*- coding: utf-8 -*-
"""Update UI tips for Energy Cost = blended / DISCOM rate; Annual bill = rate × energy."""
from pathlib import Path
import re

app = Path("frontend/dist/assets/app.js")
t = app.read_text(encoding="utf-8")

repls = [
    (
        'tip: "Year-1 total power bill ÷ annual load kWh."',
        'tip: "Captive/Hybrid: blended rate (Discom×G% + Solar×S% + Wind×W% + BESS×Storage%). DISCOM: DISCOM stack rate. Annual energy bill = this × load kWh."',
    ),
    (
        'tip: "Year-1 total power bill ÷ annual load kWh.",',
        'tip: "Captive/Hybrid: blended rate. DISCOM: DISCOM stack rate. Annual energy bill = Energy Cost × load kWh.",',
    ),
    (
        'tip: "Year-1 architecture power bill (₹ Cr)."',
        'tip: "Annual energy bill ₹ Cr = Energy Cost ₹/kWh × annual load kWh / 1e7. Demand/fixed shown separately."',
    ),
    (
        'tip: "Year-1 architecture power bill in ₹ Cr."',
        'tip: "Annual energy bill ₹ Cr = Energy Cost ₹/kWh × annual load kWh / 1e7. Demand/fixed shown separately."',
    ),
]

# Broader tipPowerCost if present
n = 0
for a, b in repls:
    if a in t:
        t = t.replace(a, b)
        n += 1
        print("OK tip", n)
    else:
        print("MISS", a[:50])

# tipPowerCost variable
old_tip = None
i = t.find("tipPowerCost")
if i >= 0:
    print("tipPowerCost context:", repr(t[i : i + 200]))

# Donut center tip already has formula - update centerTip default in call site
old_center = 'centerTip: `₹/kWh = Year-1 total bill ÷ annual load kWh | Blended energy = Discom×${fmt(gPct,1)}% + Solar×${fmt(sPct,1)}% + Wind×${fmt(wPct,1)}% + BESS×${fmt(bPct,1)}% (+ demand + fixed)`,'
new_center = 'centerTip: `Energy Cost = blended rate (Discom×${fmt(gPct,1)}% + Solar×${fmt(sPct,1)}% + Wind×${fmt(wPct,1)}% + BESS×${fmt(bPct,1)}%). Annual energy bill = Energy Cost × load kWh. Demand/fixed are separate slices.`,'
if old_center in t:
    t = t.replace(old_center, new_center, 1)
    print("OK centerTip")
else:
    print("MISS centerTip")

# Subtext under energy cost card
t2 = t.replace("per kWh delivered", "blended / DISCOM energy rate")
if t2 != t:
    t = t2
    print("OK subtext")

# Methodology page line about Power/Energy cost
t = t.replace(
    "<b>Energy Cost ₹/kWh</b> = Year-1 total bill ÷ annual load kWh (TOTAL COST OF DELIVERED ENERGY).",
    "<b>Energy Cost ₹/kWh</b> = blended rate (Captive/Hybrid) or DISCOM rate (baseline). Annual energy bill = Energy Cost × load kWh.",
)
t = t.replace(
    "<b>Power cost ₹/kWh</b> = Year-1 total bill ÷ annual load kWh (TOTAL COST OF DELIVERED ENERGY).",
    "<b>Energy Cost ₹/kWh</b> = blended rate (Captive/Hybrid) or DISCOM rate (baseline). Annual energy bill = Energy Cost × load kWh.",
)

app.write_text(t, encoding="utf-8")

idx = Path("frontend/dist/index.html")
h = idx.read_text(encoding="utf-8")
h = re.sub(r"app\.js\?v=\d+", "app.js?v=149", h)
h = re.sub(r"charts\.js\?v=\d+", "charts.js?v=149", h)
h = re.sub(r"styles\.css\?v=\d+", "styles.css?v=149", h)
idx.write_text(h, encoding="utf-8")
print("v149")
