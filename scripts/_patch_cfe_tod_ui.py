# -*- coding: utf-8 -*-
"""Patch in-app Assumptions/Methodology firm-delivery wording to TOD/availability."""
from pathlib import Path

p = Path("frontend/dist/assets/app.js")
t = p.read_text(encoding="utf-8")

repls = [
    (
        "Delivery is <b>firm every hour</b> (Load × mix %) — <b>no plant generation shapes</b>, no plant MW / CAPEX / OPEX / SOC.",
        "Bill uses <b>Architecture mix %</b>. Hourly CFE uses <b>TOD/availability</b> (solar ~0 at night; wind/BESS can serve).",
    ),
    (
        "Firm hourly delivery.",
        "Annual contract energy via mix %; TOD shapes for hourly CFE.",
    ),
    (
        "Both = Architecture contracted mix % × rates (Target = Simulated).",
        "Bill = Architecture mix % × rates (Target = Simulated). CFE = availability.",
    ),
    (
        "<b>24×7 CFE Pass</b> — Every hour ≥ target ${cfeT}% (flat firm mix ⇒ min = mean = RE%).",
        "<b>24×7 CFE Pass</b> — Every hour ≥ target ${cfeT}% (availability; night solar ~0).",
    ),
    (
        "<b>Annual RE / CFE / RPO</b> — Solar% + Wind% + BESS% (firm).",
        "<b>Annual RE / CFE</b> — energy-weighted from hourly availability. <b>RPO</b> — Architecture RE mix.",
    ),
    (
        "What “no plant shapes” means",
        "Bill vs hourly CFE",
    ),
    (
        "Firm hourly contracts (no plant shapes):",
        "Annual contracts + hourly availability:",
    ),
    (
        "Night solar contract share does <b>not</b> go to zero.",
        "Night: solar shape ≈ 0; wind and/or BESS can still serve.",
    ),
    (
        "Cost blend — Target = Simulated",
        "Cost blend (bill) — Target = Simulated",
    ),
]

n = 0
for a, b in repls:
    if a in t:
        t = t.replace(a, b, 1)
        n += 1
        print("OK", n)
    else:
        print("MISS", n)

old_bullets = """      <li><b>Every hour:</b> Solar_MW = Load × Solar%/100; Wind_MW = Load × Wind%/100; DISCOM_MW = Load × DISCOM%/100.</li>
      <li><b>BESS:</b> Mix % × Storage tariff on the bill; BESS% counts in RE/CFE. No BESS plant MW/MWh or SOC.</li>
      <li><b>Night:</b> Solar contract share continues (does not drop to zero). CFE stays at Solar%+Wind%+BESS%.</li>
      <li><b>Removed:</b> Plant CF curves, plant curtailment/SOC charts, plant CAPEX/OPEX/MW fields.</li>"""
new_bullets = """      <li><b>Bill:</b> Architecture mix % × stacked ₹/kWh (Storage tariff × BESS%).</li>
      <li><b>Hourly:</b> Solar/Wind shapes scaled to annual mix%×load — solar ≈ 0 at night (TOD/sunrise–sunset).</li>
      <li><b>BESS:</b> Mix % on the bill; derived storage shifts day RE to night for CFE.</li>
      <li><b>CFE:</b> Min(Load, Solar+Wind+RE-BESS discharge)/Load each hour — not flat firm mix.</li>"""
if old_bullets in t:
    t = t.replace(old_bullets, new_bullets, 1)
    n += 1
    print("OK bullets")
else:
    print("MISS bullets")

old_mono = "Solar_t = Load_t × Solar%/100<br>Wind_t = Load_t × Wind%/100<br>DISCOM_t = Load_t × DISCOM%/100"
new_mono = "Annual Solar/Wind MWh = Load × mix%. Hourly: solar ~0 at night; wind/BESS/DISCOM as available."
if old_mono in t:
    t = t.replace(old_mono, new_mono, 1)
    n += 1
    print("OK mono")

old_cfe = """    <p class="mono" style="margin:0.35rem 0 0.65rem;font-size:0.88rem">RE% = Solar% + Wind% + BESS%</p>
    <p>Compared to annual RE target <b>${reT}%</b>. Same value every hour (firm).</p>"""
new_cfe = """    <p class="mono" style="margin:0.35rem 0 0.65rem;font-size:0.88rem">Annual RE% = Σ RE serving load / Σ Load × 100</p>
    <p>Compared to annual RE target <b>${reT}%</b>. Architecture mix % is the bill share — not flat hourly CFE.</p>"""
if old_cfe in t:
    t = t.replace(old_cfe, new_cfe, 1)
    n += 1
    print("OK cfe block")

p.write_text(t, encoding="utf-8")
print("replacements", n)
