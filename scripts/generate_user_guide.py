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
        "Techno-Economic 8,760-Hour Power Architecture Tool\n"
        "for Data Centre · Solar · Wind · BESS · Grid\n"
        "Includes: portable EXE · LAN sharing · Save Project (.pto.zip) · architecture asset selection · "
        "simplified BESS · compact Indian number format · on-screen parameter help"
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
            "Commercial architectures, selectable assets & recommendation rules",
            "Compliance (RPO / RCO / ESO / RE / CFE) — edited in Project Setup",
            "Profiles — optional PROJECT DATA CSV import",
            "Running the 8,760-hour simulation, charts & Energy Ledger",
            "How numbers are displayed (Thousand / Lakh / Cr)",
            "Feasibility status & binding constraints",
            "Optimization, explainability & marginal analysis",
            "Scenarios & sensitivity",
            "Economics (incremental vs DISCOM) & reports",
            "Assumptions, methodology & Settings (Share & access)",
            "Detailed calculations & formulas (profiles, dispatch, RE/CFE, costs, NPV/IRR, ledger)",
            "Recommended end-to-end workflow",
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
        "PowerTrain Optimizer is a local Windows desktop application with a browser-based interface. "
        "It performs genuine 8,760-hour techno-economic simulation and capacity optimization for a "
        "Data Centre power architecture supplied by Solar, Wind, BESS and Grid.",
    )
    add_para(doc, "It evaluates:")
    add_bullets(
        doc,
        [
            "Annual Renewable Energy percentage (Annual RE %)",
            "Hourly Carbon-Free Energy percentage (Hourly CFE %) with configurable pass modes and CFE analytics",
            "Four commercial structures: DISCOM (GRID-ONLY BASELINE), Captive / Group Captive, Hybrid, Open Access",
            "RPO, RCO and ESO compliance indicators (with legal-applicability gates)",
            "Feasibility status and binding-constraint diagnosis (RECOMMENDED only when FEASIBLE)",
            "Energy Ledger reconciliation and config fingerprint",
            "TOTAL COST OF DELIVERED ENERGY (₹/kWh), incremental NPV/IRR/payback vs DISCOM",
            "Architecture comparison, scenario management, sensitivity and optimization explainability",
            "Optional PROJECT DATA 8,760-hour profile import (Load / Solar / Wind)",
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
            "Not an investment recommendation engine that can label infeasible architectures as RECOMMENDED.",
        ],
    )
    add_heading(doc, "2.2 Critical design rules", 2)
    add_bullets(
        doc,
        [
            "Synthetic profiles remain the default — no mandatory file uploads for load, solar or wind.",
            "Optional PROJECT DATA CSV import (exactly 8,760 or 8,784 hours) is available under Profiles; invalid files are rejected with no silent substitution.",
            "No external database server — embedded SQLite only.",
            "End users do not need Python, Node.js, Docker or admin rights.",
            "Every default number is labelled DEFAULT ASSUMPTION unless it comes from the concept note.",
            "All KPIs are calculated by the model — never hard-coded.",
            "Architectures are never labelled RECOMMENDED if feasibility fails (RE/CFE/unserved/legal gates as configured).",
            "DISCOM is a GRID-ONLY BASELINE comparator (solar/wind/BESS forced to 0).",
            "After you change inputs, prior results are marked STALE until you re-run the 8,760 simulation.",
            "Energy Ledger must reconcile annually and monthly; MODEL ERROR is raised on hard balance failures.",
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
                "Energy Ledger",
                "Annual + monthly flow table (solar/wind → load/BESS/curtail; BESS origin splits; grid; unserved) "
                "with reconciliation status. Page: Energy Ledger. Excel sheet: Energy Ledger / Ledger Monthly.",
            ],
            [
                "Config fingerprint",
                "SHA-256 config hash stored with each run. Shown on Energy Ledger. Used for audit trail.",
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
                "can_recommend is true only when status = FEASIBLE. Binding constraints list code, message, remedies.",
            ],
            [
                "Recommendation rules",
                "Dashboard architecture card shows RECOMMENDED only if feasible. Otherwise shows status "
                "(e.g. NOT FEASIBLE) and “Why not recommended.” DISCOM is labelled GRID-ONLY BASELINE.",
            ],
            [
                "Optimization explainability",
                "Why-this-configuration bullets, nearby alternatives with why-not text, no-feasible detail with "
                "primary binding constraint. Optional Marginal Capacity Steps (±solar/wind/BESS).",
            ],
            [
                "Incremental economics",
                "Economics page shows GRID-ONLY BASELINE (DISCOM) and Incremental vs DISCOM (Δ CAPEX, Δ OPEX, "
                "NPV/IRR/payback). Non-DISCOM project NPV/IRR/payback use incremental cashflows.",
            ],
            [
                "Cost label",
                "₹/kWh is TOTAL COST OF DELIVERED ENERGY (annualised cost / load energy) — not a formal LCOE certificate.",
            ],
            [
                "Project data profiles",
                "Profiles menu: upload/clear Load, Solar, Wind CSVs. profile_source = SYNTHETIC | PROJECT DATA. "
                "Missing/invalid PROJECT DATA raises MODEL ERROR (no silent fallback).",
            ],
            [
                "Data quality card",
                "Dashboard shows Load/Solar/Wind source badges and count of remaining default assumptions / critical defaults.",
            ],
            [
                "Reports",
                "Excel adds Data Quality, Feasibility, Energy Ledger, CFE Analytics, incremental economics. "
                "PDF includes feasibility, CFE pass mode, DISCOM baseline, binding constraints, stale warning.",
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
                "Architecture asset selection",
                "DISCOM: DISCOM/grid only. CAPTIVE: Solar / Wind / BESS. HYBRID & OPEN_ACCESS: DISCOM + Solar + "
                "Wind + BESS. Unselected assets are zeroed in simulation; Project Setup tabs follow the selection.",
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
                "Simplified BESS inputs",
                "Charge efficiency, Discharge efficiency, Max charge power and Max discharge power are removed. "
                "BESS power (MW) is both the charge and discharge limit; conversion efficiency is ideal (100%). "
                "BESS losses MWh = 0. SOC_t = SOC_(t−1) + Charge_t − Discharge_t within min/max SOC.",
            ],
            [
                "On-screen parameter help",
                "Every editable field shows a plain-language title plus a short explanation under the label "
                "(from the model description), not only a cryptic snake_case name.",
            ],
            [
                "Compact number display",
                "KPIs and tables keep at most ~5 digits: values under 1 Lakh show in full; larger values use "
                "Lakh / Cr (₹ prefixed for money). Chart axes may also use Thousand for short labels.",
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
            "If no UI heartbeats arrive for ~45 seconds, the process exits as a safety net.",
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
            "Click Run 8760 Simulation in the top bar.",
            "On the Dashboard, first read Feasibility, Data Quality and CFE Pass Mode cards — then the KPI row.",
            "Check whether the architecture card says RECOMMENDED or NOT FEASIBLE / other status (demo often fails strict 90% CFE).",
            "Open Energy Ledger and confirm reconciliation status is OK.",
            "Open Project Setup: pick Architecture assets, edit Load/Solar/Wind/BESS/Grid, Compliance and Financial "
            "(including Additional costs). Setup tabs follow selected assets.",
            "After any input change, click Save Project again if you want the .pto.zip updated, then re-run "
            "simulation if you see a STALE RESULTS banner.",
            "Optionally run Optimization, Architecture Comparison, Sensitivity, then export Excel/PDF from Reports "
            "(or Backup Project .pto.zip).",
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
            ["IT / peak load", "250 MW"],
            ["Load factor", "80% (base ≈ 200 MW)"],
            ["Solar", "450 MW @ 22% CF"],
            ["Wind", "300 MW @ 32% CF"],
            ["BESS", "150 MW / 600 MWh"],
            ["Grid max import", "250 MW @ 220 kV"],
            ["Commercial structure", "HYBRID"],
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
            "Commercial structure pill (e.g. HYBRID Architecture)",
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
            "Executive results home after a simulation (Model 2.0 layout). Top row: Feasibility card "
            "(status + primary issue + binding constraints), Data Quality card (Load/Solar/Wind source, "
            "defaults remaining, critical defaults), and CFE Pass Mode card (mode, target, min hour, "
            "% hours ≥ target, longest deficit streak). Then enlarged KPI cards; monthly energy stacked chart; "
            "hourly CFE heatmap (0–100% coral→amber→teal with target tick); cost and energy donuts; "
            "architecture status card (RECOMMENDED only if feasible — otherwise NOT FEASIBLE / other status; "
            "DISCOM shown as GRID-ONLY BASELINE); scenario comparison with feasibility-aware RECOMMENDED "
            "label; compliance Pass/Fail with Why Fail? and a link Open Project Setup → Compliance; recent runs. "
            "STALE RESULTS banner when inputs changed. "
            "If no simulation has been run yet, prompts you to click Run 8760 Simulation.",
        ),
        (
            "Project Setup",
            "Guided wizard covering General, Data Centre, Load, selected asset steps (Solar/Wind/BESS/Grid per "
            "Architecture checkboxes), Commercial, Compliance, Financial (incl. Additional costs), and Optimization. "
            "Progress bar and step chips follow the selected assets. Buttons: Back, Save Section, Next / Finish. "
            "Load/Solar/Wind steps include profile_source (SYNTHETIC | PROJECT DATA).",
        ),
        (
            "Load",
            "Direct editor for the data-centre load model (peak, load factor, shape multipliers, profile_source).",
        ),
        (
            "Profiles",
            "Optional PROJECT DATA import for Load, Solar and Wind. Upload a CSV with exactly 8,760 (or 8,784 leap) "
            "hourly MW values. Validation rejects wrong length, NaN/Inf, negatives, and duplicate timestamps. "
            "On success, profile_source is set to PROJECT DATA. Clear returns to SYNTHETIC. Invalid files are "
            "never silently replaced by synthetic data — simulation raises MODEL ERROR if PROJECT DATA is selected "
            "but the file is missing/invalid.",
        ),
        (
            "Solar",
            "Direct editor for solar capacity, CF, diurnal/seasonal factors, CAPEX/OPEX, energy cost and profile_source.",
        ),
        (
            "Wind",
            "Direct editor for wind capacity, CF, monthly factors, CAPEX/OPEX, energy cost and profile_source.",
        ),
        (
            "BESS",
            "Direct editor for battery power (MW) and energy (MWh), SOC window (initial/min/max), degradation, "
            "CAPEX/OPEX, replacement and allow-grid-charge. Power rating is both max charge and max discharge; "
            "charge/discharge efficiencies are not user inputs (modelled as 100%).",
        ),
        (
            "Grid",
            "Direct editor for interconnection voltage, import limit, tariffs (incl. TOD), demand/fixed charges "
            "and DISCOM/grid network charges (when the DISCOM asset and network flag are enabled).",
        ),
        (
            "Architecture",
            "Select commercial structure (DISCOM / CAPTIVE / HYBRID / OPEN_ACCESS), tick which assets are in scope "
            "(DISCOM-only for DISCOM; Solar/Wind/BESS for Captive; DISCOM+Solar+Wind+BESS for Hybrid/OA), "
            "edit commercial parameters filtered by structure/assets, and run Architecture Comparison. "
            "Comparison highlights RECOMMENDED only among feasible architectures; DISCOM remains GRID-ONLY BASELINE.",
        ),
        (
            "8760 Simulation",
            "Hourly chart workspace. Choose a clear Time window (Full year overview / One month / One week / "
            "One day), pick Month and Day of month when needed, then Show charts for Load/Solar/Wind, "
            "BESS charge/discharge/SOC, grid/curtailment and hourly CFE, plus a monthly energy-balance table. "
            "A live hint explains what each window displays.",
        ),
        (
            "Energy Ledger",
            "Audit view of annual and monthly energy flows after a simulation: solar/wind generation split to "
            "load / BESS / curtailment; BESS charge by origin; BESS discharge by solar/wind/grid origin; "
            "grid→load/BESS; unserved; reconciliation gaps (solar identity, wind identity, load identity, AC balance). "
            "Shows config hash. Use this to prove the dispatch balances before presenting economics.",
        ),
        (
            "Optimization",
            "Set objective, search mode, capacity bounds and constraint flags, then run staged capacity optimization "
            "(each candidate is a full 8,760 evaluation). Shows live progress, top feasible solutions, "
            "WHY THIS CONFIGURATION? bullets, nearby alternatives, and optional Marginal Capacity Steps.",
        ),
        (
            "Scenarios",
            "Save the current inputs as a named scenario; load, run, or delete scenarios. Default scenarios are "
            "seeded for DISCOM 90% RE, Captive 95% RE, Hybrid 95% RE / 99% CFE, OA 99% RE / 100% CFE.",
        ),
        (
            "Sensitivity",
            "Runs ±20% tornado analysis on key cost/capacity drivers and a two-variable matrix (solar × BESS energy).",
        ),
        (
            "Economics",
            "TOTAL COST OF DELIVERED ENERGY ₹/kWh, annual cost, CAPEX, NPV/IRR/payback; GRID-ONLY BASELINE (DISCOM) "
            "panel; Incremental vs DISCOM panel (Δ CAPEX, Δ OPEX Y1, incremental NPV/IRR/payback); cost breakdown chart.",
        ),
        (
            "Reports",
            "Export Excel workbook (incl. Energy Ledger, Feasibility, Data Quality, CFE Analytics, incremental economics), "
            "PDF executive report (feasibility + binding constraints + DISCOM baseline), or Backup Project (.pto.zip).",
        ),
        (
            "Assumptions",
            "Searchable/filterable register of every parameter with value, unit, source and description.",
        ),
        (
            "Methodology",
            "In-app Model 2.0 summary: synthetic vs PROJECT DATA profiles, power balance, SOC/origin tracking, "
            "RE%/CFE, feasibility/recommendation rules, incremental economics, optimization stages. "
            "The User Guide Section 17A expands every formula in detail.",
        ),
        (
            "Settings",
            "Share & access card shows This laptop URL and Network URLs for LAN colleagues (with Copy). "
            "Also displays application settings (currency, theme, model version, runtime). "
            "Core equations are not editable here.",
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
        "Open Project Setup. A progress bar and step chips show where you are. The middle asset steps "
        "(Solar / Wind / BESS / Grid) appear only when those assets are selected under Architecture. "
        "Always click Save Section (or Next, which also saves) before leaving a step if you changed values. "
        "Use top-bar Save Project when you want a portable .pto.zip on disk.",
    )
    steps = [
        ("1. General", "Project name, location label, currency, model hours (8760), calendar year, random seed, notes."),
        ("2. Data Centre", "Facility name, IT capacity (MW), grid connection kV (concept note: 220 kV), designated-consumer status."),
        (
            "3. Load",
            "profile_source (SYNTHETIC | PROJECT DATA), peak load, load factor, load model type, weekday/weekend multipliers, "
            "month and hour multipliers. If PROJECT DATA, import the CSV under Profiles before simulating.",
        ),
        (
            "4–7. Asset steps (conditional)",
            "Solar / Wind / BESS / Grid editors appear according to Architecture asset checkboxes. "
            "DISCOM structure shows Grid (DISCOM) only; Captive shows Solar/Wind/BESS; Hybrid and Open Access can show all four.",
        ),
        (
            "Commercial / Architecture",
            "Structure selection, include_* asset flags, and structure-specific ownership/price/network flags "
            "(network charge sections appear per selected asset when each apply_network_charges_to_* flag is True).",
        ),
        (
            "Compliance",
            "RPO/RCO/ESO applicability and targets, Annual RE and Hourly CFE targets and pass mode (drives feasibility). "
            "This is the only place to edit compliance inputs (removed from the Analysis nav).",
        ),
        (
            "Financial",
            "Project life, discount rate, inflation, escalations, residual value, optional financing flags, "
            "and Additional costs (named annual ₹ line items included in Year-1 cost, ₹/kWh and cashflows).",
        ),
        ("Optimization", "Objective, dispatch mode, search effort, capacity bounds, constraint toggles, balanced weights."),
    ]
    for title, text in steps:
        add_heading(doc, title, 2)
        add_para(doc, text)
    add_para(
        doc,
        "Tip: The dedicated Load / Solar / Wind / BESS / Grid menus edit the same data as wizard steps 3–7. "
        "Use Profiles for CSV import. Use whichever is more convenient.",
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
        "On Project Setup and every direct editor page (Load, Solar, Wind, BESS, Grid, Architecture, "
        "Compliance, Optimization, etc.), each field is shown as:",
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
        "Set profile_source = PROJECT DATA and import a CSV under Profiles to use measured/forecast series instead. "
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
        "When profile_source = SYNTHETIC, generation is zero at night, peaks near peak_generation_hour, and is scaled to the target CF. "
        "PROJECT DATA replaces the synthetic series with your imported MW profile (scaled/capacities still apply as configured).",
        rows,
    )
    section_params(
        doc,
        "wind",
        "9.5 Wind",
        "When profile_source = SYNTHETIC, wind uses monthly factors and deterministic variability seeded by general.random_seed. "
        "PROJECT DATA uses the imported hourly MW series.",
        rows,
    )
    section_params(
        doc,
        "bess",
        "9.6 BESS",
        "Physical battery model with power rating (caps both charge and discharge), energy capacity, SOC window, "
        "and renewable-origin tracking for ESO. Conversion efficiency is ideal (100%) — charge/discharge efficiency "
        "and separate max charge/discharge power inputs are not used.",
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
        "Controls which commercial cost stack is applied and how RE is priced.",
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
        "Cash-flow horizon and discounting. Financing fields are optional (default: financing disabled).",
        rows,
    )
    section_params(
        doc,
        "optimization",
        "9.11 Optimization parameters",
        "Search bounds and feasibility constraints for capacity optimization.",
        rows,
    )

    doc.add_page_break()

    # 10 Source tags
    add_heading(doc, "10. Understanding Source Tags & Data Quality", 1)
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
        "Each on-screen field shows: Parameter name · Value · Unit · Source badge · ⓘ description tooltip.",
    )
    add_heading(doc, "10.1 Data quality labels (Dashboard)", 2)
    add_table(
        doc,
        ["Label", "Meaning"],
        [
            ["SYNTHETIC", "Profile came from the parameterized generator (default)."],
            ["PROJECT DATA", "Profile came from a validated imported 8,760/8,784 CSV."],
            ["PRELIMINARY", "Overall data-quality badge when not all of Load/Solar/Wind are PROJECT DATA (typical demo)."],
            ["PROJECT DATA ANALYSIS", "All three of Load/Solar/Wind are PROJECT DATA."],
            ["Defaults remaining", "Count of editable parameters still marked DEFAULT_ASSUMPTION."],
            ["Critical defaults", "High-impact defaults still present (e.g. peak load, CFs, tariffs, CAPEX, compliance applicability)."],
        ],
    )

    # 11 Architectures
    add_heading(doc, "11. Commercial Architectures, Selectable Assets & Recommendation Rules", 1)
    add_heading(doc, "11.0 Asset selection (include flags)", 2)
    add_para(
        doc,
        "On Architecture / Commercial you choose which assets participate. Unselected assets are forced to "
        "zero capacity in the engine and their Project Setup tabs are hidden.",
    )
    add_table(
        doc,
        ["Structure", "Selectable assets"],
        [
            ["DISCOM", "DISCOM / grid only"],
            ["CAPTIVE", "Solar, Wind, BESS"],
            ["HYBRID", "DISCOM, Solar, Wind, BESS"],
            ["OPEN_ACCESS", "DISCOM, Solar, Wind, BESS"],
        ],
    )
    add_heading(doc, "11.1 DISCOM — GRID-ONLY BASELINE", 2)
    add_para(
        doc,
        "Data Centre → MSEDCL/DISCOM → Grid. RE and BESS capacities are treated as zero for the DISCOM "
        "energy path so the case represents full grid supply economics. "
        "Therefore Annual RE % and Hourly CFE min show 0% by design (not a calculation error). "
        "Costs include energy (TOD if enabled), demand and fixed charges, plus any applicable compliance cost "
        "and DISCOM network charges when enabled. "
        "IRR and Payback typically show “—” for DISCOM because cashflows are all costs with no RE CAPEX "
        "investment to recover; NPV of DISCOM is the present value of grid electricity bills (often large and negative). "
        "On the Dashboard architecture card, DISCOM is labelled GRID-ONLY BASELINE — never RECOMMENDED when "
        "RE/CFE targets are missed (which they are by design at 0%).",
    )
    add_heading(doc, "11.2 Captive / Group Captive", 2)
    add_para(
        doc,
        "Avaada RE project style captive structure into the Data Centre. Ownership % and allocation % are "
        "commercial inputs — the tool does not certify captive legal qualification. Energy may be priced via "
        "captive_energy_price with optional per-asset network charges and losses on the selected Solar/Wind/BESS assets.",
    )
    add_heading(doc, "11.3 Hybrid (primary optimization architecture)", 2)
    add_para(
        doc,
        "Selected combination of Solar + Wind + BESS + DISCOM/grid serving the Data Centre. This is the default "
        "structure and the primary architecture contemplated for least-cost optimization under RE/CFE constraints.",
    )
    add_heading(doc, "11.4 Open Access", 2)
    add_para(
        doc,
        "RE generators → OA / transmission network → Data Centre (with optional DISCOM backup). Uses oa_energy_price "
        "plus configurable per-asset network charges when those flags are enabled.",
    )
    add_heading(doc, "11.5 Architecture Comparison & RECOMMENDED label", 2)
    add_para(
        doc,
        "On the Architecture page (and on the Dashboard scenario table), Run Architecture Comparison / Refresh "
        "simulates all four structures with the current project inputs (structure-specific capacity zeroing "
        "applied where required) and shows a side-by-side table of Solar/Wind/BESS/Grid MW, Annual RE %, "
        "Hourly CFE, Grid GWh, curtailment, BESS utilization, ₹/kWh, NPV, IRR, payback, and feasibility status. "
        "RECOMMENDED is assigned only to a feasible architecture with the lowest delivered-energy cost among "
        "feasible options. If none are feasible, the UI shows NO FEASIBLE RECOMMENDATION (lowest-cost row may "
        "still be highlighted as a cost reference only). Footnotes explain DISCOM 0% RE/CFE and blank IRR/Payback.",
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
    add_heading(doc, "12.2 RPO", 2)
    add_para(
        doc,
        "Configurable solar/wind/hydro/other targets. Concept note does not hard-code numeric RPO splits — "
        "defaults are 0% until you enter jurisdiction-specific targets. Shortfall can incur rpo_buyout cost if Applicable.",
    )
    add_heading(doc, "12.3 RCO", 2)
    add_para(
        doc,
        "Configurable target, compliance route (Unknown / Self-generation / REC / Buyout / Other) and costs. "
        "The concept note specifically questions whether a 220 kV Data Centre SPV is a Designated Consumer — "
        "do not treat model output as that determination.",
    )
    add_heading(doc, "12.4 ESO", 2)
    add_para(
        doc,
        "Trajectory from concept note: FY2026-27 = 2.5% rising to FY2029-30 = 4.0% (intervening years are "
        "DEFAULT ASSUMPTION interpolations). Select eso_active_year for the study. Renewable-origin stored "
        "energy requirement defaults to ≥ 85% (concept note).",
    )
    add_heading(doc, "12.5 Annual RE % vs Hourly CFE % (and CFE analytics)", 2)
    add_bullets(
        doc,
        [
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
        ],
    )

    doc.add_page_break()

    # 12A Profiles
    add_heading(doc, "12A. Profiles — Optional PROJECT DATA CSV Import", 1)
    add_para(
        doc,
        "Open Profiles from the left navigation (Project group). For each of Load, Solar and Wind you can keep "
        "SYNTHETIC generation or upload a PROJECT DATA series.",
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
            "Download ready-made templates from the Profiles page: Load / Solar / Wind template CSVs "
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
    add_heading(doc, "13. Running the 8,760-Hour Simulation & Energy Ledger", 1)
    add_heading(doc, "13.1 How to run", 2)
    add_numbered(
        doc,
        [
            "Ensure the correct project is open and inputs are saved.",
            "If using PROJECT DATA, confirm Profiles uploaded successfully.",
            "Click Run 8760 Simulation in the top bar (works from any page).",
            "Wait for completion (typically a few seconds for rule-based dispatch).",
            "You are taken to the Dashboard with Feasibility / Data Quality / CFE cards and KPIs.",
            "Open Energy Ledger to verify reconciliation OK before presenting numbers.",
        ],
    )
    add_heading(doc, "13.2 What the engine does (Model 2.0)", 2)
    add_numbered(
        doc,
        [
            "Resolve each profile: SYNTHETIC generator or PROJECT DATA import (error if PROJECT DATA missing/invalid).",
            "Generate/load 8,760-hour load, solar and wind series (deterministic seed for synthetic).",
            "Dispatch each hour with explicit flows: solar/wind → load, → BESS, → curtailment; BESS discharge with "
            "solar/wind/grid origin tracking; grid on residual; unserved if still short.",
            "Validate hourly power balance, SOC bounds, energy identities and finite values — MODEL ERROR on hard failure.",
            "Build Energy Ledger (annual + monthly) and SHA-256 config fingerprint.",
            "Compute KPIs, CFE analytics, monthly balance, compliance, feasibility and financials.",
            "Also compute a DISCOM GRID-ONLY BASELINE for incremental economics.",
        ],
    )
    add_heading(doc, "13.3 8760 Simulation page — Time window controls (detailed)", 2)
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
                "Month-wise load, solar, wind, BESS, grid, curtailment, RE%, CFE.",
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
    add_heading(doc, "13.4 Energy Ledger page — how to read it", 2)
    add_para(
        doc,
        "The Energy Ledger is the audit trail for the latest simulation. Annual table lists every major flow in MWh and GWh. "
        "Reconciliation checks solar identity, wind identity, load identity and AC balance against a tight tolerance. "
        "Status OK / Fail is shown as a pill. Monthly table lists each month’s AC gap and curtailment. "
        "Config hash is printed for traceability. If ledger is missing, re-run the simulation (older runs before V2 "
        "may need a fresh run).",
    )
    add_heading(doc, "13.5 Dashboard KPI cards", 2)
    add_table(
        doc,
        ["KPI", "Meaning"],
        [
            ["Annual RE", "Year energy RE serving load / total load"],
            ["Hourly CFE (min)", "Minimum hourly CFE across the year; subtext shows CFE pass mode Pass/Fail"],
            ["Grid Import", "Annual grid energy in GWh"],
            ["BESS", "Configured power MW / energy MWh and utilization"],
            ["Curtailment", "Curtailed RE as % of RE generation"],
            ["Cost ₹/kWh", "TOTAL COST OF DELIVERED ENERGY (annualised cost / load energy)"],
            ["NPV ₹ Cr", "Net present value; incremental vs DISCOM for non-DISCOM structures"],
            ["IRR", "Project IRR if defined (often — for pure DISCOM cost stack)"],
            ["Payback", "Simple/model payback years if defined"],
        ],
    )

    add_heading(doc, "13.6 How numbers are displayed (Thousand / Lakh / Cr)", 2)
    add_para(
        doc,
        "Large techno-economic figures are intentionally shown in compact Indian-style units so the UI "
        "never floods the screen with long digit strings. The same rules apply to Dashboard KPIs, tables, "
        "ledger values, economics and most chart tooltips/axes.",
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
            ["Chart axis labels", "May use Thousand / Lakh / Cr to keep axis text short", "1.5 Thousand"],
        ],
    )
    add_para(
        doc,
        "Exports (Excel/PDF) may still contain full-precision numeric cells for audit; the on-screen SPA "
        "is optimized for readable Indian units. Hard-refresh (Ctrl+F5) after upgrading the EXE if an old "
        "cached UI still shows long digit strings.",
    )

    # 13B Feasibility
    add_heading(doc, "13B. Feasibility Status & Binding Constraints", 1)
    add_para(
        doc,
        "Every simulation returns a unified feasibility object. The Dashboard Feasibility card is the authoritative "
        "status for whether the current architecture can be labelled RECOMMENDED.",
    )
    add_table(
        doc,
        ["Status", "Meaning", "can_recommend?"],
        [
            ["FEASIBLE", "Enabled technical/compliance targets met; no hard model error.", "Yes — may show RECOMMENDED"],
            ["NOT FEASIBLE", "RE target miss, CFE pass-mode fail, and/or unserved energy > 0 (among other binding issues).", "No"],
            ["INCOMPLETE INPUTS", "Editable DEFAULT_ASSUMPTION values remain (preliminary / not investment-ready).", "No"],
            ["LEGAL REVIEW REQUIRED", "RPO/RCO/ESO applicability still requires legal review (and technical pass).", "No"],
            ["MODEL ERROR", "Internal validation failed (balance/SOC/NaN). Do not use results.", "No"],
        ],
    )
    add_heading(doc, "13B.1 Binding constraints", 2)
    add_para(
        doc,
        "When not feasible, the card lists binding items such as ANNUAL_RE, HOURLY_CFE, UNSERVED, RPO, RCO, ESO "
        "with actual vs target and suggested remedies (increase BESS/wind, relax target/pass mode, raise grid, etc.). "
        "An approximate extra BESS MWh hint may appear for CFE deficits — it is a heuristic, not a guarantee.",
    )
    add_heading(doc, "13B.2 Stale results", 2)
    add_para(
        doc,
        "Saving inputs increments the project input_version. If the loaded simulation’s input_version differs, "
        "results_stale = true and a red STALE RESULTS banner appears. Re-run before exporting board packs.",
    )

    # 14 Optimization
    add_heading(doc, "14. Optimization, Explainability & Marginal Analysis", 1)
    add_numbered(
        doc,
        [
            "Open Optimization.",
            "Choose objective: Minimum Cost (default / concept-note primary), Maximum RE, Maximum CFE, "
            "Minimum Grid Dependency, Compliance First, or Balanced (uses weights).",
            "Choose dispatch mode: Rule-Based (default, fast) or LP Dispatch (SciPy HiGHS weekly blocks).",
            "Choose search mode: Quick / Standard / Thorough (more candidates = longer runtime).",
            "Set capacity bounds and steps for solar, wind, BESS power/energy and grid.",
            "Toggle enforce_re_target, enforce_cfe_target, enforce_no_unserved as needed. "
            "Note: strict 24×7 CFE enforcement is demanding — default CFE enforce is off.",
            "Click Save, then Run Optimization.",
            "Watch progress: scenario, iteration, best ₹/kWh, feasible count.",
            "Use Cancel if you need to stop.",
            "Review Top Feasible Solutions table, recommendation label, and WHY THIS CONFIGURATION? bullets.",
            "Optionally click Run Marginal Capacity Steps for +50 MW solar / +50 MW wind / +100 MWh BESS / +25 MW BESS power deltas.",
        ],
    )
    add_para(
        doc,
        "If no feasible solution exists, the UI shows NO FEASIBLE SOLUTION with primary binding constraint, "
        "message and remedies (RE/CFE too high, BESS too small, RE/grid limits, compliance, commercial constraints) — "
        "not a bare 'Optimization failed' message. Infeasible winners are never labelled RECOMMENDED.",
    )
    add_para(
        doc,
        "Algorithm (transparent staged approach): capacity screening → feasibility screening → "
        "full 8,760 dispatch + economic evaluation per candidate → ranking → local neighborhood refine → top 10. "
        "Project-data profiles (if selected) are used for every candidate via the project_id path.",
    )
    add_heading(doc, "14.1 Explainability fields", 2)
    add_bullets(
        doc,
        [
            "Headline: WHY THIS CONFIGURATION?",
            "Bullets: capacities, RE/CFE status, grid/curtail/unserved, delivered-energy cost and NPV, CFE stress note.",
            "Nearby alternatives: feasible-but-worse vs infeasible with binding reasons.",
            "Marginal steps: Δ ₹/kWh, Δ RE pp, Δ CFE min pp, Δ grid GWh, feasibility flag.",
        ],
    )

    # 15 Scenarios & sensitivity
    add_heading(doc, "15. Scenarios & Sensitivity", 1)
    add_heading(doc, "15.1 Scenarios", 2)
    add_bullets(
        doc,
        [
            "Save Current as Scenario — stores a named snapshot of the full config.",
            "Load — writes that scenario’s config into the active project inputs (marks prior results stale).",
            "Run — loads the scenario and immediately runs an 8,760 simulation, then opens Dashboard.",
            "Delete — removes the scenario record.",
        ],
    )
    add_para(doc, "Seeded examples:")
    add_bullets(
        doc,
        [
            "DISCOM – 90% RE",
            "CAPTIVE – 95% RE",
            "HYBRID – 95% RE / 99% CFE",
            "OPEN ACCESS – 99% RE / 100% CFE",
        ],
    )
    add_heading(doc, "15.2 Sensitivity", 2)
    add_para(
        doc,
        "Click Run Sensitivity. The engine varies key drivers (solar/wind/BESS cost, grid tariff, load factor, "
        "capacities, discount rate, escalations, etc.) by ±20%, plots a tornado on ₹/kWh, and shows a "
        "two-variable matrix for solar capacity × BESS energy.",
    )

    # 16 Economics & reports
    add_heading(doc, "16. Economics (Incremental vs DISCOM) & Reports", 1)
    add_heading(doc, "16.1 Economics page", 2)
    add_para(
        doc,
        "Requires a completed simulation. Shows TOTAL COST OF DELIVERED ENERGY ₹/kWh, annual cost, CAPEX, "
        "NPV/IRR/payback (basis noted: incremental_vs_discom or standalone_cost_stack), cost-breakdown chart "
        "and raw breakdown JSON.",
    )
    add_heading(doc, "16.2 GRID-ONLY BASELINE (DISCOM) panel", 2)
    add_para(
        doc,
        "Shows DISCOM comparator cost ₹/kWh and annual cost, with the reason that solar/wind/BESS are forced to 0 MW. "
        "Use this as the bill baseline for investment cases — not as a RE/CFE architecture.",
    )
    add_heading(doc, "16.3 Incremental vs DISCOM panel", 2)
    add_para(
        doc,
        "Shows incremental CAPEX, year-1 incremental OPEX, and incremental NPV / IRR / payback derived from "
        "cashflows = −ΔCAPEX then annual DISCOM_cost − architecture_cost. For non-DISCOM structures, the "
        "headline NPV/IRR/payback on Dashboard and Economics use these incremental cashflows.",
    )
    add_heading(doc, "16.4 Reports page", 2)
    add_table(
        doc,
        ["Button", "Output (Model 2.0)"],
        [
            [
                "Export Excel",
                "Summary (incl. feasibility, data quality, config hash, stale flag), Project, Assumptions, "
                "Load/Solar/Wind/BESS/Grid, 8760 note, Monthly, Compliance, Economics (+ incremental + DISCOM baseline), "
                "Data Quality, Feasibility (+ binding table), Energy Ledger, Ledger Monthly, CFE Analytics.",
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

    # 17 Assumptions / methodology / settings
    add_heading(doc, "17. Assumptions, Methodology & Settings", 1)
    add_heading(doc, "17.1 Assumptions register", 2)
    add_para(
        doc,
        "Filter by CONCEPT_NOTE / DEFAULT_ASSUMPTION / USER_INPUT / CALCULATED and search by parameter name. "
        "Use this before any management presentation to audit what is still a default.",
    )
    add_heading(doc, "17.2 Methodology (overview)", 2)
    add_para(
        doc,
        "Model 2.0 equations are summarised in the in-app Methodology page and in full detail in "
        "Section 17A below (and in MODEL_METHODOLOGY.md / ASSUMPTIONS.md). "
        "Every KPI on the Dashboard is calculated — never hard-coded.",
    )
    add_heading(doc, "17.3 Settings — Share & access", 2)
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
        "One model hour = 1 MW sustained for 1 hour → 1 MWh.",
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

    add_heading(doc, "17A.2 Synthetic load profile", 2)
    add_para(
        doc,
        "When load.profile_source = SYNTHETIC, an 8,760 shape is built from the Load parameters, then scaled:",
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

    add_heading(doc, "17A.3 Synthetic solar profile", 2)
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
        "Each hour t the engine follows fixed priorities (also shown as Optimization priority_1…5):",
    )
    add_para(
        doc,
        "BESS modelling note: separate Charge efficiency, Discharge efficiency, Max charge power and Max discharge "
        "power inputs are removed. Charge and discharge are each limited by bess.power_mw. Conversion is ideal "
        "(η = 100%), so energy into storage equals energy out for a given throughput (aside from SOC window limits). "
        "Older projects drop the retired fields automatically when opened.",
    )
    add_numbered(
        doc,
        [
            "RE serves load first: DirectRE_t = min(Solar_t + Wind_t, Load_t). Solar/wind shares of DirectRE are proportional to their generation.",
            "Excess RE charges BESS (if capacity and SOC headroom allow), limited by BESS power rating (η = 100%).",
            "Any RE still left is curtailed.",
            "If load remains, BESS discharges (limited by power rating and SOC above min; η = 100%).",
            "Grid import serves any residual, ≤ max_import_mw × (availability_pct/100).",
            "If still short → Unserved_t > 0.",
            "Optional: if allow_grid_charge and load is fully met, residual grid headroom may charge BESS.",
        ],
    )
    add_para(doc, "State of charge (MWh):", bold=True)
    add_para(
        doc,
        "SOC_t = SOC_(t−1) + Charge_t − Discharge_t, "
        "with SOC_min = min_soc_pct/100 × energy_mwh and SOC_max = max_soc_pct/100 × energy_mwh. "
        "Charge and discharge power are both capped at bess.power_mw. Conversion efficiency is modelled as ideal (100%).",
    )
    add_para(doc, "User-editable BESS technical inputs (Setup → BESS):", bold=True)
    add_table(
        doc,
        ["Parameter", "Role"],
        [
            ["power_mw", "Power rating — max charge MW and max discharge MW in every hour"],
            ["energy_mwh", "Energy capacity used with SOC % limits"],
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
            "charge_efficiency_pct — was one-way charge efficiency; now fixed at 100%.",
            "discharge_efficiency_pct — was one-way discharge efficiency; now fixed at 100%.",
            "round_trip_efficiency_pct — was calculated from the two efficiencies; removed.",
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
            "Charge from solar/wind increases the matching RE bucket 1:1 (η = 100%); grid charge increases grid-origin.",
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
    )

    add_heading(doc, "17A.9 Other KPI formulas", 2)
    add_table(
        doc,
        ["KPI", "Calculation"],
        [
            ["Annual solar / wind MWh", "Σ Solar_t / Σ Wind_t over 8,760 hours"],
            ["Grid import MWh / GWh", "Σ Grid_t ; GWh = MWh / 1,000"],
            ["Curtailment %", "Σ Curtail_t / max(Σ Solar_t + Σ Wind_t, ε) × 100"],
            ["Unserved MWh", "Σ Unserved_t  (must be ≈ 0 for feasibility when enforce_no_unserved)"],
            ["BESS duration (h)", "energy_mwh / power_mw"],
            ["BESS cycles", "Σ Discharge_t / energy_mwh"],
            ["BESS utilization %", "min(100, cycles / 365 × 100) — vs 1 full cycle/day"],
            ["BESS losses MWh", "0 (ideal conversion; η_c = η_d = 100%)"],
            ["Max grid import MW", "max(Grid_t) over the year (feeds demand charge)"],
        ],
    )

    add_heading(doc, "17A.10 Energy Ledger reconciliation", 2)
    add_para(doc, "Annual (and each month) the ledger checks four identities within a tight MWh tolerance:")
    add_bullets(
        doc,
        [
            "Solar identity: Solar = Solar→Load + Solar→BESS + Solar curtailment",
            "Wind identity: Wind = Wind→Load + Wind→BESS + Wind curtailment",
            "Load identity: Load = Direct RE + BESS discharge + Grid→Load + Unserved",
            "AC balance: Solar + Wind + Discharge + Grid + Unserved  ≈  Load + Charge + Curtailment",
        ],
    )
    add_para(
        doc,
        "If any gap exceeds tolerance → reconciliation Fail / MODEL ERROR — do not use the run for decisions.",
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
            "RPO: for each bucket (solar/wind/hydro/other), required_mwh = Load_MWh × target_pct/100. "
            "Gap = max(0, required − actual_generation_bucket). "
            "If Applicable: cost = Σ gaps_mwh × 1,000 × rpo_buyout_inr_per_kwh.",
            "RCO: compares Annual RE % to rco_target_pct. "
            "Gap energy ≈ max(0, Load×target/100 − RE_serving_load). "
            "Cost uses REC or buyout ₹/kWh when Applicable.",
            "ESO: required_storage_mwh = Load_MWh × active_year_target_pct/100. "
            "Actual storage energy = Σ BESS charge. Also requires RE-origin share of stored energy ≥ eso_re_origin_min_pct "
            "(default 85% from concept note). Buyout on shortfall / origin failure when Applicable.",
            "total_compliance_cost_inr = RPO cost + RCO cost + ESO cost (year-1 stack).",
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

    add_heading(doc, "17A.13 CAPEX and OPEX", 2)
    add_bullets(
        doc,
        [
            "Solar CAPEX = capacity_mw × capex_inr_per_mw",
            "Wind CAPEX = capacity_mw × capex_inr_per_mw",
            "BESS CAPEX = power_mw × capex_inr_per_mw + energy_mwh × capex_inr_per_mwh",
            "Total CAPEX = solar + wind + BESS (forced to 0 for DISCOM structure / when include_generation_capex = False as configured)",
            "Solar OPEX = capacity_mw × opex_inr_per_mw_year (0 under DISCOM)",
            "Wind OPEX = capacity_mw × opex_inr_per_mw_year",
            "BESS OPEX = opex_inr_per_year",
        ],
    )

    add_heading(doc, "17A.14 Capital recovery factor (annualised CAPEX)", 2)
    add_para(
        doc,
        "CRF(r, n) = r(1+r)^n / ((1+r)^n − 1)   with r = discount_rate_pct/100, n = asset project_life_yr. "
        "If r ≈ 0, CRF = 1/n.",
        italic=True,
    )
    add_para(
        doc,
        "Annualised CAPEX_asset = CAPEX_asset × CRF(r, n_asset). "
        "Used in Year-1 TOTAL COST OF DELIVERED ENERGY when generation CAPEX is included. "
        "DISCOM forces annualised generation CAPEX to 0.",
    )

    add_heading(doc, "17A.15 Commercial energy & network charges (Year 1)", 2)
    add_bullets(
        doc,
        [
            "Demand charge = max_grid_import_mw × demand_charge_inr_per_mw_month × 12",
            "Fixed charge = fixed_charge_inr_per_year",
            "Additional costs = sum of Financial → additional_costs annual ₹ rows (inflated in multi-year cashflows)",
            "DISCOM: RE energy cost = 0 (grid-only).",
            "CAPTIVE: RE energy cost = (RE_serving_load_mwh / (1 − loss_pct/100)) × 1,000 × captive_energy_price",
            "OPEN_ACCESS: same form with oa_energy_price",
            "HYBRID with include_generation_capex = False: "
            "RE energy cost = Solar_mwh×1,000×solar_energy_cost + Wind_mwh×1,000×wind_energy_cost",
            "HYBRID with include_generation_capex = True: RE tariff energy cost typically 0; CAPEX recovered via CRF",
            "Network charges are per asset when that asset is included and its apply_network_charges_to_* flag is True:",
            "  — Solar MWh × 1,000 × (solar transmission + wheeling + banking_if_enabled + other)",
            "  — Wind MWh × 1,000 × (wind transmission + wheeling + banking_if_enabled + other)",
            "  — BESS discharge MWh × 1,000 × (bess transmission + wheeling + other)",
            "  — Grid import MWh × 1,000 × (grid/DISCOM transmission + wheeling + other) when apply_network_charges_to_grid",
            "Legacy apply_network_charges_to_re / re_* rates are migrated into the per-asset fields when opening older projects.",
        ],
    )

    add_heading(doc, "17A.16 TOTAL COST OF DELIVERED ENERGY (₹/kWh)", 2)
    add_para(
        doc,
        "Year-1 total annual cost = Grid energy + Demand + Fixed + RE energy + Network + OPEX + "
        "Annualised CAPEX + Compliance + Additional costs",
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

    add_heading(doc, "17A.17 Multi-year cash-flows, NPV, IRR, payback", 2)
    add_para(doc, "Absolute project cash-flows (cost framing):", bold=True)
    add_bullets(
        doc,
        [
            "Year 0: CF_0 = −CAPEX_0 (0 if CAPEX not included / DISCOM)",
            "Year y = 1…N: escalate grid energy by electricity_escalation_pct; "
            "demand/fixed/OPEX/compliance by inflation_pct; RE/network parts by re_cost_escalation_pct",
            "In bess.replacement_year: add replacement_cost_pct/100 × BESS CAPEX (if CAPEX included)",
            "Final year: residual credit = −CAPEX_0 × residual_value_pct/100 (negative cost = inflow)",
            "CF_y = −(operating cost_y) − residual_adjustment",
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

    add_heading(doc, "17A.18 Incremental economics vs DISCOM (GRID-ONLY BASELINE)", 2)
    add_para(
        doc,
        "The model always runs a parallel DISCOM case with solar = wind = BESS = 0 (grid-only). "
        "For CAPTIVE / HYBRID / OPEN_ACCESS:",
    )
    add_bullets(
        doc,
        [
            "Incremental CAPEX = Project_CAPEX − DISCOM_CAPEX (usually = Project_CAPEX)",
            "Year-y savings = DISCOM_annual_cost_y − Project_annual_cost_y",
            "Incremental cash-flows: CF_0 = −Incremental CAPEX; CF_y = savings_y",
            "Incremental NPV uses the project discount_rate_pct on those cash-flows",
            "Dashboard NPV / IRR / Payback for non-DISCOM structures are these incremental metrics "
            "(economics_basis = incremental_vs_discom)",
            "DISCOM itself remains the GRID-ONLY BASELINE comparator and is never auto-labelled RECOMMENDED for RE/CFE targets",
        ],
    )

    add_heading(doc, "17A.19 Feasibility → RECOMMENDED", 2)
    add_bullets(
        doc,
        [
            "FEASIBLE only if enabled technical checks pass (RE target if enforce_re_target, CFE pass mode if enforce_cfe_target, "
            "unserved ≈ 0 if enforce_no_unserved) and no MODEL ERROR.",
            "INCOMPLETE INPUTS if editable DEFAULT_ASSUMPTION values remain.",
            "LEGAL REVIEW REQUIRED if RPO/RCO/ESO still need legal review.",
            "can_recommend = true only when status = FEASIBLE. Architectures are never labelled RECOMMENDED otherwise.",
        ],
    )

    add_heading(doc, "17A.20 Optimization ranking (summary)", 2)
    add_numbered(
        doc,
        [
            "Build capacity candidates (Quick / Standard / Thorough grids of solar, wind, BESS, grid).",
            "For each candidate: full 8,760 dispatch → KPIs → compliance → feasibility → financials (incl. incremental vs DISCOM).",
            "Discard / flag infeasible per enforce_* flags.",
            "Rank by objective (Minimum Cost, Maximum RE, Maximum CFE, Minimum Grid Dependency, Compliance First, or Balanced weighted score).",
            "Local neighbourhood refine; return top feasible solutions + explainability (why this / why not nearby).",
        ],
    )
    add_para(
        doc,
        "Balanced objective uses weight_cost, weight_re, weight_cfe, weight_grid (normalised) to combine "
        "lower cost, higher RE, higher CFE and lower grid energy.",
    )

    add_heading(doc, "17A.21 Config fingerprint", 2)
    add_para(
        doc,
        "Each run stores a SHA-256 hash of the normalised project configuration (config fingerprint) "
        "shown on the Energy Ledger for audit. Changing inputs increments input_version; mismatched "
        "versions mark results STALE until you re-run the simulation.",
    )

    add_heading(doc, "17A.22 Display formatting (not a model change)", 2)
    add_para(
        doc,
        "On-screen Lakh / Cr formatting only changes how numbers are printed. Underlying calculations "
        "and Excel numeric cells use full precision. Under 1 Lakh → full digits; then Lakh; then Cr.",
    )

    doc.add_page_break()

    # 18 Workflow
    add_heading(doc, "18. Recommended End-to-End Workflow (Model 2.0)", 1)
    add_numbered(
        doc,
        [
            "Launch EXE (Chrome opens Start) or open Network URL if using a shared host → Create New Project "
            "(or Open Existing Project… .pto.zip).",
            "Optional: open Settings → note Network URL if colleagues will join from other laptops.",
            "Optional: Save Project to store a .pto.zip in a local folder.",
            "Project Setup: select Architecture structure + assets; replace peak load, tariffs, CAPEX/OPEX, "
            "Compliance applicability/targets and Financial (incl. Additional costs) with project data. "
            "Read the short help text under each parameter.",
            "Optional: Profiles → upload Load/Solar/Wind PROJECT DATA CSVs; confirm badges.",
            "Review Assumptions register — clear remaining critical defaults (Data Quality card will update after re-sim).",
            "Run 8760 Simulation → read Feasibility / Data Quality / CFE Pass Mode before KPI storytelling "
            "(numbers show as Lakh / Cr when large).",
            "Open Energy Ledger → confirm reconciliation OK and note config hash.",
            "If status is NOT FEASIBLE, use binding constraints / remedies before optimizing "
            "(adjust Compliance in Project Setup if targets/pass mode need changing).",
            "Open 8760 Simulation page → pick Time window (month/week/day) → Show charts for critical periods.",
            "Architecture → Run Architecture Comparison → note RECOMMENDED only if a feasible architecture exists.",
            "Optimization → set RE/CFE constraints → Run Optimization → read explainability + optional marginal steps.",
            "Apply a preferred candidate capacity set into inputs (manually) → re-simulate (clear STALE).",
            "Economics → review GRID-ONLY BASELINE and Incremental vs DISCOM.",
            "Scenarios → save named cases for board packs.",
            "Sensitivity → understand ₹/kWh drivers.",
            "Reports → Export Excel and PDF; Backup Project (.pto.zip) or top-bar Save Project.",
            "Independent legal/commercial review of RPO/RCO/ESO applicability before decisions.",
            "When finished: Quit App (or close the Chrome tab) so the host EXE exits and network users disconnect.",
        ],
    )

    # 19 Interpreting results
    add_heading(doc, "19. Interpreting Results Correctly", 1)
    add_bullets(
        doc,
        [
            "Never present an architecture as RECOMMENDED if Feasibility ≠ FEASIBLE.",
            "Unserved energy > 0 means load was not fully met under the configured grid/BESS/RE limits — treat as NOT FEASIBLE for reliability.",
            "High curtailment means RE was oversized relative to load + BESS absorption.",
            "High Annual RE with low min Hourly CFE means energy is green on average but not 24×7 — needs more BESS and/or wind for night coverage.",
            "Read CFE Pass Mode carefully — All hours ≥ target is much stricter than Mean or Share-of-hours.",
            "DISCOM ₹/kWh is the GRID-ONLY BASELINE for incremental NPV/IRR — not a green architecture.",
            "DISCOM rows with 0% RE/CFE and “—” IRR/Payback are expected (grid-only, no investment recovery).",
            "Pass/Fail on compliance depends on your applicability declaration and targets — Unknown is not Pass.",
            "INCOMPLETE INPUTS means defaults remain — suitable for screening, not investment decisions.",
            "STALE RESULTS means inputs changed after the run — re-simulate before exporting.",
            "Energy Ledger Fail / MODEL ERROR → do not use the run; report hour/context if it persists on a released build.",
            "Never present DEFAULT ASSUMPTION results as site-measured facts.",
            "₹/kWh is TOTAL COST OF DELIVERED ENERGY in this model — not a formal certified LCOE.",
            "Large on-screen values in Lakh / Cr are display formatting — check Excel exports for full-precision cells if needed.",
            "When sharing over LAN, remember everyone edits the same host database — coordinate who saves inputs.",
        ],
    )

    # 20 Data
    add_heading(doc, "20. Data Storage, Backup & Persistence", 1)
    add_bullets(
        doc,
        [
            "SQLite database auto-created on first launch (typically under %LOCALAPPDATA%\\PowerTrainOptimizer for the EXE).",
            "ACCESS_URLS.txt is written on each launch (LocalAppData and beside the EXE) with This PC + Network URLs.",
            "Projects, inputs, scenarios, settings and run metadata persist across restarts.",
            "Save Project / Backup Project write a portable .pto.zip you can store anywhere and later restore via Open Existing Project….",
            "Hourly arrays for saved runs are stored efficiently (e.g. under data/runs as NPZ), not as 8,760 SQL rows.",
            "Energy ledger JSON is stored beside the run (sim_<id>_ledger.json).",
            "Imported PROJECT DATA profiles are stored under data/profiles/project_<id>/.",
            "Before schema migrations the app backs up the database automatically.",
            "To distribute the app itself (not project data), copy dist\\PowerTrain_Share\\ or the standalone EXE.",
        ],
    )

    # 21 Troubleshooting
    add_heading(doc, "21. Troubleshooting", 1)
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
            ["Dashboard says NOT FEASIBLE but costs look fine", "Feasibility is target-driven. Read binding constraints; do not treat as RECOMMENDED."],
            ["Where is the Compliance menu?", "Under Project Setup → Compliance (removed from Analysis nav). Dashboard has a shortcut link."],
            ["DISCOM shows 0% RE/CFE and — for IRR/Payback", "Expected: DISCOM is GRID-ONLY BASELINE (no RE assets). IRR/Payback apply to investment cases vs DISCOM."],
            ["STALE RESULTS banner", "Inputs changed after the last run — click Run 8760 Simulation again."],
            ["MODEL ERROR: PROJECT DATA … no profile", "Upload the CSV under Profiles or set profile_source back to SYNTHETIC."],
            ["CSV upload rejected", "Check length (8760/8784), no negatives/NaNs, fix duplicate timestamps; there is no silent fallback."],
            ["Energy Ledger empty", "Re-run simulation on Model 2.0 so ledger JSON is written."],
            ["MODEL ERROR: power balance", "Report the hour index; indicates an internal dispatch inconsistency (should not occur on released builds)."],
            ["NO FEASIBLE SOLUTION (optimization)", "Relax RE/CFE targets, raise solar/wind/BESS/grid bounds, or switch search to Thorough; read primary binding constraint."],
            ["Optimization is slow", "Use Quick search mode first; Standard/Thorough evaluate many full 8,760 runs."],
            ["Dashboard empty", "Click Run 8760 Simulation."],
            ["Charts empty on 8760 page", "Run simulation first, then choose Time window and click Show charts."],
            ["Numbers look like long digit strings", "Hard-refresh Ctrl+F5 or relaunch latest EXE — UI should show Lakh / Cr for large values."],
            ["Parameter meaning unclear", "Read the grey help text under each field title; full list also in Assumptions and Section 9 of this guide."],
            ["UI looks old / charts not updated", "Hard-refresh the browser (Ctrl+F5) or relaunch the latest Model 2.0 EXE."],
            ["Default still 100 MW / Model 1.0.0", "You are on an old database/EXE — use the Model 2.0 rebuild, or Create New Project from current defaults."],
            ["Need to reset / transfer a project", "Create New Project, or Open Existing Project… with a .pto.zip from Save Project / Backup Project."],
            ["How do I give the app to someone else?", "Copy dist\\PowerTrain_Share\\ (or just the EXE + HOW_TO_SHARE.txt). No install required."],
        ],
    )

    # 22 Glossary
    add_heading(doc, "22. Glossary", 1)
    add_table(
        doc,
        ["Term", "Definition in this tool"],
        [
            ["8,760 / 8,784", "Hours in a non-leap / leap year; model resolution for profiles"],
            ["Annual RE %", "Share of annual load energy served by renewable (incl. RE-origin BESS discharge)"],
            ["Hourly CFE %", "Hourly carbon-free energy share of load"],
            ["CFE pass mode", "Rule used to Pass/Fail hourly CFE (all hours / mean / share of hours)"],
            ["CFE analytics", "Deficit streak, % hours ≥ target, duration-curve stats attached to KPIs"],
            ["BESS", "Battery Energy Storage System — power_mw caps charge & discharge; ideal 100% conversion"],
            ["SOC", "State of charge (MWh or %)"],
            ["Curtailment", "Renewable energy that could not serve load or charge BESS"],
            ["Energy Ledger", "Audited annual/monthly energy flow table with reconciliation"],
            ["Config hash", "SHA-256 fingerprint of configuration used for a run"],
            ["Feasibility", "Unified status deciding whether RECOMMENDED is allowed"],
            ["Binding constraint", "Primary reason a case fails feasibility (e.g. HOURLY_CFE)"],
            ["STALE", "Results older than current project input_version"],
            ["SYNTHETIC / PROJECT DATA", "Profile origin badges"],
            ["DISCOM", "GRID-ONLY BASELINE commercial structure (solar/wind/BESS forced to 0)"],
            ["Captive", "Captive / group captive commercial structure"],
            ["Hybrid", "On-site/contracted Solar+Wind+BESS with grid balancing"],
            ["Open Access", "OA wheeling of RE to the consumer"],
            ["RPO", "Renewable Purchase Obligation"],
            ["RCO", "Renewable Consumption Obligation (applicability may need legal review)"],
            ["ESO", "Energy Storage Obligation"],
            ["NPV / IRR / Payback", "Project finance metrics; for non-DISCOM use incremental vs DISCOM cashflows"],
            ["TOTAL COST OF DELIVERED ENERGY", "₹/kWh = annualised cost / load energy in this model"],
            ["Incremental vs DISCOM", "ΔCAPEX and annual bill savings vs GRID-ONLY BASELINE"],
            ["Quit App", "Sidebar control that stops the server and background PowerTrain processes (disconnects LAN users)"],
            ["Save Project", "Top-bar action that saves inputs and writes a portable .pto.zip to a folder you choose"],
            [".pto.zip", "Portable project backup/restore archive (Open Existing Project… / Backup Project)"],
            ["Asset selection", "include_discom / include_solar / include_wind / include_bess flags that gate Setup tabs and capacities"],
            ["Additional costs", "Named annual ₹ line items under Financial included in delivered-energy cost"],
            ["LAN / Network URL", "http://<host-LAN-IP>:<port>/ so other PCs on the same network can use the host’s running app"],
            ["ACCESS_URLS.txt", "File written on launch with This PC and Network URLs"],
            ["Lakh / Cr display", "Compact UI number format: under 1 Lakh full digits; then Lakh; then Cr"],
            ["Time window", "8760 Simulation control: Full year / One month / One week / One day"],
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
    add_para(
        doc,
        "This User Guide was regenerated to match the current product: Create New / Open Existing (.pto.zip) / "
        "Save Project, architecture asset selection, per-asset network charges, Additional costs, Compliance only "
        "in Project Setup, simplified BESS inputs (power_mw caps charge & discharge; ideal 100% efficiency; "
        "removed charge/discharge efficiency and max charge/discharge power), Chrome-tab launch, "
        "Quit App and tab-close shutdown of background processes, single-instance reuse, LAN sharing, "
        "on-screen parameter help, compact Lakh/Cr formatting, 8760 Time window controls, and Section 17A "
        "detailed calculations (profiles, dispatch, RE/CFE, compliance costs, CAPEX/OPEX/CRF, ₹/kWh, "
        "NPV/IRR/payback, incremental vs DISCOM, ledger identities, optimization ranking).",
    )
    add_para(doc, DISCLAIMER, italic=True, size=10)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
