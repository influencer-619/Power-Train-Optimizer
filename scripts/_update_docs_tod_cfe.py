# -*- coding: utf-8 -*-
"""Patch user guide + in-app Assumptions/Methodology for TOD/availability CFE."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_user_guide() -> None:
    guide = ROOT / "scripts" / "generate_user_guide.py"
    t = guide.read_text(encoding="utf-8")
    orig = t

    replacements = [
        (
            '"Optional PROJECT DATA 8,760-hour CSV import on Load setup (demand); Solar/Wind are firm mix — not plant invent"',
            '"Optional PROJECT DATA CSV on Load / Solar / Wind (shapes). Mix % sets annual energy; bill uses Architecture %"',
        ),
        (
            '"Firm hourly delivery — Solar/Wind/DISCOM MW each hour = Load × mix%/100; no plant CF shapes for KPIs/charts.",',
            '"Hourly CFE uses TOD/availability (solar ~0 at night; wind/BESS can serve). Bill uses Architecture mix %.",',
        ),
        (
            '''                "Firm hourly delivery: Solar_t = Load_t × Solar%/100 (same for Wind/DISCOM). "
                "TARGET_POWER_PCT and SIMULATED_ENERGY_SHARE both bill Architecture contracted mix % "
                "(Target = Simulated). No plant MW inventing; plant generation shapes are not used.",''',
            '''                "Mix % = annual contract energy (Σ Solar = Load×Solar%, shapes preserved — solar ~0 at night). "
                "Bill: TARGET_POWER_PCT and SIMULATED_ENERGY_SHARE both use Architecture mix %. "
                "Hourly CFE = Min(Load, Solar+Wind+RE-BESS)/Load.",''',
        ),
        (
            '''                "Target = Simulated (firm mix)",
                "Grid% = DISCOM mix %; RE% = Solar% + Wind% + BESS%. Both Target and Simulated equal "
                "Architecture contracted mix (firm delivery every hour, including night).",''',
            '''                "Bill: Target = Simulated (Architecture mix)",
                "Economics Grid%|RE% = Architecture DISCOM% | Solar%+Wind%+BESS%. "
                "Hourly CFE / Annual RE use TOD availability (not flat firm mix).",''',
        ),
        (
            '"Open Economics for Target = Simulated (Architecture mix); Hourly CFE for firm CFE charts; export Excel/PDF from Reports.",',
            '"Open Economics for Target = Simulated (bill); Hourly CFE for TOD availability charts; export Excel/PDF from Reports.",',
        ),
        (
            '''            "In-app summary of firm hourly delivery, bill blend (Target = Simulated), Annual RE / 24×7 CFE, carbon, "
            "and NPV of savings vs DISCOM. Section 17A of this guide expands formulas.",''',
            '''            "In-app summary of bill blend (Architecture mix), TOD/availability CFE, Annual RE, carbon, "
            "and NPV of savings vs DISCOM. Section 17A of this guide expands formulas.",''',
        ),
        (
            '''        "Commercial buyer path: Solar delivery is firm (Load × Solar% every hour) — plant diurnal CF curves are not used "
        "for KPIs, CFE, or charts. Legacy synthetic/PROJECT DATA plant-shape fields are out of scope for the buyer model.",''',
            '''        "Solar annual MWh = Load × Solar%. Hourly shape (synthetic sunrise–sunset or PROJECT DATA) is scaled to that "
        "annual energy — solar ≈ 0 at night. Used for hourly CFE/charts; bill still uses Architecture mix %.",''',
        ),
        (
            '''        "Commercial buyer path: Wind delivery is firm (Load × Wind% every hour) — plant wind CF curves are not used "
        "for KPIs, CFE, or charts.",''',
            '''        "Wind annual MWh = Load × Wind%. Hourly shape (synthetic or PROJECT DATA) is scaled to that annual energy "
        "and can serve at night. Used for hourly CFE/charts; bill uses Architecture mix %.",''',
        ),
        (
            '''        "Buyer BESS contract: Storage tariff ₹/kWh and mix % only (counts in RE/CFE). No BESS plant MW/MWh/SOC.",''',
            '''        "Buyer BESS: Storage tariff × mix % on the bill. If BESS mix > 0, derived storage shifts day RE to night for CFE.",''',
        ),
        (
            '''            "Firm hourly delivery: Solar_t / Wind_t / DISCOM_t = Load_t × mix%/100 every study hour "
            "(including night — solar share does not drop to zero). BESS% billed at Storage tariff; no plant SOC.",''',
            '''            "Annual Solar/Wind MWh = Load × mix%; hourly shapes keep TOD (solar ~0 at night). "
            "BESS% billed at Storage tariff; derived storage for night CFE when BESS mix > 0.",''',
        ),
        (
            '''            "CAPTIVE with Solar 50% + Wind 30% + BESS 20%: bill and firm CFE use those shares every hour.",
            "Hybrid with Wind unchecked: DISCOM + Solar + BESS % must sum to 100 (e.g. 25 / 50 / 25).",
            "Target Grid% | RE% always equals Simulated Grid% | RE% (Architecture mix).",''',
            '''            "CAPTIVE with Solar 50% + Wind 30% + BESS 20%: bill uses those shares; night CFE needs wind/BESS.",
            "Hybrid with Wind unchecked: DISCOM + Solar + BESS % must sum to 100 (e.g. 25 / 50 / 25).",
            "Bill Target Grid%|RE% = Simulated = Architecture mix; hourly CFE follows availability.",''',
        ),
        (
            '''            "Annual RE % = Solar% + Wind% + BESS% (Architecture contracted mix — same every hour).",
            "Hourly CFE % = Min(Load, Load × (Solar%+Wind%+BESS%)/100) / Load × 100. "
            "With firm mix this equals Solar%+Wind%+BESS% every hour, including night (solar share does not go to zero).",
            "Energy-weighted CFE ≡ Annual RE % when mix is firm (min = mean = RE%).",
            "CFE pass modes: All hours >= target | Mean hourly CFE >= target | Share of hours >= target.",
            "Default pass mode All hours >= target is a strict 24×7 rule: Pass iff Architecture RE mix ≥ hourly CFE target "
            "(flat firm series). Fail means raise Solar/Wind/BESS mix % or lower the target under Project Setup → Compliance — "
            "not “add plant MW” or “fix night solar shapes”.",
            "Dashboard CFE Pass Mode card shows: mode, target, min hour, % hours ≥ target, longest continuous deficit streak (hours), max deficit (pp).",
            "Dashboard Compliance Status shows actual vs target and a short “Why Fail?” note when status is Fail.",
            "CFE heatmap uses an absolute 0–100% colour scale; with firm mix the heatmap is flat at the Architecture RE %.",''',
            '''            "Annual RE % = Σ RE serving load / Σ Load × 100 (availability — direct Solar+Wind + RE-origin BESS).",
            "Hourly CFE % = Min(Load, Solar_t + Wind_t + RE-BESS_discharge_t) / Load × 100. "
            "Solar ≈ 0 at night; night CFE comes from wind and/or BESS.",
            "Energy-weighted CFE ≡ Annual RE % (same matched CF / load). Min hourly CFE is often below Architecture RE mix %.",
            "CFE pass modes: All hours >= target | Mean hourly CFE >= target | Share of hours >= target.",
            "Default All hours >= target is a strict 24×7 rule. Fail at night usually means raise Wind/BESS mix, "
            "improve shapes, or relax the target — not pretend solar is on at night.",
            "Dashboard CFE Pass Mode card shows: mode, target, min hour, % hours ≥ target, longest continuous deficit streak (hours), max deficit (pp).",
            "Dashboard Compliance Status shows actual vs target and a short “Why Fail?” note when status is Fail.",
            "CFE heatmap uses an absolute 0–100% colour scale; night hours often read lower than daytime.",''',
        ),
        (
            '''            ["Annual RE", "Architecture Solar% + Wind% + BESS%"],
            ["Hourly CFE (min)", "Min hourly firm CFE (= Architecture RE% with firm mix); Pass/Fail vs target"],
            ["Grid Import", "Annual contracted DISCOM energy (Load × DISCOM%) in GWh"],
            ["BESS", "Contracted BESS mix % × Storage tariff (no plant MW/MWh on buyer path)"],''',
            '''            ["Annual RE", "Energy-weighted RE serving load / load (availability)"],
            ["Hourly CFE (min)", "Min hourly CFE from Solar+Wind+RE-BESS; Pass/Fail vs target"],
            ["Grid Import", "Annual DISCOM import from dispatch (GWh)"],
            ["BESS", "Bill: Storage tariff × mix %. Hourly: derived storage when BESS mix > 0"],''',
        ),
        (
            '''            "Build DC load for each LF scenario (S1–S4) from Seasonal TOD / study period (demand shape only).",
            "Apply Architecture firm contracts: Solar_t = Load_t × Solar%/100 (same for Wind/DISCOM); BESS% on bill + RE/CFE.",
            "Validate finite values and energy identities — MODEL ERROR on hard failure. Unserved MWh = 0 on the buyer path.",
            "Run Captive and Hybrid commercial profiles plus DISCOM baseline; store SHA-256 config fingerprint.",
            "Compute KPIs, firm CFE analytics, compliance, feasibility, tariff-stack economics and savings vs DISCOM.",''',
            '''            "Build DC load for each LF scenario (S1–S4) from Seasonal TOD / study period (demand shape only).",
            "Scale Solar/Wind shapes to annual mix%×load; derive BESS storage if BESS mix > 0; set DISCOM grid cap.",
            "Dispatch hourly: RE to load, charge BESS from excess, discharge at deficit, DISCOM residual.",
            "Validate finite values — MODEL ERROR on hard failure. Commercial unserved_mwh = 0 (feasibility ignores profile unserved).",
            "Compute availability CFE/RE, compliance, feasibility, tariff-stack economics (Architecture mix bill) and savings vs DISCOM.",''',
        ),
        (
            '"Hourly CFE → Time window charts (firm CFE flat at Architecture RE%); Economics → Target = Simulated mix.",',
            '"Hourly CFE → TOD availability charts (night solar ~0); Economics → Target = Simulated bill mix.",',
        ),
        (
            '"Detailed calculations & formulas (firm delivery, bill blend, RE/CFE, carbon, savings NPV)",',
            '"Detailed calculations & formulas (bill blend, TOD/availability CFE, carbon, savings NPV)",',
        ),
        (
            '''                "Month-wise load, contracted Solar/Wind/BESS/DISCOM, RE%, firm CFE.",''',
            '''                "Month-wise load, available Solar/Wind/BESS/DISCOM, RE%, hourly CFE.",''',
        ),
        (
            '''                "No DISCOM. Selected mix % must sum to 100%. Firm hourly delivery.",''',
            '''                "No DISCOM. Selected mix % must sum to 100%. Bill = mix %; CFE = availability.",''',
        ),
        (
            '''            "Annual RE / CFE / RPO — Solar% + Wind% + BESS% (firm). 24×7 Pass = every hour ≥ target (flat = RE%).",
            "ESO — Required = load × ESO%; actual = load × BESS mix %. Carbon: baseline = load×EF; actual = load×DISCOM%×EF.",
            "Feasibility — Gates on RE/CFE (and Applicable RPO/ESO) — not on plant-profile unserved.",''',
            '''            "Annual RE / hourly CFE — availability (Solar+Wind+RE-BESS). Architecture mix shown for bill reference.",
            "RPO — Architecture RE mix. ESO — load × BESS mix %. Carbon: baseline = load×EF; actual = load×DISCOM%×EF.",
            "Feasibility — Gates on RE/CFE (and Applicable RPO/ESO) — not on plant-profile unserved.",''',
        ),
        (
            '''            "What “no plant shapes” means", bold=True)
    add_bullets(
        doc,
        [
            "Every hour: Solar_MW = Load × Solar%/100; Wind_MW = Load × Wind%/100; DISCOM_MW = Load × DISCOM%/100.",
            "BESS: Mix % × Storage tariff on the bill; BESS% counts in RE/CFE. No BESS plant MW/MWh or SOC.",
            "Night: Solar contract share continues (does not drop to zero). CFE stays at Solar%+Wind%+BESS%.",
            "Removed: Plant CF curves, plant curtailment/SOC charts, plant CAPEX/OPEX/MW fields.",
        ],
    )''',
            '''            "Bill vs hourly CFE", bold=True)
    add_bullets(
        doc,
        [
            "Bill: Architecture mix % × stacked ₹/kWh (Storage tariff × BESS%).",
            "Hourly: Solar/Wind shapes scaled to annual mix%×load — solar ≈ 0 at night.",
            "BESS: Mix % on the bill; derived storage shifts day RE to night for CFE.",
            "CFE: Min(Load, Solar+Wind+RE-BESS)/Load each hour — not flat Architecture RE%.",
        ],
    )''',
        ),
    ]

    n_ok = 0
    for old, new in replacements:
        if old not in t:
            print("MISS UG:", old[:70].replace("\n", " "))
            continue
        t = t.replace(old, new, 1)
        n_ok += 1
    print(f"user_guide replacements: {n_ok}/{len(replacements)}")

    # Section 15.2 methodology numbered list
    old_15_2 = '''    add_numbered(
        doc,
        [
            "Product scope — Captive + Hybrid equal analysis; DISCOM = savings baseline; no recommendation / Status row; "
            "no plant CAPEX/OPEX / plant shapes UI.",
            "Study period & load — Peak = IT × PUE; Seasonal TOD shapes demand only; LF S1–S4 (headline = S1); "
            "annual load = Σ hourly MWh.",
            "Architecture mix & firm delivery — Selected mix % sum to 100%; Solar_t = Load_t × Solar%/100 "
            "(same for Wind/DISCOM); BESS = Storage tariff × BESS%; no plant CF curves.",
            "Cost blend — TARGET_POWER_PCT and SIMULATED_ENERGY_SHARE both use Architecture contracted mix % "
            "(Target = Simulated). Blended = Discom×G% + Solar×S% + Wind×W% + Storage×B%.",
            "Annual bill / ₹/kWh / savings / NPV — Bill = load × blended × 1000; ₹/kWh = Year-1 bill ÷ load kWh; "
            "demand = Peak × DISCOM% × demand ₹/MW-month × 12; savings vs 100% DISCOM; NPV at discount rate "
            "(Year-0 generation CAPEX = 0).",
            "Annual RE % — Solar% + Wind% + BESS% (compared to annual RE target).",
            "24×7 CFE — CFE_t = Min(Load, Load×(S+W+B)/100)/Load×100 = Architecture RE% every hour (including night). "
            "Pass = every study hour ≥ hourly CFE target.",
            "Carbon — Baseline = load × grid EF; actual = load × DISCOM%/100 × EF; saved = baseline − actual.",
            "Compliance — RPO/RCO on Architecture RE %; ESO on contracted BESS mix × load; feasibility ignores plant unserved.",
            "Workflow — Setup both architectures → Save → Run Analysis → compare → detail tabs → Assumptions audit.",
        ],
    )'''
    new_15_2 = '''    add_numbered(
        doc,
        [
            "Product scope — Captive + Hybrid equal analysis; DISCOM = savings baseline; no recommendation / Status row; "
            "no plant CAPEX/OPEX as commercial inputs.",
            "Study period & load — Peak = IT × PUE; Seasonal TOD shapes demand; LF S1–S4 (headline = S1); "
            "annual load = Σ hourly MWh.",
            "Architecture mix (bill) — Selected mix % sum to 100%; Blended = Discom×G% + Solar×S% + Wind×W% + Storage×B%.",
            "Hourly availability — Solar/Wind shapes scaled to annual mix%×load (solar ~0 at night); "
            "BESS mix > 0 derives storage for night shifting; DISCOM fills residual when included.",
            "Cost blend — TARGET_POWER_PCT and SIMULATED_ENERGY_SHARE both price Architecture mix % (bill Target = Simulated).",
            "Annual bill / ₹/kWh / savings / NPV — Bill = load × blended × 1000; demand = Peak × DISCOM%; "
            "savings vs 100% DISCOM; NPV at discount rate (Year-0 generation CAPEX = 0).",
            "Annual RE % — Σ RE serving load / Σ Load (availability).",
            "24×7 CFE — CFE_t = Min(Load, Solar+Wind+RE-BESS)/Load×100. Pass = every hour ≥ target. "
            "Night CFE from wind/BESS, not firm solar.",
            "Carbon — Baseline = load × grid EF; actual = load × DISCOM%/100 × EF; saved = baseline − actual.",
            "Compliance — Annual RE/CFE = availability; RPO/RCO = Architecture RE mix; ESO = BESS mix × load.",
            "Workflow — Setup both architectures → Save → Run Analysis → compare → Hourly CFE → Assumptions audit.",
        ],
    )'''
    if old_15_2 in t:
        t = t.replace(old_15_2, new_15_2, 1)
        print("OK: 15.2")
    else:
        print("MISS: 15.2")

    # 17A.3–17A.8 core
    old_17 = '''    add_heading(doc, "17A.3 Firm Solar / Wind / DISCOM delivery (buyer path)", 2)
    add_para(
        doc,
        "Plant diurnal CF curves are not used for commercial KPIs, CFE, or charts. Every study hour:",
    )
    add_para(
        doc,
        "Solar_t = Load_t × (Solar%/100);  Wind_t = Load_t × (Wind%/100);  DISCOM_t = Load_t × (DISCOM%/100)",
        italic=True,
    )
    add_bullets(
        doc,
        [
            "Night hours keep the Solar contract share — it does not drop to zero.",
            "BESS% is billed at Storage tariff and counted in RE/CFE; there is no BESS plant MW/MWh/SOC on the buyer path.",
            "Unserved_mwh = 0 with firm contracts; feasibility does not gate on plant-profile unserved.",
            "Charts show contracted Load / Solar / Wind(+BESS) / DISCOM and firm CFE — not plant SOC or plant curtailment.",
        ],
    )

    add_heading(doc, "17A.4 DC load shape (demand only)", 2)
    add_bullets(
        doc,
        [
            "Seasonal TOD and LF S1–S4 shape data-centre demand only.",
            "They do not invent Solar/Wind plant generation profiles.",
            "Optional PROJECT DATA CSV on Load replaces the synthetic demand series when configured.",
        ],
    )

    add_heading(doc, "17A.5 Hourly energy balance (firm contracts)", 2)
    add_para(
        doc,
        "With firm Architecture mix, contracted supplies sum to Load every hour "
        "(Solar% + Wind% + BESS% + DISCOM% = 100% for selected assets):",
    )
    add_para(
        doc,
        "Solar_t + Wind_t(+BESS firm RE) + DISCOM_t = Load_t",
        italic=True,
    )
    add_bullets(
        doc,
        [
            "No plant curtailment / plant SOC / plant charge-discharge stack on the commercial buyer path.",
            "BESS appears as mix % × Storage tariff and as RE/CFE credit — not as a sized battery plant.",
            "Legacy plant-dispatch / LP modes are out of product scope for buyer economics.",
        ],
    )

    add_heading(doc, "17A.6 Architecture RE serving load", 2)
    add_bullets(
        doc,
        [
            "RE_serving_load_t = Load_t × (Solar% + Wind% + BESS%) / 100 every hour.",
            "Contracted BESS mix is treated as 100% RE-origin for buyer-path ESO / CFE.",
            "DISCOM share does not count toward RE / CFE.",
        ],
    )

    add_heading(doc, "17A.7 Annual RE %", 2)
    add_para(
        doc,
        "Annual RE % = Solar% + Wind% + BESS%",
        italic=True,
    )
    add_para(
        doc,
        "Pass if Annual RE % ≥ annual_re_target_pct. Gap (pp) = max(0, target − actual). "
        "With firm mix, energy-weighted CFE over the year equals Annual RE %.",
    )

    add_heading(doc, "17A.8 Hourly CFE % and pass modes", 2)
    add_para(
        doc,
        "CFE_t = Min(Load_t, Load_t × (Solar%+Wind%+BESS%)/100) / Load_t × 100  "
        "(= Architecture RE% every hour when Load_t > 0; if Load_t ≈ 0, CFE_t is treated as 100%)",
        italic=True,
    )
    add_table(
        doc,
        ["CFE pass mode", "Pass rule", "Actual used for gap"],
        [
            ["All hours ≥ target", "Every hour CFE_t ≥ target (flat firm series ⇒ min = RE%)", "Minimum hourly CFE (= RE%)"],
            ["Mean hourly CFE ≥ target", "Unweighted mean of CFE_t ≥ target", "Mean hourly CFE (= RE%)"],
            ["Share of hours ≥ target", "% of hours with CFE_t ≥ target ≥ cfe_hour_share_target_pct", "% hours meeting"],
        ],
    )
    add_para(doc, "CFE analytics also report:", bold=True)
    add_bullets(
        doc,
        [
            "min / mean / median / P95 hourly CFE (equal under firm mix)",
            "% hours ≥ target; hours below target",
            "Longest continuous deficit streak (hours) — all-or-nothing vs target when flat",
            "Max and mean CFE deficit in percentage points (pp) where below target",
            "Duration curve (flat at Architecture RE% under firm delivery)",
        ],
    )'''

    new_17 = '''    add_heading(doc, "17A.3 Solar / Wind / DISCOM — annual contract + hourly shapes", 2)
    add_para(
        doc,
        "Architecture mix % sets annual contract energy. Hourly shapes keep TOD/availability:",
    )
    add_para(
        doc,
        "Σ Solar_t = Load_annual × Solar%/100;  Σ Wind_t = Load_annual × Wind%/100 "
        "(shapes from synthetic CF or PROJECT DATA; solar ≈ 0 outside sunrise–sunset)",
        italic=True,
    )
    add_bullets(
        doc,
        [
            "Night: solar contribution ≈ 0; wind shape can still be non-zero.",
            "BESS% is billed at Storage tariff; if BESS mix > 0, derived power/energy shifts day RE to night.",
            "DISCOM included → grid import cap ≈ peak; Captive → grid cap = 0.",
            "Commercial unserved_mwh = 0 for feasibility; charts show availability series.",
        ],
    )

    add_heading(doc, "17A.4 DC load shape (demand)", 2)
    add_bullets(
        doc,
        [
            "Seasonal TOD and LF S1–S4 shape data-centre demand.",
            "Solar night = 0 comes from the solar profile (sunrise–sunset), not from load TOD alone.",
            "Optional PROJECT DATA CSV on Load / Solar / Wind replaces synthetic series when configured.",
        ],
    )

    add_heading(doc, "17A.5 Hourly dispatch (availability)", 2)
    add_para(
        doc,
        "Each hour: RE (Solar+Wind) serves load first; excess charges BESS; residual load from BESS discharge "
        "then DISCOM (if grid cap > 0). Curtailment if RE remains after charge.",
    )
    add_para(
        doc,
        "Solar_t + Wind_t + Discharge_t + Grid_t + Unserved_t ≈ Load_t + Charge_t + Curtailment_t",
        italic=True,
    )
    add_bullets(
        doc,
        [
            "RE-origin tracking on BESS charge/discharge — only RE-origin discharge counts toward CFE.",
            "Bill still uses Architecture mix % × tariffs (not dispatch energy shares).",
        ],
    )

    add_heading(doc, "17A.6 RE serving load", 2)
    add_bullets(
        doc,
        [
            "RE_serving_load_t = Direct Solar+Wind to load + RE-origin BESS discharge.",
            "DISCOM / grid-origin BESS discharge do not count toward RE / CFE.",
        ],
    )

    add_heading(doc, "17A.7 Annual RE %", 2)
    add_para(
        doc,
        "Annual RE % = (Σ RE_serving_load_t) / (Σ Load_t) × 100",
        italic=True,
    )
    add_para(
        doc,
        "Pass if Annual RE % ≥ annual_re_target_pct. Gap (pp) = max(0, target − actual). "
        "Energy-weighted CFE over the year equals Annual RE % when CFE uses the same RE serving series.",
    )

    add_heading(doc, "17A.8 Hourly CFE % and pass modes", 2)
    add_para(
        doc,
        "CFE_t = Min(Load_t, Solar_t + Wind_t + RE_BESS_discharge_t) / Load_t × 100  "
        "(if Load_t ≈ 0, CFE_t is treated as 100%)",
        italic=True,
    )
    add_table(
        doc,
        ["CFE pass mode", "Pass rule", "Actual used for gap"],
        [
            ["All hours ≥ target", "Every hour CFE_t ≥ target", "Minimum hourly CFE"],
            ["Mean hourly CFE ≥ target", "Unweighted mean of CFE_t ≥ target", "Mean hourly CFE"],
            ["Share of hours ≥ target", "% of hours with CFE_t ≥ target ≥ cfe_hour_share_target_pct", "% hours meeting"],
        ],
    )
    add_para(doc, "CFE analytics also report:", bold=True)
    add_bullets(
        doc,
        [
            "min / mean / median / P95 hourly CFE (min often set by night hours)",
            "% hours ≥ target; hours below target",
            "Longest continuous deficit streak (hours)",
            "Max and mean CFE deficit in percentage points (pp) where below target",
            "Architecture CF % = contracted Solar%+Wind%+BESS% (bill reference — not forced hourly)",
            "Duration curve and hour-of-day / daily / monthly performance blocks",
        ],
    )'''

    if old_17 in t:
        t = t.replace(old_17, new_17, 1)
        print("OK: 17A core")
    else:
        print("MISS: 17A core")

    # 17A.9 KPI rows
    old_kpis = '''            ["Annual solar / wind MWh", "Σ Load_t × Solar%/100  and  Σ Load_t × Wind%/100"],
            ["Grid import MWh / GWh", "Σ Load_t × DISCOM%/100 ; GWh = MWh / 1,000"],
            ["Annual RE %", "Solar% + Wind% + BESS%"],
            ["Hourly CFE (min)", "Architecture RE% (firm) — Pass if ≥ hourly_cfe_target_pct"],
            ["Unserved MWh", "0 on buyer path (firm contracts)"],
            ["BESS (buyer)", "Mix % × Storage tariff; ESO actual = load × BESS%"],
            ["Max grid import MW", "Peak_MW × DISCOM%/100 (feeds demand charge)"],'''
    new_kpis = '''            ["Annual solar / wind MWh", "Σ Solar_t / Σ Wind_t (shapes scaled to mix% × annual load)"],
            ["Grid import MWh / GWh", "Σ Grid_t from dispatch; GWh = MWh / 1,000"],
            ["Annual RE %", "Σ RE serving load / Σ Load × 100 (availability)"],
            ["Hourly CFE (min)", "Min of hourly availability CFE — Pass if ≥ hourly_cfe_target_pct"],
            ["Unserved MWh", "0 commercially; dispatch_unserved_mwh kept for diagnostics"],
            ["BESS (buyer)", "Bill: mix % × Storage tariff; hourly: derived MW/MWh when BESS mix > 0"],
            ["Max grid import MW", "max(Grid_t); demand charge uses Peak × DISCOM%"],'''
    if old_kpis in t:
        t = t.replace(old_kpis, new_kpis, 1)
        print("OK: 17A.9")
    else:
        print("MISS: 17A.9")

    old_bal = '''            "Mix identity: Solar% + Wind% + BESS% + DISCOM% = 100% for selected assets",
            "Hourly supply: Solar_t + Wind_t(+BESS firm RE) + DISCOM_t = Load_t",
            "Annual Solar/Wind/DISCOM MWh = Σ Load_t × mix%/100",
            "Unserved_mwh = 0 (buyer path); plant curtailment / plant SOC identities are out of scope",'''
    new_bal = '''            "Mix identity (bill): Solar% + Wind% + BESS% + DISCOM% = 100% for selected assets",
            "Annual contract: Σ Solar / Σ Wind = Load × mix%",
            "Hourly AC balance: Solar + Wind + Discharge + Grid + Unserved ≈ Load + Charge + Curtailment",
            "Commercial unserved_mwh = 0; charts may still show charge/discharge/SOC when BESS mix > 0",'''
    if old_bal in t:
        t = t.replace(old_bal, new_bal, 1)
        print("OK: 17A.10")
    else:
        print("MISS: 17A.10")

    if t != orig:
        guide.write_text(t, encoding="utf-8")
        print("wrote", guide)
    else:
        print("WARNING: no user guide changes")

    print("Regenerating docx...")
    r = subprocess.run([sys.executable, str(guide)], cwd=str(ROOT))
    print("docx exit", r.returncode)


def patch_in_app() -> None:
    """Replace pageAssumptions + pageMethodology with detailed TOD/availability copy."""
    app = ROOT / "frontend" / "dist" / "assets" / "app.js"
    t = app.read_text(encoding="utf-8")
    start = t.find("function pageAssumptions() {")
    end = t.find("function pageSettings() {")
    if start < 0 or end < 0 or end <= start:
        raise SystemExit(f"app.js markers not found start={start} end={end}")

    new = r'''function pageAssumptions() {
  const rows = state.project.assumptions || [];
  const cfg = state.project?.config || {};
  const blend = cfg.commercial?.cost_blend_basis?.value || "TARGET_POWER_PCT";
  const mixG = fmt(cfg.commercial?.mix_discom_pct?.value, 0);
  const mixS = fmt(cfg.commercial?.mix_solar_pct?.value, 0);
  const mixW = fmt(cfg.commercial?.mix_wind_pct?.value, 0);
  const mixB = fmt(cfg.commercial?.mix_bess_pct?.value, 0);
  const lf1 = fmt(cfg.load?.load_factor_s1_pct?.value ?? cfg.load?.load_factor_pct?.value, 0);
  const lf2 = fmt(cfg.load?.load_factor_s2_pct?.value, 0);
  const lf3 = fmt(cfg.load?.load_factor_s3_pct?.value, 0);
  const lf4 = fmt(cfg.load?.load_factor_s4_pct?.value, 0);
  const storage = fmt(cfg.commercial?.excel_bess_ppa_inr_per_kwh?.value, 4);
  const period = studyPeriodLabel(cfg);
  const year = cfg.general?.calendar_year?.value || "";
  const reT = fmt(cfg.compliance?.annual_re_target_pct?.value, 0);
  const cfeT = fmt(cfg.compliance?.hourly_cfe_target_pct?.value, 0);
  const ef = fmt(cfg.compliance?.grid_emission_factor_tco2_per_mwh?.value, 2);
  const rpoT = fmt(cfg.compliance?.rpo_rco_target_pct?.value, 0);
  const esoT = fmt(cfg.compliance?.eso_target_pct?.value, 1);
  return `
  <div class="panel">
    <div class="section-eyebrow">Assumptions</div>
    <h3 style="margin:0 0 0.5rem">Active project assumptions</h3>
    <p class="muted" style="margin:0 0 0.85rem;font-size:0.88rem;line-height:1.5">
      Live register for <b>Captive</b> and <b>Hybrid</b> (both in Project Setup; one <b>Run Analysis</b> evaluates both).
      <b>Bill</b> = Architecture mix % × tariff stacks.
      <b>Hourly CFE</b> = TOD / availability (solar ≈ 0 at night; wind and BESS can serve).
      <b>DISCOM</b> column = 100% grid savings baseline only.
    </p>
    <div class="kpis" style="margin:0">
      ${kpiCard("Study period", `${period} ${year}`.trim(), { sub: `${currentModelHours()} model hours` })}
      ${kpiCard("Cost blend (bill)", String(blend).replaceAll("_", " "), { sub: "Both bases = Architecture mix %" })}
      ${kpiCard("Active mix G|S|W|B", `${mixG}|${mixS}|${mixW}|${mixB} %`, { sub: "Annual contracts + bill shares" })}
      ${kpiCard("Storage tariff", `₹${storage}/kWh`, { sub: "BESS bill rate; derived storage for CFE" })}
      ${kpiCard("Load factors", `${lf1} / ${lf2} / ${lf3} / ${lf4} %`, { sub: "S1–S4 · headline KPIs use S1" })}
      ${kpiCard("Tracked params", String(rows.length), { sub: "Filter / search in the register" })}
    </div>
  </div>

  <div class="panel">
    <div class="card-head"><div>
      <div class="section-eyebrow">How to read this page</div>
      <h3 style="margin:0">Source tags</h3>
    </div></div>
    <div class="table-wrap"><table class="data">
      <thead><tr><th>Source</th><th>Meaning</th></tr></thead>
      <tbody>
        <tr><td>${badge("CONCEPT_NOTE")}</td><td>Stated in the product concept note (still editable unless locked).</td></tr>
        <tr><td>${badge("DEFAULT_ASSUMPTION")}</td><td>Starter value — replace with your project data before decisions.</td></tr>
        <tr><td>${badge("USER_INPUT")}</td><td>Value you entered or saved from Project Setup.</td></tr>
        <tr><td>${badge("CALCULATED")}</td><td>Derived (peak = IT × PUE, stack totals, derived BESS size).</td></tr>
      </tbody>
    </table></div>
  </div>

  <div class="panel">
    <div class="card-head"><div>
      <div class="section-eyebrow">Input groups</div>
      <h3 style="margin:0">What you configure in Project Setup</h3>
    </div></div>
    <div class="table-wrap"><table class="data">
      <thead><tr><th>Group</th><th>What it controls</th><th>Notes</th></tr></thead>
      <tbody>
        <tr><td><b>General / study period</b></td><td>Start–end month, calendar year, model hours</td><td>Top bar study period drives ${currentModelHours()} h analysis.</td></tr>
        <tr><td><b>Load</b></td><td>IT load, PUE, peak, Seasonal TOD, LF S1–S4</td><td>Peak = IT × PUE. Demand shape only.</td></tr>
        <tr><td><b>Solar / Wind</b></td><td>CF %, sunrise/sunset, variability, profile source</td><td>Hourly shapes; annual MWh from Architecture mix %.</td></tr>
        <tr><td><b>Architecture — Captive</b></td><td>Solar / Wind / BESS flags, mix %, stacks, Storage tariff</td><td>No DISCOM. Mix sum 100%. Bill = mix %.</td></tr>
        <tr><td><b>Architecture — Hybrid</b></td><td>DISCOM + Solar / Wind / BESS flags, mix %, stacks</td><td>DISCOM % = contracted grid share.</td></tr>
        <tr><td><b>Charge stacks</b></td><td>DISCOM / Solar / Wind ₹/kWh line items</td><td>Totals calculated. BESS = <b>Storage tariff</b> only.</td></tr>
        <tr><td><b>Cost blend basis</b></td><td>TARGET_POWER_PCT vs SIMULATED_ENERGY_SHARE</td><td>Both = Architecture mix % for the <b>bill</b>.</td></tr>
        <tr><td><b>Compliance</b></td><td>Annual RE ${reT}%, hourly CFE ${cfeT}%, RPO/RCO ${rpoT}%, ESO ${esoT}%, EF ${ef}</td><td>RE/CFE actuals = availability; RPO = Architecture mix.</td></tr>
        <tr><td><b>Financial</b></td><td>Discount rate, escalations, project life</td><td>NPV of savings vs DISCOM. No plant debt/CAPEX.</td></tr>
      </tbody>
    </table></div>
  </div>

  <div class="panel">
    <div class="card-head"><div>
      <div class="section-eyebrow">Bill vs CFE</div>
      <h3 style="margin:0">Two different uses of mix %</h3>
    </div></div>
    <ul style="margin:0.35rem 0 0;padding-left:1.15rem;font-size:0.9rem;line-height:1.55">
      <li><b>Bill:</b> Architecture mix % × stacked ₹/kWh (Storage tariff × BESS%). Target = Simulated for pricing.</li>
      <li><b>Annual contracts:</b> Σ Solar / Σ Wind MWh = Load × mix% (shapes preserved).</li>
      <li><b>Hourly CFE:</b> Min(Load, Solar_t + Wind_t + RE-BESS_t) / Load × 100 — solar ≈ 0 at night.</li>
      <li><b>Night:</b> CFE from wind and/or BESS discharge — not from pretending solar is still on.</li>
      <li><b>BESS:</b> Mix % on the bill; derived storage shifts day RE to night when BESS mix &gt; 0.</li>
    </ul>
  </div>

  <div class="panel">
    <div class="card-head"><div>
      <div class="section-eyebrow">Results</div>
      <h3 style="margin:0">What drives Dashboard / Economics / Hourly CFE</h3>
    </div></div>
    <ul style="margin:0.35rem 0 0;padding-left:1.15rem;font-size:0.9rem;line-height:1.55">
      <li><b>Both architectures</b> — Captive and Hybrid in one Run Analysis. Tabs only switch detail view.</li>
      <li><b>Blended ₹/kWh</b> — Discom×G% + Solar×S% + Wind×W% + (BESS×Storage tariff if selected).</li>
      <li><b>Target vs Simulated (bill)</b> — Both = Architecture Grid% | RE%.</li>
      <li><b>Annual RE / hourly CFE</b> — Energy-weighted availability (not flat Architecture % every hour).</li>
      <li><b>24×7 CFE Pass</b> — Every hour ≥ target ${cfeT}% (night often sets the minimum).</li>
      <li><b>RPO</b> — Architecture RE mix. <b>ESO</b> — load × BESS mix %.</li>
      <li><b>Carbon</b> — Baseline = load × EF; actual = load × DISCOM% × EF.</li>
      <li><b>Feasibility</b> — Gates on RE/CFE (and Applicable RPO/ESO) — not on plant-profile unserved.</li>
    </ul>
  </div>

  <div class="panel">
    <div class="card-head"><h3 style="margin:0">Assumption register</h3></div>
    <p class="muted" style="margin:0 0 0.65rem;font-size:0.82rem">Search or filter by source. Plant CAPEX / OPEX leftovers are excluded.</p>
    <div class="row"><label>Filter <select id="assump-filter"><option value="">All</option>
      <option>CONCEPT_NOTE</option><option>DEFAULT_ASSUMPTION</option><option>USER_INPUT</option><option>CALCULATED</option>
    </select></label>
    <input id="assump-q" placeholder="Search parameter" style="flex:1;padding:0.4rem;border:1px solid var(--line);border-radius:7px" /></div>
    <div class="table-wrap" style="margin-top:0.8rem"><table>
      <thead><tr><th>Parameter</th><th>Value</th><th>Unit</th><th>Source</th><th>Description</th></tr></thead>
      <tbody id="assump-body">${rows.map(r => `<tr data-src="${r.source}" data-p="${r.parameter}"><td>${r.parameter}</td><td class="mono">${fmtValue(r.value)}</td><td>${r.unit}</td><td>${badge(r.source)}</td><td>${r.description}</td></tr>`).join("")}</tbody>
    </table></div>
  </div>`;
}

function pageMethodology() {
  const hours = currentModelHours();
  const sm = Math.max(1, Math.min(12, Number(state.project?.config?.general?.study_start_month?.value) || 1));
  const em = Math.max(1, Math.min(12, Number(state.project?.config?.general?.study_end_month?.value) || 12));
  const period = studyPeriodLabel(state.project?.config);
  const year = state.project?.config?.general?.calendar_year?.value || "-";
  const studyYr = Number(state.project?.config?.load?.study_years?.value);
  const studyYrTxt = Number.isFinite(studyYr) ? fmt(studyYr, 2) : fmt((em - sm + 1) / 12, 2);
  const ef = Number(state.project?.config?.compliance?.grid_emission_factor_tco2_per_mwh?.value) || 0.82;
  const blend = state.project?.config?.commercial?.cost_blend_basis?.value || "TARGET_POWER_PCT";
  const reT = fmt(state.project?.config?.compliance?.annual_re_target_pct?.value, 0);
  const cfeT = fmt(state.project?.config?.compliance?.hourly_cfe_target_pct?.value, 0);
  const rpoT = fmt(state.project?.config?.compliance?.rpo_rco_target_pct?.value, 0);
  const esoT = fmt(state.project?.config?.compliance?.eso_target_pct?.value, 1);
  return `
  <div class="panel">
    <div class="section-eyebrow">Methodology</div>
    <h3 style="margin:0 0 0.35rem">Model methodology (V${state.project.model_version || "2.0.0"})</h3>
    <p class="muted" style="margin:0;font-size:0.88rem;line-height:1.5">
      Commercial DC <b>buyer</b> path: <b>bill</b> = Architecture mix % × tariffs;
      <b>hourly CFE / charts</b> = TOD availability (solar ≈ 0 at night). Also in <code>MODEL_METHODOLOGY.md</code> and <code>ASSUMPTIONS.md</code>.
    </p>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">1. Product scope</h3>
    <p><b>Viewpoint:</b> Buy power for a data centre (DISCOM + Solar / Wind / BESS PPAs). Outputs: power bill, energy-weighted RE %, 24×7 CFE Pass/Fail, carbon saved, savings / NPV vs 100% DISCOM.</p>
    <p><b>Architectures:</b> Configure <b>Captive</b> and <b>Hybrid</b>. One <b>Run Analysis</b> evaluates both. DISCOM column = 100% grid baseline only.</p>
    <p><b>In scope:</b> Study period, load TOD / LF, Architecture mix %, charge stacks, Storage tariff, Solar/Wind shapes, Compliance, NPV of savings.</p>
    <p><b>Out of scope:</b> Generation-plant CAPEX / OPEX / debt as commercial inputs; treating mix % as flat firm CFE every hour.</p>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">2. Study period &amp; load</h3>
    <p><b>Period:</b> <b>${period} ${year}</b>. Model hours = days × 24 = <b>${hours} h</b>. Study years ≈ <b>${studyYrTxt} yr</b>.</p>
    <p><b>Peak:</b> Peak_MW = IT_load_MW × PUE (calculated).</p>
    <p><b>DC load shape:</b> Seasonal TOD multipliers, then scaled to each LF scenario. Headline KPIs use <b>S1</b>.</p>
    <p><b>Annual load (MWh):</b> Σ hourly load (scenario LF applied).</p>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">3. Architecture mix (bill) vs hourly availability</h3>
    <p><b>Mix %:</b> Selected assets sum to 100%.</p>
    <ul style="margin:0.35rem 0 0.75rem;padding-left:1.15rem;line-height:1.5">
      <li><b>Captive:</b> Solar + Wind + BESS (no DISCOM).</li>
      <li><b>Hybrid:</b> DISCOM + Solar + Wind + BESS.</li>
    </ul>
    <p><b>Bill:</b></p>
    <p class="mono" style="margin:0.35rem 0 0.65rem;font-size:0.9rem">Blended = Discom×(G/100) + Solar×(S/100) + Wind×(W/100) + Storage×(B/100)</p>
    <p><b>Annual contracts + hourly shapes:</b></p>
    <p class="mono" style="margin:0.35rem 0 0.5rem;font-size:0.88rem">Σ Solar = Load × Solar%/100<br>Σ Wind = Load × Wind%/100<br>Hourly: solar ≈ 0 at night; wind/BESS/DISCOM as available</p>
    <p>BESS mix &gt; 0 → derived storage for night shifting. Storage tariff × BESS% remains the bill charge.</p>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">4. Cost blend (bill) — Target = Simulated</h3>
    <p>Current setting: <code>${escHtml(String(blend))}</code></p>
    <div class="table-wrap" style="margin:0.65rem 0"><table class="data">
      <thead><tr><th>Basis</th><th>How shares are set</th><th>When to use</th></tr></thead>
      <tbody>
        <tr><td><b>TARGET_POWER_PCT</b></td><td>Bill uses Architecture mix % (G|S|W|B).</td><td>Default — contracted mix pricing.</td></tr>
        <tr><td><b>SIMULATED_ENERGY_SHARE</b></td><td>Same as Target on the buyer path (Architecture mix %).</td><td>Equals Target for pricing.</td></tr>
      </tbody>
    </table></div>
    <p><b>Economics Target | Simulated:</b> Architecture Grid% | RE% (bill). Hourly CFE is separate (availability).</p>
    <p><b>Demand charge:</b> Peak_MW × DISCOM% × demand ₹/MW-month × 12.</p>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">5. Annual bill, ₹/kWh, savings &amp; NPV</h3>
    <ul style="margin:0;padding-left:1.15rem;line-height:1.55">
      <li><b>Annual energy ₹</b> = annual_load_MWh × blended_₹/kWh × 1000.</li>
      <li><b>Annual bill ₹ Cr</b> = annual energy ₹ / 1e7 (+ demand / fixed / compliance / additional lines if set).</li>
      <li><b>Power cost ₹/kWh</b> = Year-1 total bill ÷ annual load kWh (TOTAL COST OF DELIVERED ENERGY).</li>
      <li><b>Savings vs DISCOM</b> = (100% DISCOM bill − architecture bill) / 1e7.</li>
      <li><b>NPV of savings</b> = PV of yearly savings over project life at discount rate (Year-0 plant CAPEX = 0).</li>
    </ul>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">6. Annual RE %, 24×7 CFE &amp; carbon</h3>
    <p><b>Annual RE % (energy-weighted):</b></p>
    <p class="mono" style="margin:0.35rem 0 0.65rem;font-size:0.88rem">RE% = Σ RE serving load / Σ Load × 100</p>
    <p>Compared to annual RE target <b>${reT}%</b>. RE serving = direct Solar+Wind + RE-origin BESS.</p>
    <p><b>24×7 Hourly CFE:</b></p>
    <p class="mono" style="margin:0.35rem 0 0.65rem;font-size:0.88rem">CFE% = Min(Load, Solar+Wind+RE-BESS) / Load × 100</p>
    <p>Pass = every hour ≥ <b>${cfeT}%</b>. Night: solar ≈ 0; CFE from wind and/or BESS.</p>
    <p><b>Architecture CF %</b> in analytics = contracted Solar%+Wind%+BESS% (bill reference — not forced every hour).</p>
    <p><b>Carbon:</b> baseline = load × ${ef} tCO₂/MWh; actual = load × DISCOM%/100 × EF; saved = baseline − actual.</p>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">7. Compliance</h3>
    <ul style="margin:0;padding-left:1.15rem;line-height:1.55">
      <li><b>Annual RE / Hourly CFE</b> — availability actuals vs targets ${reT}% / ${cfeT}%.</li>
      <li><b>RPO/RCO</b> — Architecture RE mix vs target ${rpoT}%.</li>
      <li><b>ESO</b> — required = load × ${esoT}%; actual = load × BESS mix %.</li>
      <li><b>Feasibility</b> — RE/CFE (/ Applicable RPO/ESO); ignores plant-profile unserved.</li>
    </ul>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">8. Charts</h3>
    <p>Hourly CFE page shows available Load / Solar / Wind / BESS / DISCOM and CFE. Architecture mix sets annual contracts and the bill; CFE is availability each hour.</p>
  </div>

  <div class="panel">
    <h3 style="margin:0 0 0.55rem">9. Workflow</h3>
    <ol style="margin:0;padding-left:1.15rem;line-height:1.55">
      <li>Configure Captive and Hybrid (mix %, stacks, Solar/Wind shapes, Compliance).</li>
      <li>Save Project → Run Analysis.</li>
      <li>Compare Dashboard economics (bill) and CFE Pass (availability).</li>
      <li>Open Hourly CFE for night/day patterns; audit Assumptions / Methodology.</li>
    </ol>
  </div>`;
}

'''
    t = t[:start] + new + t[end:]
    # bump cache
    idx = ROOT / "frontend" / "dist" / "index.html"
    h = idx.read_text(encoding="utf-8")
    h2 = re.sub(r"app\.js\?v=\d+", "app.js?v=144", h)
    idx.write_text(h2, encoding="utf-8")
    app.write_text(t, encoding="utf-8")
    print("app.js Assumptions/Methodology replaced; index v=144")


def main() -> None:
    patch_user_guide()
    patch_in_app()
    # sanity
    ug = (ROOT / "scripts" / "generate_user_guide.py").read_text(encoding="utf-8")
    for s in ["TOD/availability", "solar ≈ 0 at night", "Solar+Wind+RE-BESS", "energy-weighted"]:
        print(("OK" if s in ug else "MISS"), "UG", s)
    app = (ROOT / "frontend" / "dist" / "assets" / "app.js").read_text(encoding="utf-8")
    for s in ["Bill vs CFE", "TOD / availability", "solar ≈ 0 at night"]:
        print(("OK" if s in app else "MISS"), "APP", s)


if __name__ == "__main__":
    main()
