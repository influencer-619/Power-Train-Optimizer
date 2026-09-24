# -*- coding: utf-8 -*-
"""Patch generate_user_guide.py for firm-delivery buyer path, then regenerate docx."""
from pathlib import Path
import subprocess
import sys

GUIDE = Path("scripts/generate_user_guide.py")
t = GUIDE.read_text(encoding="utf-8")
orig = t

replacements = [
    # What's New / Architecture mix
    (
        '''            [
                "Architecture mix % (buyer contracts)",
                "Captive and Hybrid each store Percentage of power (mix_*_pct) for selected assets (sum = 100%). "
                "TARGET_POWER_PCT (default) bills using Architecture %; SIMULATED_ENERGY_SHARE bills using 8760h "
                "dispatch shares after contracts (mix%×annual load for solar/wind energy, assets, load shape, profiles). "
                "Mix % does not scale plant MW — dispatch uses contract energy and profiles.",
            ],''',
        '''            [
                "Architecture mix % (buyer contracts)",
                "Captive and Hybrid each store Percentage of power (mix_*_pct) for selected assets (sum = 100%). "
                "Firm hourly delivery: Solar_t = Load_t × Solar%/100 (same for Wind/DISCOM). "
                "TARGET_POWER_PCT and SIMULATED_ENERGY_SHARE both bill Architecture contracted mix % "
                "(Target = Simulated). No plant MW inventing; plant generation shapes are not used.",
            ],''',
    ),
    (
        '''            [
                "Simulated energy shares (no BESS)",
                "Grid% = grid→load / load × 100; RE% = (Solar+Wind direct to load) / load × 100. "
                "With BESS, dispatch attributes discharge to the Storage tariff share; see Methodology.",
            ],''',
        '''            [
                "Target = Simulated (firm mix)",
                "Grid% = DISCOM mix %; RE% = Solar% + Wind% + BESS%. Both Target and Simulated equal "
                "Architecture contracted mix (firm delivery every hour, including night).",
            ],''',
    ),
    (
        '''            "Buyer economics only: power cost = Architecture % × stacked ₹/kWh tariffs (plus demand/fixed/compliance/additional costs).",
            "Captive and Hybrid are both configured under Project Setup and analysed on every Run Analysis; "
            "DISCOM is computed as GRID-ONLY BASELINE for savings — it is not a selectable architecture.",
            "BESS on Captive/Hybrid uses a single Storage tariff ₹/kWh (excel_bess_ppa_inr_per_kwh) — not battery plant CAPEX.",
            "Synthetic load/solar/wind profiles remain the default; optional PROJECT DATA CSV on Setup steps only.",
            "No external database server — embedded SQLite only.",
            "End users do not need Python, Node.js, Docker or admin rights.",''',
        '''            "Buyer economics only: power cost = Architecture % × stacked ₹/kWh tariffs (plus demand/fixed/compliance/additional costs).",
            "Captive and Hybrid are both configured under Project Setup and analysed on every Run Analysis; "
            "DISCOM is computed as GRID-ONLY BASELINE for savings — it is not a selectable architecture.",
            "Firm hourly delivery — Solar/Wind/DISCOM MW each hour = Load × mix%/100; no plant CF shapes for KPIs/charts.",
            "BESS on Captive/Hybrid uses a single Storage tariff ₹/kWh (excel_bess_ppa_inr_per_kwh) — not battery plant CAPEX/MW.",
            "DC load shape (Seasonal TOD / LF S1–S4) shapes demand only; optional PROJECT DATA CSV is for load, not plant invent.",
            "No external database server — embedded SQLite only.",
            "End users do not need Python, Node.js, Docker or admin rights.",''',
    ),
    (
        '''            "Methodology",
            "In-app summary of bill blend, TARGET_POWER_PCT vs SIMULATED_ENERGY_SHARE, dispatch, RE%/CFE, carbon, "
            "savings NPV, and Captive vs Hybrid equal analysis.",''',
        '''            "Methodology",
            "In-app summary of firm delivery, bill blend (Target = Simulated), Annual RE / 24×7 CFE, carbon, "
            "savings NPV, and Captive vs Hybrid equal analysis.",''',
    ),
    # Solar / Wind setup notes
    (
        '''        "When profile_source = SYNTHETIC, generation is zero at night, peaks near peak_generation_hour, and is scaled to the target CF. "
        "PROJECT DATA replaces the synthetic series with your imported MW profile (scaled/capacities still apply as configured).",''',
        '''        "Commercial buyer path: Solar delivery is firm (Load × Solar% every hour) — plant diurnal CF curves are not used "
        "for KPIs, CFE, or charts. Legacy synthetic/PROJECT DATA plant-shape fields are out of scope for the buyer model.",''',
    ),
    (
        '''        "When profile_source = SYNTHETIC, wind uses monthly factors and deterministic variability seeded by general.random_seed. "
        "PROJECT DATA uses the imported hourly MW series.",''',
        '''        "Commercial buyer path: Wind delivery is firm (Load × Wind% every hour) — plant wind CF curves are not used "
        "for KPIs, CFE, or charts.",''',
    ),
    (
        '''        "Buyer BESS contract: Storage tariff ₹/kWh, optional dispatch parameters for hourly CFE (no plant CAPEX/OPEX in UI).",''',
        '''        "Buyer BESS contract: Storage tariff ₹/kWh and mix % only (counts in RE/CFE). No BESS plant MW/MWh/SOC.",''',
    ),
    (
        '''        "Controls which commercial cost stack is applied, which assets are included, Percentage of power "
        "(mix_*_pct — energy share targets, selected assets must sum to 100; does not scale MW), "
        "cost_blend_basis (TARGET_POWER_PCT vs SIMULATED_ENERGY_SHARE for CAPTIVE Excel blend), "
        "ownership/allocation metadata, and network-charge flags.",''',
        '''        "Controls which commercial cost stack is applied, which assets are included, Percentage of power "
        "(mix_*_pct — contracted energy shares, selected assets must sum to 100; firm hourly delivery), "
        "cost_blend_basis (TARGET_POWER_PCT and SIMULATED_ENERGY_SHARE both = Architecture mix % on the buyer path), "
        "ownership/allocation metadata, and network-charge flags.",''',
    ),
    # Mix detailed section
    (
        '''        "For each architecture (Captive and Hybrid separately), set Percentage of power for each selected asset. "
        "These percentages are buyer contract shares for the tariff-stack bill (Architecture %). "
        "They define contract energy for dispatch (mix% × annual load for solar/wind) but do not represent plant MW investment.",''',
        '''        "For each architecture (Captive and Hybrid separately), set Percentage of power for each selected asset. "
        "These percentages are buyer contract shares for the tariff-stack bill and for firm hourly delivery: "
        "every hour Solar_MW = Load × Solar%/100 (same pattern for Wind and DISCOM). "
        "They do not represent plant MW investment; plant generation shapes are not used.",''',
    ),
    (
        '''            "After a run, Economics shows Target % (Architecture %) vs Simulated energy share from 8760 dispatch.",
            "commercial.cost_blend_basis: TARGET_POWER_PCT = Architecture %; SIMULATED_ENERGY_SHARE = 8760h "
            "served-energy shares after Project Setup contracts (selected assets, load shape, profiles).",''',
        '''            "After a run, Economics shows Target % and Simulated % — both equal Architecture contracted mix "
            "(Grid% = DISCOM%; RE% = Solar%+Wind%+BESS%).",
            "commercial.cost_blend_basis: TARGET_POWER_PCT and SIMULATED_ENERGY_SHARE both price Architecture "
            "contracted mix % × stacked rates (Target = Simulated on the buyer path).",''',
    ),
    (
        '''            "8760 dispatch uses contract energy derived from mix % × annual load (and profiles) for solar/wind; "
            "grid limit from Setup; BESS for hourly balancing and CFE.",
            "Year-1 energy ₹ = Load × (Discom×G% + Solar×S% + Wind×W% + Storage×B%) using TARGET_POWER_PCT or "
            "SIMULATED_ENERGY_SHARE.",
            "BESS on Captive/Hybrid: single Storage tariff ₹/kWh (excel_bess_ppa_inr_per_kwh) — not plant CAPEX.",
            "Config keys: commercial.mix_discom_pct, mix_solar_pct, mix_wind_pct, mix_bess_pct "
            "(each 0–100; selected assets must sum to 100)",''',
        '''            "Firm hourly delivery: Solar_t / Wind_t / DISCOM_t = Load_t × mix%/100 every study hour "
            "(including night — solar share does not drop to zero). BESS% billed at Storage tariff; no plant SOC.",
            "Year-1 energy ₹ = Load × (Discom×G% + Solar×S% + Wind×W% + Storage×B%) — both cost-blend bases "
            "use Architecture contracted mix %.",
            "BESS on Captive/Hybrid: single Storage tariff ₹/kWh (excel_bess_ppa_inr_per_kwh) — not plant CAPEX/MW.",
            "Config keys: commercial.mix_discom_pct, mix_solar_pct, mix_wind_pct, mix_bess_pct "
            "(each 0–100; selected assets must sum to 100)",''',
    ),
    (
        '''            "CAPTIVE with Solar 50% + DISCOM 50%: Excel blend uses those shares; simulation still runs full "
            "solar and grid capacities from Setup.",
            "Hybrid with Wind unchecked: DISCOM + Solar + BESS % must sum to 100 (e.g. 25 / 50 / 25).",
            "Without BESS: Simulated Grid% ≈ grid→load/load; Simulated RE% ≈ (Solar+Wind)→load/load.",''',
        '''            "CAPTIVE with Solar 50% + Wind 30% + BESS 20%: bill and firm CFE use those shares every hour.",
            "Hybrid with Wind unchecked: DISCOM + Solar + BESS % must sum to 100 (e.g. 25 / 50 / 25).",
            "Target Grid% | RE% always equals Simulated Grid% | RE% (Architecture mix).",''',
    ),
    (
        '''        "Captive-style supply contracts: Solar, Wind, BESS (Storage tariff), optional DISCOM backup share. "
        "Stacked ₹/kWh lines mirror Excel Captive/OA charge components for each asset. "
        "Ownership/allocation metadata is stored for reporting — the tool does not certify captive legal qualification. "
        "8760 dispatch drives Annual RE %, Hourly CFE, and (when cost_blend_basis = SIMULATED_ENERGY_SHARE) bill shares.",''',
        '''        "Captive-style supply contracts: Solar, Wind, BESS (Storage tariff), optional DISCOM backup share. "
        "Stacked ₹/kWh lines mirror Excel Captive/OA charge components for each asset. "
        "Ownership/allocation metadata is stored for reporting — the tool does not certify captive legal qualification. "
        "Annual RE %, Hourly CFE, and bill shares all use Architecture contracted mix % (firm delivery).",''',
    ),
    # CFE section
    (
        '''        [
            "Annual RE % = sum of renewable energy serving load / total load energy × 100 (energy-based, not capacity-based).",
            "In this model, energy-weighted CFE ≡ Annual RE % (same numerator/denominator).",
            "Hourly CFE % = renewable energy serving load in that hour / load in that hour × 100, with BESS discharge credited by tracked RE-origin share.",
            "They are related but not the same as the pass-mode metric — do not treat min hourly CFE and annual RE as interchangeable.",
            "CFE pass modes: All hours >= target | Mean hourly CFE >= target | Share of hours >= target.",
            "Default pass mode All hours >= target is a strict 24×7 rule. The demo 250 MW plant often Fails "
            "Annual RE (≈81% vs 90% target) and Hourly CFE (night hours drop well below 90%) until BESS/wind "
            "is increased or targets/pass mode are relaxed under Project Setup → Compliance.",
            "Dashboard CFE Pass Mode card shows: mode, target, min hour, % hours ≥ target, longest continuous deficit streak (hours), max deficit (pp).",
            "Dashboard Compliance Status shows actual vs target and a short “Why Fail?” note when status is Fail.",
            "CFE heatmap uses an absolute 0–100% colour scale (coral → amber → teal/green) so low night CFE "
            "reads clearly; the compliance target is marked on the colour bar.",
        ],''',
        '''        [
            "Annual RE % = Solar% + Wind% + BESS% (Architecture contracted mix — same every hour).",
            "Hourly CFE % = Min(Load, Load × (Solar%+Wind%+BESS%)/100) / Load × 100. "
            "With firm mix this equals Solar%+Wind%+BESS% every hour, including night (solar share does not go to zero).",
            "Energy-weighted CFE ≡ Annual RE % when mix is firm (min = mean = RE%).",
            "CFE pass modes: All hours >= target | Mean hourly CFE >= target | Share of hours >= target.",
            "Default pass mode All hours >= target is a strict 24×7 rule: Pass iff Architecture RE mix ≥ hourly CFE target "
            "(flat firm series). Fail means raise Solar/Wind/BESS mix % or lower the target under Project Setup → Compliance — "
            "not “add plant MW” or “fix night solar shapes”.",
            "Dashboard CFE Pass Mode card shows: mode, target, min hour, % hours ≥ target, longest continuous deficit streak (hours), max deficit (pp).",
            "Dashboard Compliance Status shows actual vs target and a short “Why Fail?” note when status is Fail.",
            "CFE heatmap uses an absolute 0–100% colour scale; with firm mix the heatmap is flat at the Architecture RE %.",
        ],''',
    ),
    # Engine does
    (
        '''        [
            "Resolve profiles: SYNTHETIC generator or PROJECT DATA import (error if PROJECT DATA missing/invalid).",
            "For each load-factor scenario (S1–S4), build 8,760-hour load/solar/wind series and dispatch hourly flows.",
            "Validate power balance and finite values — MODEL ERROR on hard failure.",
            "Run Captive and Hybrid commercial profiles plus DISCOM baseline; store SHA-256 config fingerprint.",
            "Compute KPIs, CFE analytics, compliance, feasibility, tariff-stack economics and savings vs DISCOM.",
        ],''',
        '''        [
            "Build DC load for each LF scenario (S1–S4) from Seasonal TOD / study period (demand shape only).",
            "Apply Architecture firm contracts: Solar_t = Load_t × Solar%/100 (same for Wind/DISCOM); BESS% on bill + RE/CFE.",
            "Validate finite values and energy identities — MODEL ERROR on hard failure. Unserved MWh = 0 on the buyer path.",
            "Run Captive and Hybrid commercial profiles plus DISCOM baseline; store SHA-256 config fingerprint.",
            "Compute KPIs, firm CFE analytics, compliance, feasibility, tariff-stack economics and savings vs DISCOM.",
        ],''',
    ),
    # KPI cards
    (
        '''            ["Annual RE", "Year energy RE serving load / total load"],
            ["Hourly CFE (min)", "Minimum hourly CFE across the year; subtext shows CFE pass mode Pass/Fail"],
            ["Grid Import", "Annual grid energy in GWh"],
            ["BESS", "Configured power MW / energy MWh and utilization"],
            ["Curtailment", "Curtailed RE as % of RE generation"],
            ["Cost ₹/kWh", "TOTAL COST OF DELIVERED ENERGY (annualised cost / load energy)"],
            ["NPV ₹ Cr", "Present value of bill savings vs DISCOM baseline (Captive/Hybrid)"],
            ["Savings vs DISCOM", "Year-1 bill delta vs GRID-ONLY BASELINE (₹ Cr)"],
            ["LF scenario", "Headline row uses S1; other scenarios in run metadata / exports"],''',
        '''            ["Annual RE", "Architecture Solar% + Wind% + BESS%"],
            ["Hourly CFE (min)", "Min hourly firm CFE (= Architecture RE% with firm mix); Pass/Fail vs target"],
            ["Grid Import", "Annual contracted DISCOM energy (Load × DISCOM%) in GWh"],
            ["BESS", "Contracted BESS mix % × Storage tariff (no plant MW/MWh on buyer path)"],
            ["Cost ₹/kWh", "TOTAL COST OF DELIVERED ENERGY (Year-1 bill ÷ load kWh)"],
            ["NPV ₹ Cr", "Present value of bill savings vs DISCOM baseline (Captive/Hybrid)"],
            ["Savings vs DISCOM", "Year-1 bill delta vs GRID-ONLY BASELINE (₹ Cr)"],
            ["LF scenario", "Headline row uses S1; other scenarios in run metadata / exports"],''',
    ),
    # Feasibility
    (
        '''        "Every simulation returns a unified feasibility object per architecture. The Dashboard Feasibility card "
        "summarises whether enabled RE/CFE/unserved checks pass — it does not select Captive vs Hybrid.",''',
        '''        "Every simulation returns a unified feasibility object per architecture. The Dashboard Feasibility card "
        "summarises whether enabled RE/CFE (and Applicable RPO/ESO) checks pass — it does not select Captive vs Hybrid. "
        "Plant-profile unserved energy is not a buyer-path gate (unserved_mwh = 0 with firm contracts).",''',
    ),
    (
        '''            ["NOT FEASIBLE", "RE target miss, CFE pass-mode fail, and/or unserved energy > 0 (among other binding issues)."],''',
        '''            ["NOT FEASIBLE", "RE target miss and/or CFE pass-mode fail (Architecture mix below target), or Applicable RPO/ESO fail."],''',
    ),
    (
        '''        "When not feasible, the card lists binding items such as ANNUAL_RE, HOURLY_CFE, UNSERVED, RPO, RCO, ESO "
        "with actual vs target and suggested remedies (increase BESS/wind, relax target/pass mode, raise grid, etc.). "
        "An approximate extra BESS MWh hint may appear for CFE deficits — it is a heuristic, not a guarantee.",''',
        '''        "When not feasible, the card lists binding items such as ANNUAL_RE, HOURLY_CFE, RPO, RCO, ESO "
        "with actual vs target. Remedies: raise Solar/Wind/BESS mix %, or relax the target / pass mode under "
        "Project Setup → Compliance — not plant MW sizing.",''',
    ),
]

n_ok = 0
for old, new in replacements:
    if old not in t:
        print("MISS:", old[:80].replace("\n", " "))
        continue
    t = t.replace(old, new, 1)
    n_ok += 1

print(f"replacements applied: {n_ok}/{len(replacements)}")

# Large block: Assumptions §15.1–15.2
old_15 = '''    add_heading(doc, "15.1 Assumptions register", 2)
    add_para(
        doc,
        "Assumptions is the searchable register of parameters that drive Captive and Hybrid on the commercial "
        "buyer path. Generation-plant CAPEX / OPEX, plant MW capacities, plant financing, and optimization "
        "leftovers are hidden by design.",
    )
    add_para(doc, "Source tags", bold=True)
    add_table(
        doc,
        ["Source", "Meaning"],
        [
            ["CONCEPT_NOTE", "Stated in the product concept note (still editable unless locked)."],
            ["DEFAULT_ASSUMPTION", "Starter value — replace with your project data before decisions."],
            ["USER_INPUT", "Value you entered or saved from Project Setup."],
            ["CALCULATED", "Derived by the model (e.g. peak = IT × PUE, stack totals)."],
        ],
    )
    add_para(doc, "Input groups you configure", bold=True)
    add_table(
        doc,
        ["Group", "What it controls", "Notes"],
        [
            [
                "General / study period",
                "Start–end month, calendar year, model hours",
                "Top bar study period drives analysis hours.",
            ],
            [
                "Load",
                "IT load, PUE, peak, Seasonal TOD, LF S1–S4",
                "Peak = IT × PUE. Four LF scenarios; headline KPIs use S1.",
            ],
            [
                "Architecture — Captive",
                "Solar / Wind / BESS flags, mix %, Solar/Wind stacks, Storage tariff",
                "No DISCOM. Selected mix % must sum to 100%.",
            ],
            [
                "Architecture — Hybrid",
                "DISCOM + Solar / Wind / BESS flags, mix %, all stacks",
                "DISCOM share is procurement %; DISCOM column elsewhere is savings baseline.",
            ],
            [
                "Charge stacks",
                "DISCOM / Solar / Wind ₹/kWh line items",
                "Totals calculated. BESS on Captive/Hybrid = Storage tariff only.",
            ],
            [
                "Cost blend basis",
                "TARGET_POWER_PCT vs SIMULATED_ENERGY_SHARE",
                "TARGET prices Architecture %. SIMULATED prices served shares after Setup contracts.",
            ],
            [
                "Compliance",
                "Annual RE, hourly CFE, RPO/RCO, ESO, grid EF",
                "Project Setup → Compliance (not a separate Analysis page).",
            ],
            [
                "Financial (results)",
                "Discount rate, electricity / RE escalation, project life",
                "NPV of savings vs DISCOM. No generation-plant debt / CAPEX path.",
            ],
        ],
    )
    add_para(doc, "What drives Dashboard / Economics / Hourly CFE", bold=True)
    add_bullets(
        doc,
        [
            "Both architectures — Captive and Hybrid are analysed in one Run Analysis. Tabs only switch detail view.",
            "Blended ₹/kWh — Discom×G% + Solar×S% + Wind×W% + (BESS×Storage tariff if BESS selected).",
            "Target vs Simulated — Target = Architecture %. Simulated = 8760h served energy after Setup mix × load contracts.",
            "CFE / carbon — Mix RE% and 24×7 hourly CFE; carbon saved vs 100% DISCOM × grid EF.",
            "Hidden from the register — generation CAPEX / OPEX, plant MW, plant financing, Optimization leftovers.",
        ],
    )

    add_heading(doc, "15.2 Methodology (detailed — matches in-app page)", 2)
    add_para(
        doc,
        "Methodology documents commercial buyer calculation rules. Summary of sections (full formulas also in §17A):",
    )
    add_numbered(
        doc,
        [
            "Product scope — Captive + Hybrid equal analysis; DISCOM = savings baseline; no recommendation / Status row; "
            "no plant CAPEX/OPEX UI.",
            "Study period & load — Peak = IT × PUE; Seasonal TOD; LF S1–S4 (headline = S1); annual load = Σ hourly MWh.",
            "Architecture mix & tariffs — Selected mix % sum to 100%; DISCOM/Solar/Wind = stack totals; "
            "BESS = Storage tariff ₹/kWh on Captive/Hybrid.",
            "Cost blend — TARGET_POWER_PCT uses Architecture %; SIMULATED_ENERGY_SHARE applies Setup energy contracts "
            "(Solar/Wind annual = mix % × load, shape preserved; BESS off → 0 MW; DISCOM → grid cap = peak), "
            "then prices served G|S|W|B. Without BESS: Grid% = grid→load/load×100; RE% = (Solar+Wind)→load/load×100.",
            "Annual bill / ₹/kWh / savings / NPV — Bill = load × blended × 1000; ₹/kWh = Year-1 bill ÷ load kWh; "
            "savings vs 100% DISCOM; NPV of savings at discount rate (Year-0 generation CAPEX = 0).",
            "Dashboard / Economics / Hourly CFE — Compare table + CAPTIVE/HYBRID detail tabs.",
            "CFE & carbon — Hourly CFE% = Min(Load, Solar+Wind+CF-BESS)/Load×100; carbon saved = baseline − actual.",
            "Compliance — RPO/RCO single target, ESO single target, hourly CFE pass rule, grid EF.",
            "Workflow — Setup both architectures → Save → Run Analysis → compare → detail tabs → Assumptions audit.",
        ],
    )'''

new_15 = '''    add_heading(doc, "15.1 Assumptions register", 2)
    add_para(
        doc,
        "Assumptions is the searchable register of parameters that drive Captive and Hybrid on the commercial "
        "buyer path. The data centre is an energy consumer: Solar / Wind / BESS / DISCOM are contracted "
        "Architecture mix % at fixed ₹/kWh with firm hourly delivery (Load × mix %). Generation-plant CAPEX / OPEX, "
        "plant MW, plant CF shapes, plant financing, and optimization leftovers are hidden by design.",
    )
    add_para(doc, "Source tags", bold=True)
    add_table(
        doc,
        ["Source", "Meaning"],
        [
            ["CONCEPT_NOTE", "Stated in the product concept note (still editable unless locked)."],
            ["DEFAULT_ASSUMPTION", "Starter value — replace with your project data before decisions."],
            ["USER_INPUT", "Value you entered or saved from Project Setup."],
            ["CALCULATED", "Derived by the model (e.g. peak = IT × PUE, stack totals)."],
        ],
    )
    add_para(doc, "Input groups you configure", bold=True)
    add_table(
        doc,
        ["Group", "What it controls", "Notes"],
        [
            [
                "General / study period",
                "Start–end month, calendar year, model hours",
                "Top bar study period drives analysis hours.",
            ],
            [
                "Load",
                "IT load, PUE, peak, Seasonal TOD, LF S1–S4",
                "Peak = IT × PUE. Demand shape only — not Solar/Wind plant CF. KPIs use S1.",
            ],
            [
                "Architecture — Captive",
                "Solar / Wind / BESS flags, mix %, Solar/Wind stacks, Storage tariff",
                "No DISCOM. Selected mix % must sum to 100%. Firm hourly delivery.",
            ],
            [
                "Architecture — Hybrid",
                "DISCOM + Solar / Wind / BESS flags, mix %, all stacks",
                "DISCOM share is contracted grid %. Baseline savings use 100% DISCOM elsewhere.",
            ],
            [
                "Charge stacks",
                "DISCOM / Solar / Wind ₹/kWh line items",
                "Totals calculated. BESS on Captive/Hybrid = Storage tariff only.",
            ],
            [
                "Cost blend basis",
                "TARGET_POWER_PCT vs SIMULATED_ENERGY_SHARE",
                "Both = Architecture contracted mix % (Target = Simulated).",
            ],
            [
                "Compliance",
                "Annual RE, hourly CFE, RPO/RCO, ESO, grid EF",
                "Actuals use Architecture mix (firm). Project Setup → Compliance.",
            ],
            [
                "Financial (results)",
                "Discount rate, electricity / RE escalation, project life",
                "NPV of savings vs DISCOM. No generation-plant debt / CAPEX path.",
            ],
        ],
    )
    add_para(doc, "What “no plant shapes” means", bold=True)
    add_bullets(
        doc,
        [
            "Every hour: Solar_MW = Load × Solar%/100; Wind_MW = Load × Wind%/100; DISCOM_MW = Load × DISCOM%/100.",
            "BESS: Mix % × Storage tariff on the bill; BESS% counts in RE/CFE. No BESS plant MW/MWh or SOC.",
            "Night: Solar contract share continues (does not drop to zero). CFE stays at Solar%+Wind%+BESS%.",
            "Removed: Plant CF curves, plant curtailment/SOC charts, plant CAPEX/OPEX/MW fields.",
        ],
    )
    add_para(doc, "What drives Dashboard / Economics / Hourly CFE", bold=True)
    add_bullets(
        doc,
        [
            "Both architectures — Captive and Hybrid are analysed in one Run Analysis. Tabs only switch detail view.",
            "Blended ₹/kWh — Discom×G% + Solar×S% + Wind×W% + (BESS×Storage tariff if BESS selected).",
            "Target vs Simulated — Both = Architecture contracted mix % (Grid% | RE%).",
            "Annual RE / CFE / RPO — Solar% + Wind% + BESS% (firm). 24×7 Pass = every hour ≥ target (flat = RE%).",
            "ESO — Required = load × ESO%; actual = load × BESS mix %. Carbon: baseline = load×EF; actual = load×DISCOM%×EF.",
            "Feasibility — Gates on RE/CFE (and Applicable RPO/ESO) — not on plant-profile unserved.",
            "Hidden from the register — generation CAPEX / OPEX, plant MW, plant financing, Optimization leftovers.",
        ],
    )

    add_heading(doc, "15.2 Methodology (detailed — matches in-app page)", 2)
    add_para(
        doc,
        "Methodology documents commercial buyer calculation rules with firm hourly delivery. "
        "Summary of sections (full formulas also in §17A and MODEL_METHODOLOGY.md):",
    )
    add_numbered(
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

if old_15 not in t:
    print("MISS: section 15 block")
else:
    t = t.replace(old_15, new_15, 1)
    print("OK: section 15")

# Replace 17A.3–17A.8 firm-delivery core
old_17a_core = '''    add_heading(doc, "17A.3 Synthetic solar profile", 2)
    add_bullets(
        doc,
        [
            "Outside [sunrise_hour, sunset_hour] generation = 0.",
            "Inside daylight: a Gaussian-like diurnal curve peaked at peak_generation_hour, "
            "× monthly seasonal_1…12 factors, × deterministic noise of amplitude hourly_variability (seeded).",
            "Scaled so annual energy / (capacity_mw × 8760) ≈ capacity_factor_pct / 100.",
            "Clipped so solar_t ≤ capacity_mw every hour.",
            "PROJECT DATA uses the imported MW series instead.",
        ],
    )

    add_heading(doc, "17A.4 Synthetic wind profile", 2)
    add_bullets(
        doc,
        [
            "Monthly month_1…12 factors × mild diurnal shape × deterministic hourly_variability noise.",
            "Scaled to capacity_factor_pct and clipped to capacity_mw.",
            "PROJECT DATA uses the imported MW series instead.",
        ],
    )

    add_heading(doc, "17A.5 Hourly dispatch (rule-based — default)", 2)
    add_para(
        doc,
        "Each hour t the engine follows fixed dispatch priorities:",
    )
    add_para(
        doc,
        "BESS modelling note: Charge and discharge are each limited by bess.power_mw. One-way efficiencies "
        "bess.charge_efficiency_pct and bess.discharge_efficiency_pct (default 95%) apply: "
        "SOC_t = SOC_(t−1) + η_c·Charge_t − Discharge_t/η_d. Round-trip ≈ η_c × η_d. "
        "Separate max charge/discharge power inputs are not used (power_mw caps both).",
    )
    add_numbered(
        doc,
        [
            "RE serves load first: DirectRE_t = min(Solar_t + Wind_t, Load_t). Solar/wind shares of DirectRE are proportional to their generation.",
            "Excess RE charges BESS (if capacity and SOC headroom allow), limited by BESS power rating and η_c.",
            "Any RE still left is curtailed.",
            "If load remains, BESS discharges (limited by power rating, SOC above min, and η_d).",
            "Grid import serves any residual, ≤ max_import_mw × (availability_pct/100).",
            "If still short → Unserved_t > 0.",
            "Optional: if allow_grid_charge and load is fully met, residual grid headroom may charge BESS.",
        ],
    )
    add_para(doc, "State of charge (MWh):", bold=True)
    add_para(
        doc,
        "SOC_t = SOC_(t−1) + η_c·Charge_t − Discharge_t/η_d, "
        "with SOC_min = min_soc_pct/100 × energy_mwh and SOC_max = max_soc_pct/100 × energy_mwh. "
        "Charge and discharge power are both capped at bess.power_mw.",
    )
    add_para(doc, "User-editable BESS technical inputs (Setup → BESS):", bold=True)
    add_table(
        doc,
        ["Parameter", "Role"],
        [
            ["power_mw", "Power rating — max charge MW and max discharge MW in every hour"],
            ["energy_mwh", "Energy capacity used with SOC % limits"],
            ["charge_efficiency_pct", "One-way charge efficiency η_c (default 95%)"],
            ["discharge_efficiency_pct", "One-way discharge efficiency η_d (default 95%)"],
            ["initial_soc_pct / min_soc_pct / max_soc_pct", "Starting SOC and operating window"],
            ["calendar_degradation_pct / cycle_degradation_pct", "Multi-year fade (financial / availability framing)"],
            ["capex / opex / life / replacement_*", "Economics of the battery"],
            ["allow_grid_charge", "If true, grid may charge BESS after load is met"],
        ],
        col_widths=[2.2, 4.3],
    )
    add_para(doc, "Removed from BESS (no longer in UI or model inputs):", bold=True)
    add_bullets(
        doc,
        [
            "round_trip_efficiency_pct — derived as η_c × η_d in KPIs; not a separate editable input.",
            "max_charge_mw / max_discharge_mw — replaced by power_mw for both directions.",
        ],
    )
    add_para(doc, "Hourly AC power balance (validated):", bold=True)
    add_para(
        doc,
        "Solar_t + Wind_t + Discharge_t + Grid_t + Unserved_t  =  Load_t + Charge_t + Curtailment_t",
        italic=True,
    )
    add_para(
        doc,
        "Optional LP Dispatch mode solves weekly blocks with SciPy HiGHS (minimise grid cost + small curtailment penalty) "
        "when selected; the default product path is rule-based.",
    )

    add_heading(doc, "17A.6 Renewable serving load & origin tracking", 2)
    add_bullets(
        doc,
        [
            "RE_serving_load_t = DirectRE_t + RE_origin_discharge_t  (MW in hour t → MWh for that hour).",
            "BESS stores separate origin buckets: solar-origin, wind-origin, grid-origin SOC.",
            "Charge from solar/wind increases the matching RE bucket by η_c·charge; grid charge increases grid-origin by η_c·charge.",
            "Discharge depletes origin buckets in proportion to their share of stored energy.",
            "Grid-origin discharge does NOT count toward RE_serving_load / CFE.",
            "re_origin_stored_share_pct ≈ Σ charge_from_RE / Σ total_charge × 100 (used in ESO checks).",
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
        "This energy-weighted CFE over the year equals Annual RE % in this model.",
    )

    add_heading(doc, "17A.8 Hourly CFE % and pass modes", 2)
    add_para(
        doc,
        "CFE_t = (RE_serving_load_t / Load_t) × 100   (if Load_t ≈ 0, CFE_t is treated as 100%)",
        italic=True,
    )
    add_table(
        doc,
        ["CFE pass mode", "Pass rule", "Actual used for gap"],
        [
            ["All hours ≥ target", "Every hour CFE_t ≥ target (hours meeting ≈ 100%)", "Minimum hourly CFE"],
            ["Mean hourly CFE ≥ target", "Unweighted mean of CFE_t ≥ target", "Mean hourly CFE"],
            ["Share of hours ≥ target", "% of hours with CFE_t ≥ target ≥ cfe_hour_share_target_pct", "% hours meeting"],
        ],
    )
    add_para(doc, "CFE analytics also report:", bold=True)
    add_bullets(
        doc,
        [
            "min / mean / median / P95 hourly CFE",
            "% hours ≥ target; hours below target",
            "Longest continuous deficit streak (hours)",
            "Max and mean CFE deficit in percentage points (pp) where below target",
            "Duration curve (CFE sorted high→low vs % of hours)",
        ],
    )'''

new_17a_core = '''    add_heading(doc, "17A.3 Firm Solar / Wind / DISCOM delivery (buyer path)", 2)
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

if old_17a_core not in t:
    print("MISS: 17A core")
else:
    t = t.replace(old_17a_core, new_17a_core, 1)
    print("OK: 17A core")

# 17A.9 KPIs + 17A.11 compliance + 17A.14 blend
old_17a9 = '''            ["Annual solar / wind MWh", "Σ Solar_t / Σ Wind_t over 8,760 hours"],
            ["Grid import MWh / GWh", "Σ Grid_t ; GWh = MWh / 1,000"],
            ["Curtailment %", "Σ Curtail_t / max(Σ Solar_t + Σ Wind_t, ε) × 100"],
            ["Unserved MWh", "Σ Unserved_t  (must be ≈ 0 for feasibility when enforce_no_unserved)"],
            ["BESS duration (h)", "energy_mwh / power_mw"],
            ["BESS cycles", "Σ Discharge_t / energy_mwh"],
            ["BESS utilization %", "min(100, cycles / 365 × 100) — vs 1 full cycle/day"],
            ["BESS losses MWh", "Σ charge×(1−η_c) + Σ discharge×(1/η_d − 1)"],
            ["Max grid import MW", "max(Grid_t) over the year (feeds demand charge)"],'''

new_17a9 = '''            ["Annual solar / wind MWh", "Σ Load_t × Solar%/100  and  Σ Load_t × Wind%/100"],
            ["Grid import MWh / GWh", "Σ Load_t × DISCOM%/100 ; GWh = MWh / 1,000"],
            ["Annual RE %", "Solar% + Wind% + BESS%"],
            ["Hourly CFE (min)", "Architecture RE% (firm) — Pass if ≥ hourly_cfe_target_pct"],
            ["Unserved MWh", "0 on buyer path (firm contracts)"],
            ["BESS (buyer)", "Mix % × Storage tariff; ESO actual = load × BESS%"],
            ["Max grid import MW", "Peak_MW × DISCOM%/100 (feeds demand charge)"],'''

if old_17a9 not in t:
    print("MISS: 17A.9")
else:
    t = t.replace(old_17a9, new_17a9, 1)
    print("OK: 17A.9")

old_comp = '''            "RPO: for each bucket (solar/wind/hydro/other), required_mwh = Load_MWh × target_pct/100. "
            "Gap = max(0, required − actual_generation_bucket). "
            "If Applicable: cost = Σ gaps_mwh × 1,000 × rpo_buyout_inr_per_kwh.",
            "RCO: compares Annual RE % to rco_target_pct. "
            "Gap energy ≈ max(0, Load×target/100 − RE_serving_load). "
            "Cost uses REC or buyout ₹/kWh when Applicable.",
            "ESO: required_storage_mwh = Load_MWh × active_year_target_pct/100. "
            "Actual storage energy = Σ BESS charge. Also requires RE-origin share of stored energy ≥ eso_re_origin_min_pct "
            "(default 85% from concept note). Buyout on shortfall / origin failure when Applicable.",
            "total_compliance_cost_inr = RPO cost + RCO cost + ESO cost (year-1 stack).",'''

new_comp = '''            "RPO/RCO (single integrated target): actual = Architecture RE % (Solar%+Wind%+BESS%). "
            "Required MWh = Load_MWh × rpo_rco_target_pct/100. Gap = max(0, required − Load×RE%/100). "
            "Buyout cost when Applicable uses configured ₹/kWh.",
            "ESO: required_storage_mwh = Load_MWh × eso_target_pct/100. "
            "Actual = Load_MWh × BESS mix %/100. Contracted BESS treated as 100% RE-origin on the buyer path. "
            "Buyout on shortfall when Applicable.",
            "total_compliance_cost_inr = RPO/RCO cost + ESO cost (year-1 stack).",'''

if old_comp not in t:
    print("MISS: compliance")
else:
    t = t.replace(old_comp, new_comp, 1)
    print("OK: compliance")

old_blend = '''            "TARGET_POWER_PCT: Grid/Solar/Wind/BESS shares = Architecture mix_*_pct for selected assets.",
            "SIMULATED_ENERGY_SHARE — before dispatch, apply Project Setup energy contracts: "
            "Solar annual MWh = load × Solar%/100 (shape kept); Wind similarly; unselected assets = 0; "
            "BESS off → 0 MW; if DISCOM included, grid import cap = peak load.",
            "SIMULATED — after dispatch (no BESS): Grid% = (grid→load)/load×100; "
            "RE% = (Solar→load + Wind→load)/load×100.",
            "SIMULATED — with BESS: bill may use G|S|W|B = direct-to-load + BESS discharge at Storage tariff; "
            "Grid|RE reporting attributes BESS discharge to charge origin.",
            "Blended ₹/kWh = Discom×G% + Solar×S% + Wind×W% + Storage×B% (DISCOM/Solar/Wind rates from stacked lines).",
            "BESS on Captive/Hybrid: Storage rate = excel_bess_ppa_inr_per_kwh only.",'''

new_blend = '''            "TARGET_POWER_PCT: Grid/Solar/Wind/BESS shares = Architecture mix_*_pct for selected assets.",
            "SIMULATED_ENERGY_SHARE: same as Target on the buyer path — Architecture contracted mix % "
            "(no plant MW inventing; Target = Simulated).",
            "Blended ₹/kWh = Discom×G% + Solar×S% + Wind×W% + Storage×B% (DISCOM/Solar/Wind rates from stacked lines).",
            "BESS on Captive/Hybrid: Storage rate = excel_bess_ppa_inr_per_kwh only.",
            "Demand charge = Peak_MW × DISCOM%/100 × demand ₹/MW-month × 12.",'''

if old_blend not in t:
    print("MISS: blend")
else:
    t = t.replace(old_blend, new_blend, 1)
    print("OK: blend")

old_carbon_note = '''            "Carbon / CFE reporting: RE (Solar+Wind+BESS share in bill model) vs grid EF on grid share",'''
new_carbon_note = '''            "Carbon: baseline tCO₂ = load×EF; actual = load×DISCOM%/100×EF; saved = baseline−actual. "
            "CFE / Annual RE = Solar%+Wind%+BESS% (firm)",'''
if old_carbon_note not in t:
    print("MISS: carbon note")
else:
    t = t.replace(old_carbon_note, new_carbon_note, 1)
    print("OK: carbon note")

# TOC line
old_toc = '''            "Detailed calculations & formulas (bill blend, dispatch, RE/CFE, carbon, savings NPV)",'''
new_toc = '''            "Detailed calculations & formulas (firm delivery, bill blend, RE/CFE, carbon, savings NPV)",'''
if old_toc in t:
    t = t.replace(old_toc, new_toc, 1)
    print("OK: toc")

# Hourly CFE page monthly table note
old_monthly = '''                "Month-wise load, solar, wind, BESS, grid, curtailment, RE%, CFE.",'''
new_monthly = '''                "Month-wise load, contracted Solar/Wind/BESS/DISCOM, RE%, firm CFE.",'''
if old_monthly in t:
    t = t.replace(old_monthly, new_monthly, 1)
    print("OK: monthly")

# HYBRID costs row
old_hyb = '''                "Energy share targets for reporting; HYBRID costs use hourly dispatch stack",'''
new_hyb = '''                "Contracted shares for bill + firm delivery (same rules as Captive)",'''
if old_hyb in t:
    t = t.replace(old_hyb, new_hyb, 1)
    print("OK: hybrid row")

old_cap = '''                "Energy cost-share targets for Excel blend (not MW scaling)",'''
new_cap = '''                "Contracted shares for bill + firm delivery (not plant MW)",'''
if old_cap in t:
    t = t.replace(old_cap, new_cap, 1)
    print("OK: captive row")

# Intro features bullet about CSV
old_csv = '''            "Optional PROJECT DATA 8,760-hour CSV import on Load / Solar / Wind setup steps (synthetic default remains)",'''
new_csv = '''            "Optional PROJECT DATA 8,760-hour CSV import on Load setup (demand); Solar/Wind are firm mix — not plant invent",'''
if old_csv in t:
    t = t.replace(old_csv, new_csv, 1)
    print("OK: csv feature")

if t == orig:
    print("WARNING: no changes written")
else:
    GUIDE.write_text(t, encoding="utf-8")
    print("wrote", GUIDE)

# Regenerate user guide
print("Regenerating docx...")
r = subprocess.run([sys.executable, str(GUIDE)], cwd=str(Path(".").resolve()))
print("exit", r.returncode)
