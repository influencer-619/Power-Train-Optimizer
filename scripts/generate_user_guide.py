"""Generate the PowerTrain Optimizer User Guide (.docx)."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from config.defaults import (
    APPLICABILITY_BANNER,
    DISCLAIMER,
    MODEL_VERSION,
    PRESET_CFE_TARGETS,
    PRESET_RE_TARGETS,
    flatten_assumptions,
    get_default_config,
    recompute_calculated,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "PowerTrain_Optimizer_User_Guide.docx"


def set_run_font(run, size=11, bold=False, color=None):
    run.font.name = "Calibri"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = color


def add_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        set_run_font(run, size={1: 18, 2: 14, 3: 12}.get(level, 11), bold=True)
    return h


def add_para(doc, text, *, bold=False, italic=False, size=11):
    p = doc.add_paragraph()
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold)
    run.italic = italic
    p.paragraph_format.space_after = Pt(6)
    return p


def add_bullets(doc, items):
    for item in items:
        p = doc.add_paragraph(item, style="List Bullet")
        for run in p.runs:
            set_run_font(run)


def add_numbered(doc, items):
    for item in items:
        p = doc.add_paragraph(item, style="List Number")
        for run in p.runs:
            set_run_font(run)


def add_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
        for p in hdr[i].paragraphs:
            for run in p.runs:
                set_run_font(run, bold=True, size=10)
    for r_i, row in enumerate(rows):
        cells = table.rows[r_i + 1].cells
        for c_i, val in enumerate(row):
            cells[c_i].text = "" if val is None else str(val)
            for p in cells[c_i].paragraphs:
                for run in p.runs:
                    set_run_font(run, size=9)
    if col_widths:
        for row in table.rows:
            for i, w in enumerate(col_widths):
                row.cells[i].width = Inches(w)
    doc.add_paragraph()
    return table


def section_params(doc, section_key: str, title: str, intro: str, rows: list[dict]):
    add_heading(doc, title, 2)
    add_para(doc, intro)
    subset = [r for r in rows if r["parameter"].startswith(section_key + ".")]
    add_table(
        doc,
        ["Parameter", "Default", "Unit", "Source", "Description"],
        [
            [
                r["parameter"].split(".", 1)[1].replace("_", " "),
                r["value"],
                r["unit"],
                r["source"],
                r["description"],
            ]
            for r in subset
        ],
        col_widths=[1.6, 1.1, 0.7, 1.3, 2.8],
    )


def build():
    cfg = recompute_calculated(get_default_config())
    rows = flatten_assumptions(cfg)
    doc = Document()

    # Cover
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("PowerTrain Optimizer")
    set_run_font(r, size=28, bold=True, color=RGBColor(0x1B, 0x3A, 0x4B))

    st = doc.add_paragraph()
    st.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = st.add_run("User Guide & Operating Manual")
    set_run_font(r, size=18, bold=True)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = meta.add_run(
        f"Model Version {MODEL_VERSION}\n"
        "Commercial Data-Centre Power Buyer Tool\n"
        "Captive vs Hybrid · DISCOM savings baseline · 8,760-hour dispatch\n"
        "Includes: portable EXE · LAN sharing · Create/Open/Save .pto.zip · "
        "Architecture % × tariff/PPA stacks (no generation-plant CAPEX) · "
        "four load-factor scenarios (headline KPIs = S1) · compact k/Lakh/Cr charts · "
        "on-screen parameter help · Data Quality (SYNTHETIC / Defaults left)"
    )
    set_run_font(r, size=11)
    add_para(doc, "")
    add_para(
        doc,
        "Audience: data-centre developers, renewable energy developers, infrastructure investors, "
        "CFO/finance teams, energy consultants, engineering teams, and management.",
        italic=True,
    )
    add_para(doc, DISCLAIMER, italic=True, size=10)
    doc.add_page_break()

    # TOC-style overview
    add_heading(doc, "1. Contents", 1)
    add_numbered(
        doc,
        [
            "What PowerTrain Optimizer is (incl. Model 2.0 / V2)",
            "System requirements, portable EXE & LAN / network sharing",
            "Quick-start (first 10 minutes)",
            "Start screen — every option",
            "Main application layout & banners",
            "Left navigation — every menu explained",
            "Project Setup wizard (asset-aware steps)",
            "Parameter reference & on-screen help text",
            "Understanding source tags & data quality",
            "Captive vs Hybrid — equal analysis, DISCOM baseline, mix % & storage tariff",
            "Compliance (RPO/RCO single target, ESO single target, hourly CFE) — Project Setup",
            "Optional PROJECT DATA CSV import (Project Setup load/solar/wind steps)",
            "Running analysis, Dashboard comparison, Hourly CFE & load-factor scenarios",
            "How numbers are displayed (k / Lakh / Cr on charts & KPIs)",
            "Feasibility status & binding constraints (no architecture recommendation tags)",
            "Economics, NPV of savings vs DISCOM & reports",
            "Assumptions register (buyer-facing params only), methodology & Settings",
            "Detailed calculations & formulas (bill blend, TOD/availability CFE, carbon, savings NPV)",
            "End-to-end workflow",
            "Interpreting results correctly",
            "Data storage, backup & persistence",
            "Troubleshooting",
            "Glossary",
            "Document control",
        ],
    )
    doc.add_page_break()

    # 2 What it is
    add_heading(doc, "2. What PowerTrain Optimizer Is", 1)
    add_para(
        doc,
        "PowerTrain Optimizer is a local Windows desktop application with a browser-based interface for "
        "commercial data-centre power buyers. It models the facility power bill from Architecture mix % "
        "× DISCOM / PPA / OA tariff stacks — not from solar/wind/BESS generation-plant CAPEX or OPEX.",
    )
    add_para(doc, "On each Run 8760 Simulation (Run Analysis) it evaluates Captive and Hybrid equally using "
             "the same Project Setup contracts, then shows DISCOM as a savings baseline only:")
    add_bullets(
        doc,
        [
            "Side-by-side Captive vs Hybrid comparison on the Dashboard (+ DISCOM baseline column); "
            "CAPTIVE and HYBRID detail tabs — no RECOMMENDED label or Status recommendation row",
            "Annual RE % and Hourly CFE % (pass modes, CFE analytics, Hourly CFE page heatmaps/charts)",
            "Four load-factor scenarios (S1–S4); headline KPIs and primary economics use S1",
            "TOTAL COST OF DELIVERED ENERGY (₹/kWh) from tariff stacks; NPV of bill savings vs DISCOM",
            "RPO/RCO single target, ESO single target, and hourly CFE compliance (Project Setup → Compliance)",
            "Feasibility and binding-constraint diagnosis when targets are not met (informational — not a pick-one recommendation)",
            "Optional PROJECT DATA CSV on Load / Solar / Wind (shapes). Mix % sets annual energy; bill uses Architecture %",
            "Create / Open / Save portable .pto.zip; single EXE with optional LAN sharing",
        ],
    )
    add_heading(doc, "2.1 What it is not", 2)
    add_bullets(
        doc,
        [
            "Not a legal or regulatory determination tool — applicability must be validated externally.",
            "Not a real-time SCADA / EMS system.",
            "Not dependent on Excel/CSV uploads to run — synthetic profiles are always available; PROJECT DATA import is optional.",
            "Not a cloud SaaS product — it is a portable Windows EXE / local server. You may also share it on the "
            "same office Wi‑Fi / LAN so colleagues open it by IP in their browser (see Section 3).",
            "Not a generation-plant investment model — no solar/wind/BESS plant CAPEX, plant financing, or capacity optimization UI.",
            "Not an architecture recommendation engine — the Dashboard does not assign RECOMMENDED or pick a winning structure.",
        ],
    )
    add_heading(doc, "2.2 Critical design rules", 2)
    add_bullets(
        doc,
        [
            "Buyer economics only: power cost = Architecture % × stacked ₹/kWh tariffs (plus demand/fixed/compliance/additional costs).",
            "Captive and Hybrid are both configured under Project Setup and analysed on every Run Analysis; "
            "DISCOM is computed as GRID-ONLY BASELINE for savings — it is not a selectable architecture.",
            "Hourly CFE uses TOD/availability (solar ~0 at night; wind/BESS can serve). Bill uses Architecture mix %.",
            "BESS on Captive/Hybrid uses a single Storage tariff ₹/kWh (excel_bess_ppa_inr_per_kwh) — not battery plant CAPEX/MW.",
            "DC load shape (Seasonal TOD / LF S1–S4) shapes demand only; optional PROJECT DATA CSV is for load, not plant invent.",
            "No external database server — embedded SQLite only.",
            "End users do not need Python, Node.js, Docker or admin rights.",
            "Every default number is labelled DEFAULT ASSUMPTION unless it comes from the concept note.",
            "All KPIs are calculated by the model — never hard-coded.",
            "After you change inputs, prior results are marked STALE until you re-run analysis.",
            "Hourly dispatch must balance; MODEL ERROR is raised on hard validation failures.",
            "Assumptions register hides generation-plant leftovers (CAPEX/OPEX/plant MW/financing/optimization paths).",
        ],
    )

    add_heading(doc, "2.3 What is new in Model 2.0 (V2) — detailed", 2)
    add_para(
        doc,
        f"Model version is now {MODEL_VERSION}. V2 upgrades accuracy and auditability without discarding "
        "existing projects. The following capabilities are live in the EXE and UI:",
    )
    add_table(
        doc,
        ["Area", "What you see / get"],
        [
            [
                "Commercial buyer bill",
                "Year-1 power bill from Architecture mix % × DISCOM / Solar / Wind / Storage tariff stacks. "
                "No generation-plant CAPEX/OPEX in ₹/kWh or NPV.",
            ],
            [
                "Captive vs Hybrid comparison",
                "Each Run Analysis evaluates both Captive and Hybrid profiles plus a DISCOM baseline column on the Dashboard. "
                "CAPTIVE / HYBRID tabs show detail. No RECOMMENDED tag or recommendation Status row.",
            ],
            [
                "Config fingerprint",
                "SHA-256 config hash stored with each run (Reports / audit). Changing inputs marks results STALE until re-run.",
            ],
            [
                "Stale results",
                "If project input_version changes after a run, Dashboard shows a red STALE RESULTS banner. Re-run simulation.",
            ],
            [
                "CFE analytics",
                "Pass mode, % hours ≥ target, longest continuous deficit streak, max/mean deficit (pp), duration-curve stats. "
                "Visible on Dashboard CFE Pass Mode card and Compliance page.",
            ],
            [
                "Feasibility engine",
                "Statuses: FEASIBLE | NOT FEASIBLE | INCOMPLETE INPUTS | LEGAL REVIEW REQUIRED | MODEL ERROR. "
                "Binding constraints list code, message, remedies. Used for Pass/Fail context — not to auto-pick Captive vs Hybrid.",
            ],
            [
                "Economics vs DISCOM",
                "Economics and Dashboard show GRID-ONLY BASELINE (DISCOM) bill and Captive/Hybrid savings. "
                "NPV is the present value of annual bill savings vs DISCOM (no Δ plant CAPEX).",
            ],
            [
                "Load-factor scenarios",
                "Four LF scenarios (S1–S4) from Project Setup load factors; each Run Analysis evaluates all four. "
                "Headline KPIs and primary ₹/kWh use S1.",
            ],
            [
                "Navigation (commercial UI)",
                "Dashboard · Project Setup · Economics · Hourly CFE · Reports · Assumptions · Methodology · Settings. "
                "No Optimization, Sensitivity, Energy Ledger, Profiles, or plant-capacity editor tabs.",
            ],
            [
                "Cost label",
                "₹/kWh is TOTAL COST OF DELIVERED ENERGY (annualised cost / load energy) — not a formal LCOE certificate.",
            ],
            [
                "PROJECT DATA profiles",
                "Optional CSV import on Project Setup Load / Solar / Wind steps (profile_source = SYNTHETIC | PROJECT DATA). "
                "Missing/invalid PROJECT DATA raises MODEL ERROR (no silent fallback).",
            ],
            [
                "Data quality card",
                "Dashboard shows Load/Solar/Wind source badges and count of remaining default assumptions / critical defaults.",
            ],
            [
                "Reports",
                "Excel/PDF exports include Data Quality, Feasibility, CFE Analytics, Captive/Hybrid comparison, "
                "DISCOM baseline, LF scenarios, and tariff-stack economics.",
            ],
            [
                "Portable EXE + LAN share",
                "Single EXE with no Python/Node install. Binds to 0.0.0.0 so other laptops on the same network "
                "can open http://<host-IP>:<port>/ . Settings → Share & access shows Network URLs. "
                "package_share.bat builds dist\\PowerTrain_Share\\ for USB/email distribution.",
            ],
            [
                "Chrome launch",
                "Opens in your existing Google Chrome as a normal tab (falls back to Edge / system browser). "
                "Override with PTO_BROWSER=edge|default if needed.",
            ],
            [
                "Quit / close stops background",
                "Quit App stops the server immediately (and clears orphaned EXE copies). Closing the browser tab "
                "also stops the background process within a few seconds. A second EXE launch reuses a live instance "
                "instead of stacking servers.",
            ],
            [
                "Create / Open / Save Project",
                "Start screen: Create New Project (full defaults) or Open Existing Project… (.pto.zip from disk). "
                "Top bar Save Project writes inputs and a portable .pto.zip to a folder you choose.",
            ],
            [
                "Architecture mix % (buyer contracts)",
                "Captive and Hybrid each store Percentage of power (mix_*_pct) for selected assets (sum = 100%). "
                "Mix % = annual contract energy (Σ Solar = Load×Solar%, shapes preserved — solar ~0 at night). "
                "Bill: TARGET_POWER_PCT and SIMULATED_ENERGY_SHARE both use Architecture mix %. "
                "Hourly CFE = Min(Load, Solar+Wind+RE-BESS)/Load.",
            ],
            [
                "BESS storage tariff",
                "Captive/Hybrid: one Storage ₹/kWh field (excel_bess_ppa_inr_per_kwh). Charge/discharge stack lines "
                "for OA-style BESS are not used on the buyer path.",
            ],
            [
                "Network charges per asset",
                "Optional ₹/kWh transmission / wheeling / other (and banking where applicable) applied separately "
                "to Solar, Wind, BESS discharge and DISCOM/grid import when each asset’s network flag is on.",
            ],
            [
                "Additional costs",
                "Project Setup → Financial: editable list of extra annual costs included in ₹/kWh and cashflows.",
            ],
            [
                "Compliance location",
                "Compliance targets and applicability are edited under Project Setup → Compliance (not a separate "
                "Analysis nav item). Dashboard links back to that setup step.",
            ],
            [
                "Bill: Target = Simulated (Architecture mix)",
                "Economics Grid%|RE% = Architecture DISCOM% | Solar%+Wind%+BESS%. "
                "Hourly CFE / Annual RE use TOD availability (not flat firm mix).",
            ],
            [
                "Savings NPV discount rate",
                "NPV of savings vs DISCOM uses financial.discount_rate_pct from Project Setup → Financial.",
            ],
            [
                "Assumptions register filter",
                "Hides plant-leftover parameters (solar/wind/BESS plant CAPEX/OPEX/MW, financing, optimization) "
                "so the register lists buyer-facing tariff and compliance inputs only.",
            ],
            [
                "On-screen parameter help",
                "Every editable field shows a plain-language title plus a short explanation under the label "
                "(from the model description), not only a cryptic snake_case name.",
            ],
            [
                "Compact number display",
                "KPIs and tables keep at most ~5 digits: values under 1 Lakh show in full; larger values use "
                "Lakh / Cr (₹ prefixed for money). Chart Y-axis ticks use short forms: k (thousands), Lakh, Cr "
                "— with enough left margin so labels do not overlap the axis title (e.g. Energy (MWh)).",
            ],
            [
                "8760 chart time window",
                "Friendly Time window control (Full year / One month / One week / One day) with month names "
                "and day-of-month — replaces the old confusing Month=1 / Day=180 controls.",
            ],
            [
                "Responsive UI",
                "Layouts and charts auto-fit on zoom in/out and window resize.",
            ],
        ],
    )

    # 3 Launch
    add_heading(doc, "3. System Requirements, Portable EXE & Network Sharing", 1)
    add_para(
        doc,
        "PowerTrain Optimizer is designed so you can hand a single Windows EXE to anyone. They can run it on "
        "their laptop with no Python, Node.js, Docker or database install. Optionally, one host laptop runs the "
        "EXE and other people on the same Wi‑Fi / office LAN open the same app in their browser using the host IP.",
    )
    add_heading(doc, "3.1 System requirements", 2)
    add_bullets(
        doc,
        [
            "Windows 10 or Windows 11 (64-bit).",
            "A modern browser (Microsoft Edge or Google Chrome recommended).",
            "Enough free disk for the EXE (~85 MB) plus project data under LocalAppData.",
            "For LAN sharing: host and guests on the same private Wi‑Fi / Ethernet (not guest-network isolation).",
            "Windows Firewall: allow Private network access when Windows prompts on first network use.",
        ],
    )
    add_heading(doc, "3.2 End-user launch — zero dependency (recommended)", 2)
    add_para(
        doc,
        "Share folder (built by package_share.bat): dist\\PowerTrain_Share\\ containing "
        "PowerTrainOptimizer.exe and HOW_TO_SHARE.txt. You may also distribute only the EXE.",
    )
    add_numbered(
        doc,
        [
            "Copy PowerTrainOptimizer.exe to the laptop (USB, shared drive, or email).",
            "Double-click PowerTrainOptimizer.exe (no console/CMD window appears).",
            "Wait a few seconds while the embedded server starts "
            "(first launch creates SQLite; later launches reuse existing data and start faster).",
            "Google Chrome opens a new tab to http://127.0.0.1:<port>/ when Chrome is installed "
            "(preferred port starts at 8765; if busy the launcher picks the next free port). "
            "If Chrome is missing, Edge or the system default browser is used.",
            "If an instance is already running, a second double-click reopens that UI instead of starting another server.",
            "The Start screen appears — PowerTrain Optimizer is ready.",
        ],
    )
    add_para(
        doc,
        "Writable data (database, logs, exports, run files, ACCESS_URLS.txt) is stored under "
        "%LOCALAPPDATA%\\PowerTrainOptimizer when running the EXE. Default project inputs are seeded once "
        "and are not rewritten on every launch.",
    )
    add_heading(doc, "3.3 Share on the office / Wi‑Fi network (LAN)", 2)
    add_para(
        doc,
        "By default the server binds to 0.0.0.0 — meaning it listens on this PC and on the local network. "
        "That lets colleagues open the app without installing anything.",
    )
    add_heading(doc, "3.3.1 On the host laptop (runs the EXE)", 3)
    add_numbered(
        doc,
        [
            "Start PowerTrainOptimizer.exe and leave it running.",
            "Open Settings in the left navigation. The Share & access card shows:",
            "  — This laptop: http://127.0.0.1:<port>/",
            "  — Network (other laptops): one or more URLs like http://192.168.x.x:<port>/",
            "You can Copy a Network URL from Settings, or open ACCESS_URLS.txt "
            "(written next to the EXE and under %LOCALAPPDATA%\\PowerTrainOptimizer).",
            "If Windows Firewall asks, choose Allow on Private networks.",
            "Do not click Quit App until everyone has finished — Quit stops the server for all users.",
        ],
    )
    add_heading(doc, "3.3.2 On other laptops (guests)", 3)
    add_numbered(
        doc,
        [
            "Confirm you are on the same Wi‑Fi / LAN as the host.",
            "Open Edge / Chrome (or any browser).",
            "Type the Network URL from the host, for example http://192.168.1.45:8765/",
            "Use the app normally — no install required.",
        ],
    )
    add_para(doc, "Important LAN behaviour:", bold=True)
    add_bullets(
        doc,
        [
            "All users share the same projects and database on the HOST laptop.",
            "Quit App on the host stops the server for everyone immediately.",
            "Closing the last host browser tab also stops the background EXE within a few seconds "
            "(a short delay allows a page refresh to reconnect). While any UI tab is open and sending "
            "heartbeats — including a guest on the Network URL — the server stays up.",
            "Guest Wi‑Fi with client isolation, VPN, or corporate firewalls may block access — ask IT if needed.",
            "Local-only mode (no network): set environment variable PTO_HOST=127.0.0.1 before starting the EXE.",
            "Optional: PTO_BROWSER=chrome|edge|default controls which browser the host launcher opens.",
        ],
    )
    add_heading(doc, "3.4 Developer launch & rebuild", 2)
    add_para(doc, "From the repository root:")
    add_bullets(
        doc,
        [
            "run_dev.bat — creates/uses .venv, installs requirements, starts the launcher (also LAN-capable).",
            "run_tests.bat — runs pytest unit tests.",
            "build_exe.bat — rebuilds dist\\PowerTrainOptimizer.exe with PyInstaller (windowed, no CMD) "
            "and copies HOW_TO_SHARE.txt beside the EXE. Quit any running EXE first or Windows will block overwrite.",
            "package_share.bat — builds the EXE then creates dist\\PowerTrain_Share\\ "
            "(EXE + HOW_TO_SHARE.txt) ready to give to anyone.",
            "scripts\\generate_user_guide.py — regenerates docs\\PowerTrain_Optimizer_User_Guide.docx.",
        ],
    )
    add_heading(doc, "3.5 Closing the application", 2)
    add_bullets(
        doc,
        [
            "Preferred: click Quit App at the bottom of the left sidebar. Confirm the prompt "
            "(it warns that the server and background PowerTrain processes will stop). "
            "The UI then shows that the server stopped — close the Chrome tab yourself.",
            "Closing the browser tab / window also stops the background EXE (within a few seconds). "
            "Refresh within that window cancels the stop so you do not lose the session by accident.",
            "If no UI heartbeats arrive for ~5 minutes, the process exits as a safety net.",
            "Quit App also terminates other orphaned PowerTrainOptimizer.exe copies from earlier runs.",
            "There is no separate CMD window to close for the packaged EXE (windowed build).",
            "Developer mode (run_dev.bat): the console window closes automatically when the server exits.",
            "Project data remains in SQLite (and any .pto.zip you saved) and is available on the next launch.",
        ],
    )

    # 4 Quick start
    add_heading(doc, "4. Quick-Start (First 10 Minutes)", 1)
    add_numbered(
        doc,
        [
            "Launch the application (latest EXE) — Chrome opens the Start screen.",
            "Click Create New Project (loads full default parameters for the demo 250 MW case).",
            "Confirm the project opens and note the yellow DEFAULT ASSUMPTIONS banner.",
            "Optional: click Save Project in the top bar and choose a local folder for the .pto.zip backup.",
            "Click Run 8760 Simulation in the top bar (Run Analysis — evaluates Captive and Hybrid together).",
            "On the Dashboard, read Feasibility, Data Quality and CFE Pass Mode, then the Captive vs Hybrid comparison "
            "table (+ DISCOM baseline column). Open CAPTIVE / HYBRID tabs for detail.",
            "Open Project Setup: configure Captive and Hybrid mix % (each selected set must sum to 100), "
            "tariff/PPA stacks, Storage ₹/kWh, Load/Solar/Wind/Grid contracts, Compliance and Financial.",
            "After any input change, Save Project if you want an updated .pto.zip, then re-run if STALE RESULTS appears.",
            "Open Economics for Target = Simulated (bill); Hourly CFE for TOD availability charts; export Excel/PDF from Reports.",
            "When finished: Quit App (or close the Chrome tab) so the background EXE exits.",
        ],
    )
    doc.add_page_break()

    # 5 Start screen
    add_heading(doc, "5. Start Screen — Every Option", 1)
    add_para(
        doc,
        "The Start screen is the first page. No project is loaded until you choose one of the two actions below. "
        "(Earlier “Start with Default Model” and sidebar “Switch Project” controls have been removed.)",
    )
    add_heading(doc, "5.1 Create New Project", 2)
    add_para(
        doc,
        "Creates a new project from the full central default configuration (same sizing as the former "
        "demonstration case). Use Project Setup to rename and replace defaults. Every pre-filled editable "
        "value is a DEFAULT ASSUMPTION unless marked CONCEPT_NOTE.",
    )
    add_para(doc, "Default sizing seeded into a new project (editable):")
    add_table(
        doc,
        ["Item", "Default"],
        [
            ["Typical seeded name / facility", "Default Data Centre - 250 MW (editable in Setup)"],
            ["IT load × PUE", "200 MW × 1.25 → 250 MW facility peak"],
            ["Load factor", "80% (base ≈ 200 MW)"],
            ["Solar", "450 MW @ 22% CF"],
            ["Wind", "300 MW @ 32% CF"],
            ["BESS", "150 MW / 600 MWh"],
            ["Grid max import", "250 MW @ 220 kV"],
            ["Architectures analysed", "Captive + Hybrid (DISCOM baseline only)"],
            ["Annual RE target", "90%"],
            ["Hourly CFE target", "90%"],
        ],
    )
    add_heading(doc, "5.2 Open Existing Project…", 2)
    add_para(
        doc,
        "Opens a file picker for a local PowerTrain backup (.pto.zip or .zip). The archive is restored into "
        "the running app’s database so you can continue editing and simulating. Use this after moving machines "
        "or receiving a colleague’s saved project file.",
    )
    add_para(
        doc,
        "Tip: After Create New Project or any input edits, use Save Project in the top bar to write a fresh "
        ".pto.zip to a folder you choose (Save As / download fallback if the browser blocks the folder picker).",
    )

    # 6 Layout
    add_heading(doc, "6. Main Application Layout", 1)
    add_heading(doc, "6.1 Left sidebar", 2)
    add_para(
        doc,
        "Primary navigation to every analysis page (listed in Section 7). At the bottom of the sidebar: "
        "Collapse (narrow/wide nav) and Quit App (shuts down the local server / background EXE).",
    )
    add_heading(doc, "6.2 Top bar", 2)
    add_bullets(
        doc,
        [
            "Project name and current page title",
            f"Model version chip (Model {MODEL_VERSION})",
            "Active detail tab indicator when viewing CAPTIVE or HYBRID drill-down on Dashboard",
            "Study year selector (01 Jan – 31 Dec of the chosen calendar year)",
            "Run 8760 Simulation button — always available once a project is open",
            "Save Project — saves inputs and lets you store a .pto.zip on your local drive",
            "Theme toggle (light / dark)",
        ],
    )
    add_heading(doc, "6.3 Banners (read these before trusting KPIs)", 2)
    add_bullets(
        doc,
        [
            "⚠ DEFAULT ASSUMPTIONS IN USE — shown while any editable DEFAULT_ASSUMPTION remains. "
            "After you edit a field it becomes USER_INPUT. When no editable defaults remain, the green "
            "✓ PROJECT INPUTS CONFIGURED banner appears.",
            "Legal/regulatory applicability banner — reminds that RCO Designated Consumer status and "
            "similar questions require legal review. The model does not decide applicability.",
            "⚠ STALE RESULTS (red) — appears on Dashboard when project inputs changed after the loaded "
            "simulation run (input_version mismatch). Re-run 8760 Simulation before decisions or reports.",
        ],
    )
    add_para(doc, APPLICABILITY_BANNER, italic=True, size=10)

    doc.add_page_break()

    # 7 Navigation
    add_heading(doc, "7. Left Navigation — Every Menu Explained", 1)

    menus = [
        (
            "Dashboard",
            "Results home after Run Analysis. Feasibility, Data Quality and CFE Pass Mode cards; headline KPIs use "
            "load-factor scenario S1. Side-by-side Captive vs Hybrid comparison table with a DISCOM (GRID-ONLY BASELINE) "
            "column for savings context — no RECOMMENDED tag or recommendation Status row. CAPTIVE and HYBRID tabs open "
            "detail for each architecture. Monthly energy chart, cost mix, compliance Pass/Fail with link to "
            "Project Setup → Compliance, LF scenario summary, STALE RESULTS banner when inputs changed.",
        ),
        (
            "Project Setup",
            "Guided wizard: General, Data Centre, Load (incl. four load-factor scenarios S1–S4 and optional PROJECT DATA CSV), "
            "Solar/Wind/BESS/Grid contract steps, Captive architecture (assets + mix % + tariff stacks + Storage ₹/kWh), "
            "Hybrid architecture (same pattern), Compliance (RPO/RCO single target, ESO single target, hourly CFE), "
            "Financial (discount rate, escalations, Additional costs). No Optimization step. Save Section / Next / Finish.",
        ),
        (
            "Economics",
            "Tariff-stack bill breakdown for the active Captive or Hybrid tab context: TOTAL COST OF DELIVERED ENERGY ₹/kWh, "
            "annual bill ₹ Cr, savings vs DISCOM, NPV of savings, Target % vs Simulated energy share "
            "(cost_blend_basis), and component charts. No plant CAPEX lines.",
        ),
        (
            "Hourly CFE",
            "8760-hour workspace: Time window (full year / month / week / day), charts for load, RE, grid, BESS, "
            "curtailment and hourly CFE; monthly energy balance table; CFE heatmap aligned with compliance targets.",
        ),
        (
            "Reports",
            "Export Excel workbook and PDF executive summary (feasibility, CFE, Captive/Hybrid comparison, DISCOM baseline, "
            "LF scenarios, data quality). Backup Project (.pto.zip) for portable restore.",
        ),
        (
            "Assumptions",
            "Searchable register of buyer-facing parameters (tariff stacks, mix %, compliance, load). "
            "Plant-leftover paths (generation CAPEX/OPEX/MW, financing, optimization) are hidden by design.",
        ),
        (
            "Methodology",
            "In-app summary of bill blend (Architecture mix), TOD/availability CFE, Annual RE, carbon, "
            "and NPV of savings vs DISCOM. Section 17A of this guide expands formulas.",
        ),
        (
            "Settings",
            "Share & access: This laptop URL and Network URLs for LAN colleagues (Copy). Application metadata "
            "(currency, theme, model version). Core equations are not editable here.",
        ),
    ]
    for name, desc in menus:
        add_heading(doc, name, 2)
        add_para(doc, desc)

    doc.add_page_break()

    # 8 Setup wizard
    add_heading(doc, "8. Project Setup Wizard — Step by Step", 1)
    add_para(
        doc,
        "Open Project Setup. Configure both Captive and Hybrid contract profiles here (DISCOM is baseline-only and "
        "is not selected as an architecture). Always click Save Section (or Next) before leaving a step. "
        "Use top-bar Save Project for a portable .pto.zip on disk.",
    )
    steps = [
        ("1. General", "Project name, location label, currency, model hours (8760), calendar year, random seed, notes."),
        ("2. Data Centre", "Facility name, IT capacity (MW), grid connection kV (concept note: 220 kV), designated-consumer status."),
        (
            "3. Load",
            "profile_source (SYNTHETIC | PROJECT DATA), IT load, PUE, peak load, load-factor scenarios S1–S4 "
            "(headline KPIs use S1), shape multipliers. Optional PROJECT DATA CSV upload on this step.",
        ),
        (
            "4. Solar / Wind / BESS / Grid contracts",
            "Energy contract inputs: stacked ₹/kWh tariff/PPA lines, contract energy (mix% × annual load), "
            "synthetic or PROJECT DATA generation shapes, grid import limit and DISCOM tariff/TOD/demand/fixed. "
            "BESS: Storage tariff ₹/kWh only on Captive/Hybrid (not plant CAPEX).",
        ),
        (
            "5. Captive architecture",
            "Asset include flags, Percentage of power (sum 100%), Captive tariff stacks, optional DISCOM share, "
            "cost_blend_basis, network flags as applicable.",
        ),
        (
            "6. Hybrid architecture",
            "Same pattern as Captive with DISCOM + Solar + Wind + BESS combinations typical for hybrid supply.",
        ),
        (
            "7. Compliance",
            "RPO/RCO single target, ESO single target, Annual RE and Hourly CFE targets and pass mode. "
            "Dashboard links here for edits.",
        ),
        (
            "8. Financial",
            "Project life, discount rate (NPV of savings vs DISCOM), inflation, electricity/RE escalations, "
            "Additional costs (named annual ₹ lines in the power bill).",
        ),
    ]
    for title, text in steps:
        add_heading(doc, title, 2)
        add_para(doc, text)
    add_para(
        doc,
        "Tip: There are no separate Profiles or plant-capacity sidebar tabs — import PROJECT DATA and edit "
        "contracts entirely within Project Setup.",
    )

    doc.add_page_break()

    # 9 Parameter reference
    add_heading(doc, "9. Complete Parameter Reference & On-Screen Help", 1)
    add_para(
        doc,
        "The tables below list every configurable parameter in the default configuration, including the "
        f"demonstration Default Data Centre - 250 MW values (Model {MODEL_VERSION}). "
        "When you edit a value in the UI, its Source becomes USER_INPUT.",
    )
    add_heading(doc, "9.0 How parameters appear in the UI", 2)
    add_para(
        doc,
        "On Project Setup (and Economics / Compliance sub-forms), each field is shown as:",
    )
    add_bullets(
        doc,
        [
            "A clear human-readable title (for example Peak load instead of peak_load_mw).",
            "A short explanation under the title — taken from the same Description column documented below — "
            "so users understand what the parameter means before editing.",
            "The input control (number / text / dropdown / True–False) and unit.",
            "A source badge: CONCEPT_NOTE, DEFAULT_ASSUMPTION, USER_INPUT or CALCULATED.",
        ],
    )
    add_para(
        doc,
        "Read-only CALCULATED fields are slightly dimmed and cannot be typed over. "
        "Use the Assumptions register for a searchable full list of the same descriptions.",
    )

    section_params(
        doc,
        "general",
        "9.1 General",
        "Project identity and model clock settings.",
        rows,
    )
    section_params(
        doc,
        "data_center",
        "9.2 Data Centre",
        "Facility labelling and interconnection facts from / aligned with the concept note.",
        rows,
    )
    section_params(
        doc,
        "load",
        "9.3 Load",
        "Parameters used to synthesize the 8,760-hour demand profile when profile_source = SYNTHETIC. "
        "Set profile_source = PROJECT DATA and upload a CSV on the Load step to use measured/forecast series instead. "
        "You never enter 8,760 rows in the parameter form.",
        rows,
    )
    add_para(doc, "Load model options:")
    add_bullets(
        doc,
        [
            "Flat — constant shape before load-factor scaling",
            "Daily Pattern — uses hour multipliers",
            "Weekday/Weekend — applies weekday vs weekend multipliers",
            "Seasonal — uses month multipliers",
            "Custom Parameterized — combines diurnal, weekday/weekend and seasonal factors (default)",
        ],
    )
    section_params(
        doc,
        "solar",
        "9.4 Solar",
        "Solar annual MWh = Load × Solar%. Hourly shape (synthetic sunrise–sunset or PROJECT DATA) is scaled to that "
        "annual energy — solar ≈ 0 at night. Used for hourly CFE/charts; bill still uses Architecture mix %.",
        rows,
    )
    section_params(
        doc,
        "wind",
        "9.5 Wind",
        "Wind annual MWh = Load × Wind%. Hourly shape (synthetic or PROJECT DATA) is scaled to that annual energy "
        "and can serve at night. Used for hourly CFE/charts; bill uses Architecture mix %.",
        rows,
    )
    section_params(
        doc,
        "bess",
        "9.6 BESS",
        "Buyer BESS: Storage tariff × mix % on the bill. If BESS mix > 0, derived storage shifts day RE to night for CFE.",
        rows,
    )
    section_params(
        doc,
        "grid",
        "9.7 Grid",
        "Import capacity and tariff stack. Effective hourly import limit = max_import_mw × availability_pct.",
        rows,
    )
    section_params(
        doc,
        "commercial",
        "9.8 Commercial structure parameters",
        "Controls which commercial cost stack is applied, which assets are included, Percentage of power "
        "(mix_*_pct — annual contract energy + bill shares, selected assets must sum to 100; CFE uses TOD shapes), "
        "cost_blend_basis (TARGET_POWER_PCT and SIMULATED_ENERGY_SHARE both = Architecture mix % on the buyer path), "
        "ownership/allocation metadata, and network-charge flags.",
        rows,
    )
    section_params(
        doc,
        "compliance",
        "9.9 Compliance parameters",
        "Targets and applicability gates. Applicability options: Applicable / Not Applicable / Unknown / Legal Review Required.",
        rows,
    )
    add_para(
        doc,
        f"Preset Annual RE targets: {', '.join(str(int(x))+'%' for x in PRESET_RE_TARGETS)}. "
        f"Preset Hourly CFE targets: {', '.join(str(int(x))+'%' for x in PRESET_CFE_TARGETS)}.",
    )
    section_params(
        doc,
        "financial",
        "9.10 Financial parameters",
        "Cash-flow horizon and discount rate for NPV of bill savings vs DISCOM; inflation and tariff escalations.",
        rows,
    )
    add_para(
        doc,
        "Generation-plant CAPEX/OPEX, plant MW sizing, project financing, and optimization parameters are "
        "omitted from this reference — they are hidden from the Assumptions register in the commercial buyer app.",
    )

    doc.add_page_break()

    # 10 Source tags
    add_heading(doc, "10. Understanding Source Tags & Data Quality", 1)
    add_para(
        doc,
        "Every parameter carries a source tag. The Dashboard Data Quality card summarises whether profiles "
        "are generated or imported, how many defaults remain, and whether critical commercial/technical "
        "inputs are still placeholders. Read this card before treating KPIs as investment-ready.",
    )
    add_table(
        doc,
        ["Source", "Meaning"],
        [
            ["CONCEPT_NOTE", "Stated in the Design Concept Note for Power Train Architecture. Still editable unless locked."],
            ["DEFAULT_ASSUMPTION", "Required to run the model but not a concept-note fact. Must be replaced with project data for investment use."],
            ["USER_INPUT", "You (or a loaded scenario / profile upload) have set this value."],
            ["CALCULATED", "Derived automatically (e.g. base_load_mw). Not directly editable."],
        ],
    )
    add_para(
        doc,
        "Each on-screen field shows: Parameter name · Value · Unit · Source badge · short help text under the label "
        "(and ⓘ description where present).",
    )
    add_heading(doc, "10.1 Data quality labels (Dashboard)", 2)
    add_table(
        doc,
        ["Label", "Meaning"],
        [
            ["SYNTHETIC", "Profile came from the parameterized generator (default)."],
            ["PROJECT DATA", "Profile came from a validated imported 8,760/8,784 CSV."],
            ["PRELIMINARY", "Overall data-quality badge when not all of Load/Solar/Wind are PROJECT DATA (typical early run)."],
            ["PROJECT DATA ANALYSIS", "All three of Load/Solar/Wind are PROJECT DATA."],
            ["Defaults left", "Count of editable parameters still marked DEFAULT_ASSUMPTION (e.g. 197 on a fresh project)."],
            ["Critical defaults", "High-impact defaults still present (e.g. peak load, LF, tariffs, compliance applicability)."],
        ],
    )

    add_heading(doc, "10.2 What SYNTHETIC means (in detail)", 2)
    add_para(
        doc,
        "SYNTHETIC does not mean “fake economics” or “random noise only.” It means the 8,760-hour "
        "Load, Solar or Wind series was built inside the model from Setup parameters, instead of from "
        "an uploaded measured/forecast CSV.",
    )
    add_table(
        doc,
        ["Series", "How SYNTHETIC is built", "How to switch to PROJECT DATA"],
        [
            [
                "Load",
                "Peak load, load factor, weekday/weekend multipliers and shape settings synthesize hourly MW demand.",
                "Project Setup → Load: upload CSV (8,760 or 8,784 hours) — profile_source becomes PROJECT DATA.",
            ],
            [
                "Solar",
                "Capacity, target CF, sunrise/sunset, peak hour, seasonal factors and seeded variability.",
                "Project Setup → Solar: upload CSV or set profile_source = PROJECT DATA after a valid import.",
            ],
            [
                "Wind",
                "Capacity, target CF, monthly factors and deterministic variability (general.random_seed).",
                "Project Setup → Wind: upload CSV; Clear returns the series to SYNTHETIC.",
            ],
        ],
        col_widths=[1.2, 3.2, 2.6],
    )
    add_para(
        doc,
        "Important: if profile_source = PROJECT DATA but no valid file is imported, simulation raises MODEL ERROR. "
        "The app never silently substitutes a synthetic series in that case. SYNTHETIC is always available for "
        "screening runs without any CSV.",
    )
    add_para(
        doc,
        "PRELIMINARY on the Data Quality card is expected when any of Load/Solar/Wind is still SYNTHETIC "
        "and/or many defaults remain. It is a caution label, not a calculation failure.",
    )

    add_heading(doc, "10.3 Defaults left — what the number means", 2)
    add_para(
        doc,
        "Defaults left counts every editable parameter whose source is still DEFAULT_ASSUMPTION. "
        "Calculated fields are excluded. A new project commonly shows a high number (often ~190+) "
        "because the model ships with a complete runnable default stack.",
    )
    add_bullets(
        doc,
        [
            "Saving a field in Project Setup (or a direct editor) marks it USER_INPUT and reduces the count.",
            "The count is a data-quality indicator — not an error code and not the same as “197 bugs.”",
            "Critical defaults lists the highest-impact placeholders still on defaults (peak load, load factor, "
            "solar/wind CF, energy tariff, key CAPEX rates, compliance applicability, etc.).",
            "Feasibility may report INCOMPLETE INPUTS while editable defaults remain — suitable for screening, "
            "not for final investment decisions.",
            "After you replace critical commercial and technical inputs, re-run 8760 Simulation so the "
            "Data Quality card refreshes.",
        ],
    )

    # 11 Architectures
    add_heading(doc, "11. Captive vs Hybrid — Equal Analysis & DISCOM Baseline", 1)
    add_para(
        doc,
        "The commercial buyer app configures two supply architectures — Captive and Hybrid — under Project Setup. "
        "Each Run Analysis evaluates both using their saved profiles (assets, mix %, tariff stacks, Storage tariff). "
        "DISCOM is not selectable: the engine always computes a GRID-ONLY BASELINE bill for savings and NPV context. "
        "The Dashboard shows a side-by-side comparison table (+ DISCOM column) and CAPTIVE / HYBRID detail tabs. "
        "There is no RECOMMENDED label, Status recommendation row, or automatic pick of a winning architecture.",
    )
    add_heading(doc, "11.0 Asset selection (include flags)", 2)
    add_para(
        doc,
        "Within each architecture profile, tick which assets participate (Solar, Wind, BESS, DISCOM/grid). "
        "Unselected assets are excluded from that architecture’s bill blend and dispatch contract energy.",
    )
    add_table(
        doc,
        ["Profile", "Typical assets"],
        [
            ["CAPTIVE", "Solar, Wind, BESS (optional DISCOM backup share)"],
            ["HYBRID", "DISCOM, Solar, Wind, BESS"],
            ["DISCOM baseline", "Grid only (not user-selectable — computed automatically)"],
        ],
    )

    add_heading(doc, "11.0.1 Percentage of power (mix shares) — detailed", 2)
    add_para(
        doc,
        "For each architecture (Captive and Hybrid separately), set Percentage of power for each selected asset. "
        "These percentages are buyer contract shares for the tariff-stack bill and annual Solar/Wind MWh "
        "(shapes scaled to mix%×load — solar ≈ 0 at night). They do not represent plant MW investment.",
    )
    add_para(doc, "Hard rule — selected assets must sum to 100%", bold=True)
    add_bullets(
        doc,
        [
            "Only selected assets count toward the sum (unchecked assets are ignored and zeroed by include flags).",
            "The Architecture screen shows a live Total: X% (must equal 100%) — green when valid, red when not.",
            "Save Section / Next / Prev / Save Project block with an alert if the total is not within 0.05 of 100%.",
            "Simulation validation also errors if Percentage of power for selected assets do not sum to 100.",
            "DISCOM baseline uses Grid% = 100, RE% = 0 (no mix editor).",
            "After a run, Economics shows Target % and Simulated % — both equal Architecture contracted mix "
            "(Grid% = DISCOM%; RE% = Solar%+Wind%+BESS%).",
            "commercial.cost_blend_basis: TARGET_POWER_PCT and SIMULATED_ENERGY_SHARE both price Architecture "
            "contracted mix % × stacked rates (Target = Simulated on the buyer path).",
        ],
    )
    add_para(doc, "UI behaviour", bold=True)
    add_bullets(
        doc,
        [
            "Switching between Captive and Hybrid setup sections keeps separate saved profiles for each architecture.",
            "Toggling an asset chip (include/exclude) redistributes % evenly across the remaining selected assets "
            "so the total stays 100%.",
            "You may then edit individual % values manually as long as the total remains 100.",
            "Only fields for the current structure and selected assets are shown.",
        ],
    )
    add_para(doc, "Example default mix (Hybrid, all four assets selected)", bold=True)
    add_table(
        doc,
        ["Asset", "Default usage %", "Config key"],
        [
            ["DISCOM / grid", "25", "commercial.mix_discom_pct"],
            ["Solar", "35", "commercial.mix_solar_pct"],
            ["Wind", "25", "commercial.mix_wind_pct"],
            ["BESS", "15", "commercial.mix_bess_pct"],
        ],
        col_widths=[2.0, 1.5, 3.0],
    )
    add_para(
        doc,
        "For CAPTIVE (Solar + Wind + BESS only), opening/merging a project equalizes the three selected "
        "mix fields so they sum to 100% (DISCOM mix is unused). Older projects that stored independent "
        "100% values on every asset are auto-equalized on load.",
    )
    add_table(
        doc,
        ["Structure", "Usage % fields shown", "What each % does"],
        [
            [
                "DISCOM",
                "(none — grid-only)",
                "Solar / Wind / BESS forced to 0; full grid import path",
            ],
            [
                "CAPTIVE",
                "Solar % · Wind % · BESS % (+ DISCOM % if DISCOM selected); sum = 100",
                "Contracted shares for bill + annual energy (TOD shapes for CFE)",
            ],
            [
                "HYBRID",
                "DISCOM % · Solar % · Wind % · BESS % (selected sum = 100)",
                "Contracted shares for bill + annual energy (same rules as Captive)",
            ],
        ],
        col_widths=[1.3, 2.4, 2.8],
    )
    add_para(doc, "Engine behaviour (after include-flag zeroing):", bold=True)
    add_bullets(
        doc,
        [
            "Annual Solar/Wind MWh = Load × mix%; hourly shapes keep TOD (solar ~0 at night). "
            "BESS% billed at Storage tariff; derived storage for night CFE when BESS mix > 0.",
            "Year-1 energy ₹ = Load × (Discom×G% + Solar×S% + Wind×W% + Storage×B%) — both cost-blend bases "
            "use Architecture contracted mix %.",
            "BESS on Captive/Hybrid: single Storage tariff ₹/kWh (excel_bess_ppa_inr_per_kwh) — not plant CAPEX/MW.",
            "Config keys: commercial.mix_discom_pct, mix_solar_pct, mix_wind_pct, mix_bess_pct "
            "(each 0–100; selected assets must sum to 100)",
        ],
    )
    add_para(doc, "Worked examples", bold=True)
    add_bullets(
        doc,
        [
            "CAPTIVE with Solar 50% + Wind 30% + BESS 20%: bill uses those shares; night CFE needs wind/BESS.",
            "Hybrid with Wind unchecked: DISCOM + Solar + BESS % must sum to 100 (e.g. 25 / 50 / 25).",
            "Bill Target Grid%|RE% = Simulated = Architecture mix; hourly CFE follows availability.",
        ],
    )
    add_para(
        doc,
        "Note: captive_ownership_pct and captive_allocation_pct remain commercial metadata for contracts; "
        "they do not replace Percentage of power.",
    )

    add_heading(doc, "11.1 DISCOM — GRID-ONLY BASELINE (not selectable)", 2)
    add_para(
        doc,
        "Full grid supply economics for the same load and LF scenario S1: stacked DISCOM ₹/kWh, demand on peak "
        "import, fixed charges, compliance. Grid% = 100, RE% = 0; Annual RE and Hourly CFE min are 0% by design. "
        "Shown as its own column in the Dashboard comparison and on Economics as the reference bill. "
        "Savings vs DISCOM and NPV of savings are measured against this baseline — not against plant CAPEX.",
    )
    add_heading(doc, "11.2 Captive / Group Captive profile", 2)
    add_para(
        doc,
        "Captive-style supply contracts: Solar, Wind, BESS (Storage tariff), optional DISCOM backup share. "
        "Stacked ₹/kWh lines mirror Excel Captive/OA charge components for each asset. "
        "Ownership/allocation metadata is stored for reporting — the tool does not certify captive legal qualification. "
        "Bill shares use Architecture mix %. Annual RE % and Hourly CFE use TOD availability.",
    )
    add_heading(doc, "11.3 Hybrid profile", 2)
    add_para(
        doc,
        "Hybrid supply combines DISCOM grid backup with contracted Solar, Wind and BESS Storage. "
        "Mix % and tariff stacks are edited separately from Captive so both can be compared on equal footing after each Run Analysis.",
    )
    add_heading(doc, "11.4 Storage tariff & charge stacks", 2)
    add_bullets(
        doc,
        [
            "Captive/Hybrid BESS: one user-facing Storage ₹/kWh (excel_bess_ppa_inr_per_kwh). Zero means no BESS energy cost in the bill.",
            "Solar/Wind: PPA + energy + wheeling + transmission + losses + CSS + AS + SLDC + banking + ED + TOSE stacks as configured.",
            "DISCOM: energy + wheeling + TOD + duty + TOSE (+ demand/fixed from Grid setup).",
            "Network charge flags may add per-asset ₹/kWh where enabled for legacy/open-access style lines.",
        ],
    )
    add_heading(doc, "11.5 Dashboard comparison (no recommendation)", 2)
    add_para(
        doc,
        "After Run Analysis the Dashboard lists Captive and Hybrid side by side with DISCOM baseline metrics: "
        "₹/kWh, annual bill ₹ Cr, savings vs DISCOM, NPV of savings, Annual RE %, Hourly CFE min, feasibility status. "
        "Use CAPTIVE / HYBRID tabs for charts and KPI detail. The UI does not show RECOMMENDED, "
        "NO FEASIBLE RECOMMENDATION, or a Status row that picks a winner — you compare numbers directly.",
    )

    # 12 Compliance
    add_heading(doc, "12. Compliance (Project Setup) Explained", 1)
    add_para(
        doc,
        "Compliance inputs and post-run analytics live under Project Setup → Compliance. There is no separate "
        "Compliance item under Analysis navigation (to avoid duplicating Setup). From the Dashboard compliance card, "
        "use Open Project Setup → Compliance to jump to that step.",
    )
    add_heading(doc, "12.1 Applicability gates", 2)
    add_para(
        doc,
        "For RPO, RCO and ESO you must declare Applicable / Not Applicable / Unknown / Legal Review Required. "
        "If Unknown or Not Applicable, the engine does not invent a legal conclusion. Unknown displays as "
        "LEGAL REVIEW REQUIRED style status rather than Pass.",
    )
    add_heading(doc, "12.2 RPO / RCO (single combined target)", 2)
    add_para(
        doc,
        "The commercial UI uses a single RPO/RCO target percentage (not separate solar/wind/hydro buckets). "
        "Set applicability, the combined target, and buyout/REC costs if Applicable. "
        "Do not treat model Pass/Fail as a legal RCO Designated Consumer determination.",
    )
    add_heading(doc, "12.3 ESO (single target)", 2)
    add_para(
        doc,
        "Single ESO target percentage for the study year (trajectory defaults from concept note unless you override). "
        "Renewable-origin stored energy requirement defaults to ≥ 85% (concept note). Select active ESO year in Setup.",
    )
    add_heading(doc, "12.4 Hourly CFE targets", 2)
    add_para(
        doc,
        "Hourly CFE target and pass mode drive feasibility alongside Annual RE %. Edit under the same Compliance step.",
    )
    add_heading(doc, "12.5 Annual RE % vs Hourly CFE % (and CFE analytics)", 2)
    add_bullets(
        doc,
        [
            "Annual RE % = Σ RE serving load / Σ Load × 100 (availability — direct Solar+Wind + RE-origin BESS).",
            "Hourly CFE % = Min(Load, Solar_t + Wind_t + RE-BESS_discharge_t) / Load × 100. "
            "Solar ≈ 0 at night; night CFE comes from wind and/or BESS.",
            "Energy-weighted CFE ≡ Annual RE % (same matched CF / load). Min hourly CFE is often below Architecture RE mix %.",
            "CFE pass modes: All hours >= target | Mean hourly CFE >= target | Share of hours >= target.",
            "Default All hours >= target is a strict 24×7 rule. Fail at night usually means raise Wind/BESS mix, "
            "improve shapes, or relax the target — not pretend solar is on at night.",
            "Dashboard CFE Pass Mode card shows: mode, target, min hour, % hours ≥ target, longest continuous deficit streak (hours), max deficit (pp).",
            "Dashboard Compliance Status shows actual vs target and a short “Why Fail?” note when status is Fail.",
            "CFE heatmap uses an absolute 0–100% colour scale; night hours often read lower than daytime.",
        ],
    )

    doc.add_page_break()

    # 12A Profiles
    add_heading(doc, "12A. Optional PROJECT DATA CSV Import (Project Setup)", 1)
    add_para(
        doc,
        "On Project Setup steps for Load, Solar and Wind you can keep SYNTHETIC generation or upload a PROJECT DATA CSV.",
    )
    add_heading(doc, "12A.1 Accepted file format", 2)
    add_bullets(
        doc,
        [
            "CSV text file.",
            "Header row: timestamp,mw (recommended) — or a single column of MW values.",
            "Exactly 8,760 data rows for a non-leap year (or 8,784 for leap) — no more, no less.",
            "timestamp: unique hourly stamps (ISO recommended), e.g. 2025-01-01T00:00:00",
            "mw: non-negative finite number (megawatts). No blanks, no text, no NaN.",
            "Download ready-made templates from Project Setup (or docs/samples/): Load / Solar / Wind template CSVs "
            "(also in docs/samples/ and frontend/dist/samples/). Keep timestamps; replace the mw column with your data.",
        ],
    )
    add_heading(doc, "12A.2 Upload / Clear workflow", 2)
    add_numbered(
        doc,
        [
            "Choose the resource card (Load / Solar / Wind).",
            "Click Choose File → select CSV → Upload CSV.",
            "On success: badge shows PROJECT DATA; profile_source is set to PROJECT DATA automatically; hours/min/max shown.",
            "On failure: error lists validation messages — fix the file and retry. Synthetic data is NOT substituted.",
            "Clear removes the imported file and sets profile_source back to SYNTHETIC.",
            "Also set profile_source in Load/Solar/Wind editors or Project Setup if you need to switch without re-upload "
            "(PROJECT DATA without a file will raise MODEL ERROR on simulate).",
        ],
    )
    add_heading(doc, "12A.3 Rules of engagement", 2)
    add_bullets(
        doc,
        [
            "Synthetic remains the default so demos and first runs never require files.",
            "No silent data substitution — accuracy over convenience.",
            "Imported profiles are stored under the project’s profile folder (writable data directory).",
            "After changing profiles or profile_source, re-run 8760 Simulation (results become STALE otherwise).",
        ],
    )

    # 13 Simulation
    add_heading(doc, "13. Running Analysis, Dashboard & Hourly CFE", 1)
    add_heading(doc, "13.1 How to run", 2)
    add_numbered(
        doc,
        [
            "Ensure the correct project is open and inputs are saved.",
            "If using PROJECT DATA, confirm CSV upload on the relevant Project Setup step.",
            "Click Run 8760 Simulation in the top bar (Run Analysis — works from any page).",
            "Wait for completion (typically a few seconds per architecture × LF scenarios).",
            "Review Dashboard: Captive vs Hybrid table, DISCOM baseline column, S1 headline KPIs.",
            "Open Hourly CFE for time-window charts and monthly energy balance.",
        ],
    )
    add_heading(doc, "13.2 What the engine does (Model 2.0)", 2)
    add_numbered(
        doc,
        [
            "Build DC load for each LF scenario (S1–S4) from Seasonal TOD / study period (demand shape only).",
            "Scale Solar/Wind shapes to annual mix%×load; derive BESS storage if BESS mix > 0; set DISCOM grid cap.",
            "Dispatch hourly: RE to load, charge BESS from excess, discharge at deficit, DISCOM residual.",
            "Validate finite values — MODEL ERROR on hard failure. Commercial unserved_mwh = 0 (feasibility ignores profile unserved).",
            "Compute availability CFE/RE, compliance, feasibility, tariff-stack economics (Architecture mix bill) and savings vs DISCOM.",
        ],
    )
    add_heading(doc, "13.3 Hourly CFE page — Time window controls (detailed)", 2)
    add_para(
        doc,
        "The chart toolbar is designed for non-technical users. It no longer shows a raw “Day = 180” "
        "(day-of-year) next to Month = 1, which was easy to misread. Instead:",
    )
    add_table(
        doc,
        ["Control", "What the user sees / does", "What the model fetches"],
        [
            [
                "Time window",
                "Dropdown with plain labels: Full year (overview) | One month | One week | One day (24 hours).",
                "Maps to engine views year / month / week / day.",
            ],
            [
                "Month",
                "Shown only for One month / One week / One day. Dropdown of month names (January–December).",
                "Calendar month 1–12 for month view; also used to compute day-of-year for week/day.",
            ],
            [
                "Day of month",
                "Shown only for One week / One day. Number 1–28/29/30/31 (clamped to that month).",
                "Converted internally to day-of-year for the week-start or single-day slice.",
            ],
            [
                "Show charts",
                "Button that loads the four panels for the selected window.",
                "GET /api/simulation/{id}/series?view=&month=&day=",
            ],
            [
                "Hint text",
                "Live sentence under the controls explaining the window (e.g. “Shows 24 hours for June 29”).",
                "UI-only guidance.",
            ],
            [
                "Monthly Energy Balance table",
                "Appears after a simulation exists.",
                "Month-wise load, available Solar/Wind/BESS/DISCOM, RE%, hourly CFE.",
            ],
        ],
    )
    add_para(doc, "How to use (examples):", bold=True)
    add_bullets(
        doc,
        [
            "Full year (overview) — no Month/Day fields. Charts show a sampled full-year overview (every 6th hour) for shape, not every single hour.",
            "One month → pick June → Show charts — all hours in June.",
            "One week → pick June and day 29 → Show charts — seven days starting 29 June.",
            "One day → pick June and day 29 → Show charts — 24 hours for that calendar day.",
            "Run a simulation first; otherwise Show charts asks you to run one.",
        ],
    )
    add_heading(doc, "13.4 Load-factor scenarios (S1–S4)", 2)
    add_para(
        doc,
        "Project Setup → Load defines up to four load-factor scenarios (load_factor_s1_pct … s4_pct). "
        "Each Run Analysis evaluates all configured scenarios. Dashboard headline KPIs, primary ₹/kWh, and "
        "the Captive vs Hybrid comparison table use S1 unless you drill into another scenario in exports or detail panels.",
    )
    add_heading(doc, "13.5 Dashboard KPI cards (S1 headline)", 2)
    add_table(
        doc,
        ["KPI", "Meaning"],
        [
            ["Annual RE", "Energy-weighted RE serving load / load (availability)"],
            ["Hourly CFE (min)", "Min hourly CFE from Solar+Wind+RE-BESS; Pass/Fail vs target"],
            ["Grid Import", "Annual DISCOM import from dispatch (GWh)"],
            ["BESS", "Bill: Storage tariff × mix %. Hourly: derived storage when BESS mix > 0"],
            ["Cost ₹/kWh", "TOTAL COST OF DELIVERED ENERGY (Year-1 bill ÷ load kWh)"],
            ["NPV ₹ Cr", "Present value of bill savings vs DISCOM baseline (Captive/Hybrid)"],
            ["Savings vs DISCOM", "Year-1 bill delta vs GRID-ONLY BASELINE (₹ Cr)"],
            ["LF scenario", "Headline row uses S1; other scenarios in run metadata / exports"],
        ],
    )

    add_heading(doc, "13.6 How numbers are displayed (k / Lakh / Cr)", 2)
    add_para(
        doc,
        "Large techno-economic figures are intentionally shown in compact Indian-style units so the UI "
        "never floods the screen with long digit strings. The same rules apply to Dashboard KPIs, tables, "
        "ledger values, economics and most chart tooltips. Chart axis ticks use an even shorter form.",
    )
    add_table(
        doc,
        ["Absolute value", "How it is shown", "Example"],
        [
            ["Less than 1,00,000 (under 1 Lakh)", "Full number with Indian grouping, up to ~5 integer digits", "45,000 · 1,401.6"],
            ["1 Lakh to under 1 Crore", "X.XX Lakh", "14.02 Lakh MWh"],
            ["1 Crore and above", "X.XX Cr", "4.50 Cr"],
            ["Money (₹)", "Same compact body with ₹ prefix", "₹14.02 Lakh · ₹4.50 Cr"],
            ["Small rates / %", "Usually stay as ordinary numbers (under 1,000)", "8.50 ₹/kWh · 90%"],
            [
                "Chart Y-axis ticks",
                "Short labels: k for thousands, then Lakh, then Cr — plus left margin so labels "
                "do not clip or overlap the rotated axis title (e.g. Energy (MWh))",
                "25k · 1.5 Lakh · 2.0 Cr",
            ],
        ],
    )
    add_para(
        doc,
        "Exports (Excel/PDF) may still contain full-precision numeric cells for audit; the on-screen SPA "
        "is optimized for readable Indian units. Hard-refresh (Ctrl+F5) after upgrading the EXE if an old "
        "cached UI still shows long digit strings or clipped axis text (e.g. “housand”).",
    )

    # 13B Feasibility
    add_heading(doc, "13B. Feasibility Status & Binding Constraints", 1)
    add_para(
        doc,
        "Every simulation returns a unified feasibility object per architecture. The Dashboard Feasibility card "
        "summarises whether enabled RE/CFE (and Applicable RPO/ESO) checks pass — it does not select Captive vs Hybrid. "
        "Plant-profile unserved energy is not a buyer-path gate (commercial unserved_mwh = 0).",
    )
    add_table(
        doc,
        ["Status", "Meaning"],
        [
            ["FEASIBLE", "Enabled technical/compliance targets met; no hard model error."],
            ["NOT FEASIBLE", "RE target miss and/or CFE pass-mode fail (Architecture mix below target), or Applicable RPO/ESO fail."],
            ["INCOMPLETE INPUTS", "Editable DEFAULT_ASSUMPTION values remain (preliminary / not board-ready)."],
            ["LEGAL REVIEW REQUIRED", "RPO/RCO/ESO applicability still requires legal review."],
            ["MODEL ERROR", "Internal validation failed (balance/SOC/NaN). Do not use results."],
        ],
    )
    add_heading(doc, "13B.1 Binding constraints", 2)
    add_para(
        doc,
        "When not feasible, the card lists binding items such as ANNUAL_RE, HOURLY_CFE, RPO, RCO, ESO "
        "with actual vs target. Remedies: raise Solar/Wind/BESS mix %, or relax the target / pass mode under "
        "Project Setup → Compliance — not plant MW sizing.",
    )
    add_heading(doc, "13B.2 Stale results", 2)
    add_para(
        doc,
        "Saving inputs increments the project input_version. If the loaded simulation’s input_version differs, "
        "results_stale = true and a red STALE RESULTS banner appears. Re-run before exporting board packs.",
    )

    # 14 Economics & reports
    add_heading(doc, "14. Economics, Savings vs DISCOM & Reports", 1)
    add_heading(doc, "14.1 Economics page", 2)
    add_para(
        doc,
        "Requires a completed Run Analysis. Shows TOTAL COST OF DELIVERED ENERGY ₹/kWh (tariff-stack bill), "
        "annual bill ₹ Cr, component breakdown (grid/solar/wind/storage/demand/fixed/compliance), "
        "Target Architecture % and Simulated % (both equal contracted mix on the buyer path), carbon/CFE outcomes, "
        "and NPV of cumulative bill savings vs DISCOM. No generation-plant CAPEX lines.",
    )
    add_heading(doc, "14.2 GRID-ONLY BASELINE (DISCOM) panel", 2)
    add_para(
        doc,
        "Reference grid-only bill for the same load and LF scenario. Use for savings ₹ Cr and NPV of savings — "
        "not as a selectable supply architecture.",
    )
    add_heading(doc, "14.3 Captive vs Hybrid on Economics", 2)
    add_para(
        doc,
        "Switch context with Dashboard CAPTIVE / HYBRID tabs (or architecture selector on Economics). "
        "Each profile shows its own stacked tariffs, Architecture Grid% | RE% (Target = Simulated), and feasibility notes.",
    )
    add_heading(doc, "14.4 Reports page", 2)
    add_table(
        doc,
        ["Button", "Output (Model 2.0)"],
        [
            [
                "Export Excel",
                "Summary (feasibility, data quality, config hash, stale flag), Project, Assumptions, "
                "Load/Solar/Wind/BESS/Grid contracts, Monthly, Compliance, Economics (Captive/Hybrid + DISCOM baseline), "
                "LF scenarios, Data Quality, Feasibility (+ binding table), CFE Analytics.",
            ],
            [
                "Export PDF",
                "Executive report with feasibility, data quality, CFE pass mode, TOTAL COST OF DELIVERED ENERGY, "
                "economics basis, binding constraints, GRID-ONLY BASELINE, compliance statuses, stale warning, disclaimer.",
            ],
            [
                "Backup Project",
                "Downloadable project package (inputs/scenarios/model version) for restore without touching SQLite manually.",
            ],
        ],
    )
    add_para(doc, "Report disclaimer (always included):", bold=True)
    add_para(doc, DISCLAIMER, italic=True)

    # 15 Assumptions / methodology / settings
    add_heading(doc, "15. Assumptions, Methodology & Settings", 1)
    add_para(
        doc,
        "The in-app Assumptions and Methodology pages (Reports menu) are the live companion to this chapter. "
        "They refresh from the open project: study period, mix %, Storage tariff, cost blend basis, and compliance targets.",
    )

    add_heading(doc, "15.1 Assumptions register", 2)
    add_para(
        doc,
        "Assumptions is the searchable register of parameters that drive Captive and Hybrid on the commercial "
        "buyer path. The data centre is an energy consumer: Solar / Wind / BESS / DISCOM are contracted "
        "Architecture mix % at fixed ₹/kWh for the bill; hourly CFE uses TOD availability. Generation-plant CAPEX / OPEX, "
        "plant financing, and optimization leftovers are hidden by design.",
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
                "No DISCOM. Selected mix % must sum to 100%. Bill = mix %; CFE = availability.",
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
                "Annual RE / CFE = availability; RPO = Architecture mix. Project Setup → Compliance.",
            ],
            [
                "Financial (results)",
                "Discount rate, electricity / RE escalation, project life",
                "NPV of savings vs DISCOM. No generation-plant debt / CAPEX path.",
            ],
        ],
    )
    add_para(doc, "Bill vs hourly CFE", bold=True)
    add_bullets(
        doc,
        [
            "Bill: Architecture mix % × stacked ₹/kWh (Storage tariff × BESS%).",
            "Hourly: Solar/Wind shapes scaled to annual mix%×load — solar ≈ 0 at night.",
            "BESS: Mix % on the bill; derived storage shifts day RE to night for CFE.",
            "CFE: Min(Load, Solar+Wind+RE-BESS)/Load each hour — not flat Architecture RE%.",
        ],
    )
    add_para(doc, "What drives Dashboard / Economics / Hourly CFE", bold=True)
    add_bullets(
        doc,
        [
            "Both architectures — Captive and Hybrid are analysed in one Run Analysis. Tabs only switch detail view.",
            "Blended ₹/kWh — Discom×G% + Solar×S% + Wind×W% + (BESS×Storage tariff if BESS selected).",
            "Target vs Simulated — Both = Architecture contracted mix % (Grid% | RE%).",
            "Annual RE / hourly CFE — availability (Solar+Wind+RE-BESS). Architecture mix shown for bill reference.",
            "RPO — Architecture RE mix. ESO — load × BESS mix %. Carbon: baseline = load×EF; actual = load×DISCOM%×EF.",
            "Feasibility — Gates on RE/CFE (and Applicable RPO/ESO) — not on plant-profile unserved.",
            "Hidden from the register — generation CAPEX / OPEX, plant MW, plant financing, Optimization leftovers.",
        ],
    )

    add_heading(doc, "15.2 Methodology (detailed — matches in-app page)", 2)
    add_para(
        doc,
        "Methodology documents commercial buyer calculation rules: Architecture mix % for the bill, "
        "TOD/availability for hourly CFE. Summary of sections (full formulas also in §17A and MODEL_METHODOLOGY.md):",
    )
    add_numbered(
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
    )

    add_heading(doc, "15.3 Settings — Share & access", 2)
    add_para(
        doc,
        "Settings has two cards:",
    )
    add_bullets(
        doc,
        [
            "Share & access — This laptop URL and Network URLs (other laptops on the same Wi‑Fi / LAN) "
            "with Copy buttons. Explains that LAN sharing is on by default and that Quit App disconnects everyone. "
            "Use this when you want colleagues to type http://<IP>:<port>/ in their browsers.",
            "Application settings dump — currency (INR), theme, model version and stored settings JSON. "
            "You cannot change core physical/financial equations from this page by design.",
        ],
    )
    add_para(
        doc,
        "If Network URLs are empty, check Wi‑Fi/Ethernet, or confirm you did not start with PTO_HOST=127.0.0.1.",
    )

    doc.add_page_break()

    # 17A Detailed calculations
    add_heading(doc, "17A. Detailed Calculations & Formulas (Model 2.0)", 1)
    add_para(
        doc,
        "This chapter documents how PowerTrain Optimizer calculates every major value you see in the UI, "
        "Excel and PDF. Units: power in MW, energy in MWh (1 MWh = 1,000 kWh), money in ₹. "
        "One model hour = 1 MW sustained for 1 hour → 1 MWh. Commercial billing uses tariff stacks — "
        "not generation-plant CAPEX recovery.",
    )

    add_heading(doc, "17A.1 Time horizon", 2)
    add_bullets(
        doc,
        [
            "Normal year: 8,760 consecutive hours (not a leap year by default).",
            "Leap-year length 8,784 is reserved and not the default.",
            "Financial cash-flows then span project_life_yr years beyond that single 8,760 study year.",
        ],
    )

    add_heading(doc, "17A.2 Synthetic load profile (DC demand)", 2)
    add_para(
        doc,
        "When load.profile_source = SYNTHETIC, an 8,760 demand shape is built from the Load parameters, then scaled. "
        "This shapes data-centre demand only — not Solar/Wind plant CF:",
    )
    add_bullets(
        doc,
        [
            "Start with shape = 1 for every hour (Flat model uses a constant).",
            "Daily Pattern / Custom / Seasonal: multiply by hour_multiplier_0…23 for the hour-of-day.",
            "Weekday/Weekend / Custom: multiply weekdays by weekday_multiplier and weekends by weekend_multiplier.",
            "Seasonal / Custom: multiply by month_multiplier_1…12 for the calendar month.",
            "Target average power: avg = peak_load_mw × (load_factor_pct / 100).",
            "Scale: load_t = shape_t / mean(shape) × avg  (so annual mean ≈ peak × load factor).",
            "If any hour exceeds peak_load_mw, the series is compressed so max(load) ≤ peak.",
            "If operating_hours < 8760, unused hours are set to zero.",
            "CALCULATED base_load_mw = peak_load_mw × load_factor_pct / 100 (labelling helper).",
        ],
    )
    add_para(
        doc,
        "PROJECT DATA: the imported CSV MW series replaces the synthetic generator (must be 8,760 or 8,784 hours; "
        "invalid files are rejected — no silent fallback).",
    )

    add_heading(doc, "17A.3 Solar / Wind / DISCOM — annual contract + hourly shapes", 2)
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
    )

    add_heading(doc, "17A.9 Other KPI formulas", 2)
    add_table(
        doc,
        ["KPI", "Calculation"],
        [
            ["Annual solar / wind MWh", "Σ Solar_t / Σ Wind_t (shapes scaled to mix% × annual load)"],
            ["Grid import MWh / GWh", "Σ Grid_t from dispatch; GWh = MWh / 1,000"],
            ["Annual RE %", "Σ RE serving load / Σ Load × 100 (availability)"],
            ["Hourly CFE (min)", "Min of hourly availability CFE — Pass if ≥ hourly_cfe_target_pct"],
            ["Unserved MWh", "0 commercially; dispatch_unserved_mwh kept for diagnostics"],
            ["BESS (buyer)", "Bill: mix % × Storage tariff; hourly: derived MW/MWh when BESS mix > 0"],
            ["Max grid import MW", "max(Grid_t); demand charge uses Peak × DISCOM%"],
        ],
    )

    add_heading(doc, "17A.10 Internal energy balance (buyer path)", 2)
    add_para(
        doc,
        "Commercial energy identities on the buyer path:",
    )
    add_bullets(
        doc,
        [
            "Mix identity (bill): Solar% + Wind% + BESS% + DISCOM% = 100% for selected assets",
            "Annual contract: Σ Solar / Σ Wind = Load × mix%",
            "Hourly AC balance: Solar + Wind + Discharge + Grid + Unserved ≈ Load + Charge + Curtailment",
            "Commercial unserved_mwh = 0; charts may still show charge/discharge/SOC when BESS mix > 0",
        ],
    )
    add_para(
        doc,
        "Hard validation failures (NaN / non-finite) → MODEL ERROR — do not use the run for decisions.",
    )

    add_heading(doc, "17A.11 Compliance calculations (RPO / RCO / ESO)", 2)
    add_para(
        doc,
        "Applicability gates: Not Applicable → status Not Applicable (no cost). "
        "Unknown / Legal Review Required → LEGAL REVIEW (no Pass). Applicable → Pass/Fail + cost.",
    )
    add_bullets(
        doc,
        [
            "RPO/RCO (single integrated target): actual = Architecture RE % (Solar%+Wind%+BESS%). "
            "Required MWh = Load_MWh × rpo_rco_target_pct/100. Gap = max(0, required − Load×RE%/100). "
            "Buyout cost when Applicable uses configured ₹/kWh.",
            "ESO: required_storage_mwh = Load_MWh × eso_target_pct/100. "
            "Actual = Load_MWh × BESS mix %/100. Contracted BESS treated as 100% RE-origin on the buyer path. "
            "Buyout on shortfall when Applicable.",
            "total_compliance_cost_inr = RPO/RCO cost + ESO cost (year-1 stack).",
        ],
    )

    add_heading(doc, "17A.12 Grid tariff series", 2)
    add_bullets(
        doc,
        [
            "If use_tod = False: every hour uses energy_tariff_inr_per_kwh.",
            "If use_tod = True: hours in [tod_peak_start_hour, tod_peak_end_hour) use tod_peak_tariff; else tod_offpeak_tariff.",
            "Grid energy cost (₹) = Σ (Grid_MW_t × tariff_₹_per_kWh_t × 1,000).",
        ],
    )

    add_heading(doc, "17A.13 Generation-plant CAPEX (not used in buyer UI)", 2)
    add_para(
        doc,
        "The commercial data-centre buyer path sets generation CAPEX and OPEX to zero in ₹/kWh and cash-flows. "
        "Solar, Wind and BESS are priced only through stacked consumer ₹/kWh tariffs (plus optional network lines). "
        "Legacy plant CAPEX parameters are hidden from the Assumptions register.",
    )

    add_heading(doc, "17A.14 Bill blend — TARGET_POWER_PCT vs SIMULATED_ENERGY_SHARE", 2)
    add_bullets(
        doc,
        [
            "TARGET_POWER_PCT: Grid/Solar/Wind/BESS shares = Architecture mix_*_pct for selected assets.",
            "SIMULATED_ENERGY_SHARE: same as Target on the buyer path — Architecture contracted mix % "
            "(no plant MW inventing; Target = Simulated).",
            "Blended ₹/kWh = Discom×G% + Solar×S% + Wind×W% + Storage×B% (DISCOM/Solar/Wind rates from stacked lines).",
            "BESS on Captive/Hybrid: Storage rate = excel_bess_ppa_inr_per_kwh only.",
            "Demand charge = Peak_MW × DISCOM%/100 × demand ₹/MW-month × 12.",
        ],
    )

    add_heading(doc, "17A.15 Commercial energy & network charges (Year 1)", 2)
    add_para(
        doc,
        "Load stack (Excel parity, all structures’ synthetic load): Total facility MW = IT Load × PUE; "
        "Actual average MW = Total × (load_factor_pct/100); annual energy MWh from the 8,760 profile "
        "(≈ Actual × 8,760 when the shape meets the load-factor target).",
    )
    add_bullets(
        doc,
        [
            "DISCOM / Captive / Hybrid Year-1 bill (tariff-stack path):",
            "  — Discom ₹/kWh = stacked DISCOM energy + wheeling + TOD + ED + TOSE",
            "  — Solar / Wind ₹/kWh = stacked PPA + energy + wheeling + transmission + losses + CSS + AS + SLDC + banking + ED + TOSE",
            "  — Storage ₹/kWh = excel_bess_ppa_inr_per_kwh (Captive/Hybrid only)",
            "  — Blended rate from Architecture % or simulated shares (17A.14)",
            "  — Annual bill ₹ = energy + demand + fixed + compliance + additional costs",
            "Demand charge ≈ billing MW × demand_charge_inr_per_mw_month × 12 (billing MW from peak×DISCOM% or max grid import when simulated)",
            "Fixed charge = fixed_charge_inr_per_year (+ meter/LD as configured)",
            "Optional per-asset network ₹/kWh when apply_network_charges_to_* flags are enabled",
            "Carbon: baseline tCO₂ = load×EF; actual = load×DISCOM%/100×EF; saved = baseline−actual. "
            "CFE / Annual RE = Solar%+Wind%+BESS% (firm)",
        ],
    )

    add_heading(doc, "17A.16 TOTAL COST OF DELIVERED ENERGY (₹/kWh)", 2)
    add_para(
        doc,
        "Year-1 total annual cost = Stacked energy bill + Demand + Fixed + Network (if any) + Compliance + Additional costs",
        italic=True,
    )
    add_para(
        doc,
        "₹/kWh = Year-1 total annual cost / (Annual_load_mwh × 1,000)",
        italic=True,
    )
    add_para(
        doc,
        "Label in the UI: TOTAL COST OF DELIVERED ENERGY — not a formal certified LCOE unless your LCOE standard "
        "matches these annualisation assumptions.",
    )

    add_heading(doc, "17A.17 Multi-year cash-flows & NPV of power bill", 2)
    add_para(doc, "Buyer cash-flows (cost framing — no plant CAPEX at Year 0):", bold=True)
    add_bullets(
        doc,
        [
            "Year 0: CF_0 = 0 (no generation-plant investment in commercial buyer mode)",
            "Year y = 1…N: escalate grid portion by electricity_escalation_pct; "
            "demand/fixed/compliance by inflation_pct; RE/storage portions by re_cost_escalation_pct",
            "CF_y = −(annual power bill_y) including additional costs and compliance",
        ],
    )
    add_para(
        doc,
        "NPV = Σ_t CF_t / (1 + r)^t    with r = discount_rate_pct/100, t = 0…N",
        italic=True,
    )
    add_para(
        doc,
        "IRR = rate that sets NPV(CF) = 0 (Newton then bisection). Shown as %; blank/— if undefined "
        "(e.g. all-negative DISCOM cost stack).",
    )
    add_para(
        doc,
        "Payback = first time cumulative cash-flow crosses from negative to non-negative (fractional year).",
    )
    add_para(doc, "npv_cr = npv_inr / 1e7  (₹ Crore display helper).", italic=True)

    add_heading(doc, "17A.18 Savings vs DISCOM & NPV of savings", 2)
    add_para(
        doc,
        "Each Run Analysis includes a parallel DISCOM GRID-ONLY BASELINE (same load, LF scenario, grid tariffs). "
        "For Captive and Hybrid:",
    )
    add_bullets(
        doc,
        [
            "Year-y savings_inr = DISCOM_annual_bill_y − architecture_annual_bill_y",
            "Savings cash-flows: CF_0 = 0; CF_y = savings_y (no Δ plant CAPEX)",
            "NPV of savings = Σ_t CF_t / (1 + r)^t with r = financial.discount_rate_pct / 100",
            "Dashboard/Economics NPV ₹ Cr for Captive/Hybrid reflects this savings series unless noted otherwise",
            "DISCOM column shows reference bill only — not a selectable architecture",
        ],
    )

    add_heading(doc, "17A.19 Feasibility (informational)", 2)
    add_bullets(
        doc,
        [
            "FEASIBLE when enabled RE/CFE (and Applicable RPO/ESO) checks pass and there is no MODEL ERROR.",
            "INCOMPLETE INPUTS when editable DEFAULT_ASSUMPTION values remain.",
            "LEGAL REVIEW REQUIRED when RPO/RCO/ESO applicability needs legal input.",
            "Feasibility does not auto-select Captive vs Hybrid and does not show RECOMMENDED tags.",
        ],
    )

    add_heading(doc, "17A.20 Load-factor scenarios", 2)
    add_para(
        doc,
        "load_factor_s1_pct … s4_pct define up to four scenarios. Each Run Analysis loops scenarios, "
        "but headline Dashboard KPIs and the comparison table use S1. Exports include all scenario summaries.",
    )

    add_heading(doc, "17A.21 Config fingerprint", 2)
    add_para(
        doc,
        "Each run stores a SHA-256 hash of the normalised project configuration (Reports / audit). "
        "Changing inputs increments input_version; mismatched versions mark results STALE until you re-run analysis.",
    )

    add_heading(doc, "17A.22 Display formatting (not a model change)", 2)
    add_para(
        doc,
        "On-screen Lakh / Cr formatting only changes how numbers are printed. Underlying calculations "
        "and Excel numeric cells use full precision. Under 1 Lakh → full digits; then Lakh; then Cr. "
        "Chart axes use compact k / Lakh / Cr tick labels with extra left padding for the axis title.",
    )

    doc.add_page_break()

    # 18 Workflow
    add_heading(doc, "16. End-to-End Workflow (Commercial Buyer)", 1)
    add_numbered(
        doc,
        [
            "Launch EXE (Chrome opens Start) or open Network URL on a shared host → Create New Project "
            "(or Open Existing Project… .pto.zip).",
            "Optional: Settings → note Network URL for LAN colleagues; Save Project for a local .pto.zip backup.",
            "Project Setup: configure Captive and Hybrid (assets, mix % sum 100%, tariff stacks, Storage ₹/kWh), "
            "Load (S1–S4 LF scenarios), Grid/DISCOM tariffs, Compliance (RPO/RCO/ESO single targets, hourly CFE), "
            "Financial (discount rate, escalations, Additional costs).",
            "Optional: upload PROJECT DATA CSVs on Load/Solar/Wind steps; confirm Data Quality badges.",
            "Review Assumptions register for remaining buyer-facing defaults.",
            "Run 8760 Simulation → Dashboard: compare Captive vs Hybrid + DISCOM baseline (S1 KPIs).",
            "If NOT FEASIBLE, read binding constraints; adjust Compliance or contracts in Project Setup.",
            "Hourly CFE → TOD availability charts (night solar ~0); Economics → Target = Simulated bill mix.",
            "Reports → Export Excel/PDF; Save Project / Backup .pto.zip for colleagues.",
            "Independent legal review of RPO/RCO/ESO applicability before decisions.",
            "Quit App (or close Chrome tab) when finished so the host EXE exits.",
        ],
    )

    # 19 Interpreting results
    add_heading(doc, "17. Interpreting Results Correctly", 1)
    add_bullets(
        doc,
        [
            "Compare Captive vs Hybrid directly on the Dashboard — the app does not pick a RECOMMENDED winner.",
            "Unserved energy > 0 means load was not fully met — treat as NOT FEASIBLE for reliability.",
            "High Annual RE with low min Hourly CFE means energy is green on average but not 24×7.",
            "Read CFE Pass Mode carefully — All hours ≥ target is much stricter than Mean or Share-of-hours.",
            "DISCOM ₹/kWh is the GRID-ONLY BASELINE for savings and NPV — not a selectable green architecture.",
            "NPV ₹ Cr is NPV of bill savings vs DISCOM, not recovery of solar/wind plant CAPEX.",
            "Pass/Fail on compliance depends on applicability and single RPO/RCO/ESO targets — Unknown is not Pass.",
            "INCOMPLETE INPUTS means defaults remain — suitable for screening, not board packs.",
            "STALE RESULTS means inputs changed after the run — re-run before exporting.",
            "MODEL ERROR → do not use the run.",
            "SYNTHETIC profiles are generated from Setup parameters; use PROJECT DATA for site-specific shapes.",
            "Architecture mix % must sum to 100% per profile before save/simulation.",
            "Headline KPIs use LF scenario S1 unless you inspect other scenarios in exports.",
            "When sharing over LAN, everyone edits the same host database — coordinate saves.",
        ],
    )

    # 20 Data
    add_heading(doc, "18. Data Storage, Backup & Persistence", 1)
    add_bullets(
        doc,
        [
            "SQLite database auto-created on first launch (typically under %LOCALAPPDATA%\\PowerTrainOptimizer for the EXE).",
            "ACCESS_URLS.txt is written on each launch (LocalAppData and beside the EXE) with This PC + Network URLs.",
            "Projects, inputs, scenarios, settings and run metadata persist across restarts.",
            "Save Project / Backup Project write a portable .pto.zip you can store anywhere and later restore via Open Existing Project….",
            "Hourly arrays for saved runs are stored efficiently (e.g. under data/runs as NPZ), not as 8,760 SQL rows.",
            "Internal energy-balance JSON may be stored beside the run for audit exports (no Ledger UI page).",
            "Imported PROJECT DATA profiles are stored under data/profiles/project_<id>/.",
            "Before schema migrations the app backs up the database automatically.",
            "To distribute the app itself (not project data), copy dist\\PowerTrain_Share\\ or the standalone EXE.",
        ],
    )

    # 21 Troubleshooting
    add_heading(doc, "19. Troubleshooting", 1)
    add_table(
        doc,
        ["Symptom", "What to do"],
        [
            ["Browser does not open", "Wait ~30–60 s on first launch. If still closed, Task Manager may show PowerTrainOptimizer.exe — Quit App or end it and relaunch. Open http://127.0.0.1:8765/ manually, or read ACCESS_URLS.txt. Developer mode: check the terminal."],
            ["Port already in use / multiple EXEs", "Quit App (clears orphans) or end PowerTrainOptimizer.exe in Task Manager; relaunching an already-live instance reopens the UI instead of stacking servers."],
            ["EXE keeps running after closing browser", "Should stop within a few seconds. If not, use Quit App or Task Manager. Rebuild to the latest EXE if you are on an older keep-alive build."],
            ["Cannot overwrite EXE while building", "Quit App / end PowerTrainOptimizer.exe first — Windows locks dist\\PowerTrainOptimizer.exe while it is running."],
            ["Colleague cannot open Network URL", "Same Wi‑Fi/LAN? Firewall allowed Private? Host EXE still running with a UI heartbeat or guest tab open? Correct IP:port from Settings / ACCESS_URLS.txt? Guest Wi‑Fi isolation off?"],
            ["Network URLs empty in Settings", "No LAN IP detected, or PTO_HOST=127.0.0.1. Connect Ethernet/Wi‑Fi and restart the EXE."],
            ["Opens Edge instead of Chrome", "Install Chrome, or set PTO_BROWSER=chrome. Use PTO_BROWSER=edge|default to force Edge / system browser."],
            ["Unhandled exception … isatty / Unable to configure formatter", "You are on an old windowed EXE. Use the rebuild that redirects stdout/stderr and uses a safe uvicorn log config."],
            ["Slow first open", "Normal on cold start (unpack + DB create). Later launches reuse the DB and should be faster."],
            ["Annual RE / Hourly CFE show Fail on demo", "Expected under default 90% targets with strict All-hours CFE mode. Raise BESS/wind, lower targets, or change CFE pass mode in Project Setup → Compliance."],
            ["Dashboard says NOT FEASIBLE but costs look fine", "Feasibility is target-driven. Read binding constraints; compare Captive vs Hybrid on merit."],
            ["Where is the Compliance menu?", "Under Project Setup → Compliance (removed from Analysis nav). Dashboard has a shortcut link."],
            ["DISCOM shows 0% RE/CFE and — for IRR/Payback", "Expected: DISCOM is GRID-ONLY BASELINE (no RE assets). IRR/Payback apply to investment cases vs DISCOM."],
            ["STALE RESULTS banner", "Inputs changed after the last run — click Run 8760 Simulation again."],
            ["MODEL ERROR: PROJECT DATA … no profile", "Upload CSV on Project Setup Load/Solar/Wind or set profile_source back to SYNTHETIC."],
            ["CSV upload rejected", "Check length (8760/8784), no negatives/NaNs, fix duplicate timestamps; there is no silent fallback."],
            ["MODEL ERROR: power balance", "Report the hour index; indicates an internal dispatch inconsistency (should not occur on released builds)."],
            ["Run Analysis feels slow", "Four LF scenarios × Captive/Hybrid × DISCOM baseline — normal for full-year dispatch; wait for completion."],
            ["Dashboard empty", "Click Run 8760 Simulation."],
            ["Charts empty on Hourly CFE page", "Run simulation first, then choose Time window and click Show charts."],
            ["Percentage of power must sum to 100% / cannot Save", "In Project Setup Captive or Hybrid section, adjust mix % so Total = 100%. Uncheck unused assets."],
            ["Chart Y-axis shows “housand” or overlaps Energy (MWh)", "Hard-refresh Ctrl+F5 or relaunch latest EXE — axes now use k/Lakh/Cr with wider left margin."],
            ["Numbers look like long digit strings", "Hard-refresh Ctrl+F5 or relaunch latest EXE — UI should show Lakh / Cr for large values."],
            ["What does SYNTHETIC / Defaults left mean?", "SYNTHETIC = generated 8,760 profile (not uploaded CSV). Defaults left = count of parameters still on built-in defaults. See Section 10."],
            ["Parameter meaning unclear", "Read the grey help text under each field title; full list also in Assumptions and Section 9 of this guide."],
            ["UI looks old / charts not updated", "Hard-refresh the browser (Ctrl+F5) or relaunch the latest Model 2.0 EXE."],
            ["Default still 100 MW / Model 1.0.0", "You are on an old database/EXE — use the Model 2.0 rebuild, or Create New Project from current defaults."],
            ["Need to reset / transfer a project", "Create New Project, or Open Existing Project… with a .pto.zip from Save Project / Backup Project."],
            ["How do I give the app to someone else?", "Copy dist\\PowerTrain_Share\\ (or just the EXE + HOW_TO_SHARE.txt). No install required."],
        ],
    )

    # 22 Glossary
    add_heading(doc, "20. Glossary", 1)
    add_table(
        doc,
        ["Term", "Definition in this tool"],
        [
            ["8,760 / 8,784", "Hours in a non-leap / leap year; model resolution for profiles"],
            ["Annual RE %", "Share of annual load energy served by renewable (incl. RE-origin BESS discharge)"],
            ["Hourly CFE %", "Hourly carbon-free energy share of load"],
            ["CFE pass mode", "Rule used to Pass/Fail hourly CFE (all hours / mean / share of hours)"],
            ["CFE analytics", "Deficit streak, % hours ≥ target, duration-curve stats attached to KPIs"],
            ["BESS", "Battery Energy Storage System — power_mw caps charge & discharge; η_c / η_d from charge/discharge efficiency"],
            ["SOC", "State of charge (MWh or %)"],
            ["Curtailment", "Renewable energy that could not serve load or charge BESS"],
            ["Config hash", "SHA-256 fingerprint of configuration used for a run"],
            ["Feasibility", "Pass/Fail for RE/CFE (and Applicable RPO/ESO) — does not pick Captive vs Hybrid"],
            ["Binding constraint", "Primary reason a case fails feasibility (e.g. HOURLY_CFE)"],
            ["STALE", "Results older than current project input_version"],
            ["SYNTHETIC", "8,760-hour Load/Solar/Wind series generated from Setup parameters (not an uploaded CSV)"],
            ["PROJECT DATA", "Imported validated hourly MW CSV (8,760 or 8,784 hours) on Project Setup steps"],
            ["Defaults left", "Count of editable parameters still marked DEFAULT_ASSUMPTION on the Data Quality card"],
            ["PRELIMINARY", "Data-quality badge when profiles are not all PROJECT DATA and/or defaults remain"],
            ["DISCOM", "GRID-ONLY BASELINE commercial structure (solar/wind/BESS forced to 0)"],
            ["Captive", "Captive / group captive commercial structure (Solar / Wind / BESS selectable)"],
            ["Hybrid", "DISCOM backup + contracted Solar/Wind/BESS Storage — analysed equally with Captive"],
            ["Storage tariff", "Single BESS ₹/kWh (excel_bess_ppa_inr_per_kwh) on Captive/Hybrid buyer path"],
            ["Load-factor scenario", "S1–S4 LF %; headline KPIs use S1"],
            ["RPO", "Renewable Purchase Obligation"],
            ["RCO", "Renewable Consumption Obligation (applicability may need legal review)"],
            ["ESO", "Energy Storage Obligation"],
            ["NPV of savings", "Present value of annual bill savings vs DISCOM at discount_rate_pct (no plant CAPEX at Year 0)"],
            ["TOTAL COST OF DELIVERED ENERGY", "₹/kWh = Year-1 power bill / load energy (tariff stacks)"],
            ["Savings vs DISCOM", "Year-1 DISCOM baseline bill minus Captive/Hybrid bill (₹ Cr)"],
            ["cost_blend_basis", "TARGET_POWER_PCT or SIMULATED_ENERGY_SHARE — both = Architecture contracted mix %"],
            ["Quit App", "Sidebar control that stops the server and background PowerTrain processes (disconnects LAN users)"],
            ["Save Project", "Top-bar action that saves inputs and writes a portable .pto.zip to a folder you choose"],
            [".pto.zip", "Portable project backup/restore archive (Open Existing Project… / Backup Project)"],
            ["Asset selection", "include_discom / include_solar / include_wind / include_bess flags that gate Setup tabs and capacities"],
            [
                "Percentage of power / mix %",
                "mix_discom_pct / mix_solar_pct / mix_wind_pct / mix_bess_pct — Architecture contract shares; "
                "selected assets must sum to 100%",
            ],
            ["Additional costs", "Named annual ₹ line items under Financial included in delivered-energy cost"],
            ["LAN / Network URL", "http://<host-LAN-IP>:<port>/ so other PCs on the same network can use the host’s running app"],
            ["ACCESS_URLS.txt", "File written on launch with This PC and Network URLs"],
            ["Lakh / Cr / k display", "Compact UI format: full digits under 1 Lakh; Lakh; Cr; chart axes use k / Lakh / Cr"],
            ["Time window", "Hourly CFE control: Full year / One month / One week / One day"],
            ["Parameter help", "Short explanation shown under each editable field title in the UI"],
            ["PTO_HOST", "Optional env var; 0.0.0.0 = LAN share (default), 127.0.0.1 = this PC only"],
            ["PTO_BROWSER", "Optional env var; chrome (default) | edge | default — which browser the launcher opens"],
        ],
    )

    add_heading(doc, "23. Document Control", 1)
    add_para(doc, f"Application model version: {MODEL_VERSION}")
    add_para(
        doc,
        "Companion files: README.md, ARCHITECTURE.md, MODEL_METHODOLOGY.md, ASSUMPTIONS.md, "
        "docs/API.md, docs/V2_IMPLEMENTATION_MAP.md, docs/HOW_TO_SHARE.txt",
    )
    add_para(doc, "This revision of the User Guide documents (in detail):", bold=True)
    add_bullets(
        doc,
        [
            "Commercial DC buyer: tariff-stack bills, no generation-plant CAPEX in UI or NPV",
            "Captive + Hybrid equal analysis; DISCOM baseline only; no RECOMMENDED tags",
            "Navigation: Dashboard, Project Setup, Economics, Hourly CFE, Reports, Assumptions, Methodology, Settings",
            "Mix %, cost_blend_basis, Storage tariff, four LF scenarios (S1 headline KPIs)",
            "Compliance under Project Setup (RPO/RCO/ESO single targets, hourly CFE)",
            "Assumptions register hides plant-leftover parameters",
            "NPV of savings vs DISCOM; Section 17A formulas updated",
            "Create/Open/Save .pto.zip; portable EXE and LAN sharing",
        ],
    )
    add_para(
        doc,
        "Regenerate this file anytime with: python scripts/generate_user_guide.py "
        "→ docs/PowerTrain_Optimizer_User_Guide.docx (also packaged into dist/PowerTrain_Share when you run package_share.bat).",
        italic=True,
        size=10,
    )
    add_para(doc, DISCLAIMER, italic=True, size=10)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"Wrote {OUT}")
    dist_dir = ROOT / "dist"
    if dist_dir.is_dir():
        import shutil

        dist_doc = dist_dir / OUT.name
        shutil.copy2(OUT, dist_doc)
        print(f"Copied to {dist_doc}")


if __name__ == "__main__":
    build()
