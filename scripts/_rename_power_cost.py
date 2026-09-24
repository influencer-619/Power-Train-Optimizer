# -*- coding: utf-8 -*-
from pathlib import Path
import re

app = Path("frontend/dist/assets/app.js")
t = app.read_text(encoding="utf-8")
repls = [
    ("Power cost ₹/kWh", "Energy Cost ₹/kWh"),
    ("Power cost (₹/kWh)", "Energy Cost (₹/kWh)"),
    ("Power cost ·", "Energy Cost ·"),
    ('label: "Power cost"', 'label: "Energy Cost"'),
    ('"Power cost", "₹"', '"Energy Cost", "₹"'),
    ("<b>Power cost ₹/kWh</b>", "<b>Energy Cost ₹/kWh</b>"),
]
n = 0
for a, b in repls:
    c = t.count(a)
    if c:
        t = t.replace(a, b)
        n += c
        print("OK", c, a)
    else:
        print("MISS", a)
app.write_text(t, encoding="utf-8")
print("remaining Power cost", t.count("Power cost"))
print("Energy Cost ₹/kWh", t.count("Energy Cost ₹/kWh"))

idx = Path("frontend/dist/index.html")
h = re.sub(r"app\.js\?v=\d+", "app.js?v=148", idx.read_text(encoding="utf-8"))
idx.write_text(h, encoding="utf-8")
print("v148", "v=148" in h)
