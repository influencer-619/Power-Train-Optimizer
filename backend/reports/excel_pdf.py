"""Excel and PDF report generation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.paths import data_dir
from backend.services.project_service import get_project
from backend.services.run_service import get_simulation
from config.defaults import DISCLAIMER, flatten_assumptions, has_default_assumptions


def export_excel(project_id: int, simulation_id: int | None = None) -> Path:
    project = get_project(project_id)
    sim = get_simulation(simulation_id) if simulation_id else None
    wb = Workbook()

    ws = wb.active
    ws.title = "Summary"
    ws.append(["PowerTrain Optimizer Report"])
    ws.append(["Generated", datetime.utcnow().isoformat()])
    ws.append(["Project", project["name"]])
    ws.append(["Model Version", project["model_version"]])
    ws.append(["Has Default Assumptions", has_default_assumptions(project["config"])])
    if sim:
        feas = sim.get("feasibility") or (sim.get("validation") or {}).get("feasibility") or {}
        dq = sim.get("data_quality") or (sim.get("validation") or {}).get("data_quality") or {}
        ws.append(["Feasibility", feas.get("status")])
        ws.append(["Can Recommend", feas.get("can_recommend")])
        ws.append(["Data Quality", dq.get("overall")])
        ws.append(["Config Hash", sim.get("config_hash")])
        ws.append(["Results Stale", sim.get("results_stale")])
        for k, v in sim["kpis"].items():
            if k == "cfe_analytics":
                continue
            if isinstance(v, (dict, list)):
                continue
            ws.append([k, v])

    ws_p = wb.create_sheet("Project")
    ws_p.append(["Section", "Parameter", "Value", "Unit", "Source"])
    for row in flatten_assumptions(project["config"]):
        ws_p.append([row["parameter"].split(".")[0], row["parameter"], row["value"], row["unit"], row["source"]])

    ws_a = wb.create_sheet("Assumptions")
    ws_a.append(["Parameter", "Value", "Unit", "Source", "Type", "Description", "Editable"])
    for row in flatten_assumptions(project["config"]):
        ws_a.append([row["parameter"], row["value"], row["unit"], row["source"], row["type"], row["description"], row["editable"]])

    for title, section in [
        ("Load", "load"),
        ("Solar", "solar"),
        ("Wind", "wind"),
        ("BESS", "bess"),
        ("Grid", "grid"),
    ]:
        w = wb.create_sheet(title)
        w.append(["Parameter", "Value", "Unit", "Source"])
        for k, p in project["config"][section].items():
            if isinstance(p, dict) and "value" in p:
                w.append([k, p["value"], p.get("unit", ""), p.get("source", "")])

    if sim:
        w8760 = wb.create_sheet("8760 Results")
        w8760.append(["Note", "Full hourly arrays are stored in NPZ beside the database; monthly aggregates below."])
        wm = wb.create_sheet("Monthly")
        wm.append(list(sim["monthly"][0].keys()) if sim["monthly"] else [])
        for row in sim["monthly"]:
            wm.append(list(row.values()))
        wc = wb.create_sheet("Compliance")
        wc.append(["Block", "JSON"])
        for k, v in sim["compliance"].items():
            wc.append([k, str(v)])
        we = wb.create_sheet("Economics")
        for k, v in sim["financial"].items():
            if not isinstance(v, (dict, list)):
                we.append([k, v])
        inc = sim["financial"].get("incremental") or {}
        if inc:
            we.append([])
            we.append(["INCREMENTAL VS DISCOM", ""])
            for k, v in inc.items():
                if not isinstance(v, (dict, list)):
                    we.append([k, v])
        db = sim["financial"].get("discom_baseline") or {}
        if db:
            we.append([])
            we.append(["GRID-ONLY BASELINE (DISCOM)", ""])
            for k, v in db.items():
                we.append([k, v])

        wdq = wb.create_sheet("Data Quality")
        dq = sim.get("data_quality") or (sim.get("validation") or {}).get("data_quality") or {}
        for k, v in dq.items():
            wdq.append([k, str(v)])

        wfeas = wb.create_sheet("Feasibility")
        feas = sim.get("feasibility") or (sim.get("validation") or {}).get("feasibility") or {}
        for k, v in feas.items():
            if k == "binding_constraints":
                continue
            if isinstance(v, (dict, list)):
                wfeas.append([k, str(v)])
            else:
                wfeas.append([k, v])
        wfeas.append([])
        wfeas.append(["Binding code", "Message", "Actual", "Target"])
        for b in feas.get("binding_constraints") or []:
            wfeas.append([b.get("code"), b.get("message"), b.get("actual"), b.get("target")])

        led = sim.get("energy_ledger")
        if led:
            wl = wb.create_sheet("Energy Ledger")
            wl.append(["Flow", "MWh"])
            for k, v in (led.get("annual") or {}).get("flows", {}).items():
                wl.append([k, v])
            wl.append([])
            wl.append(["Reconciliation", ""])
            for k, v in (led.get("annual") or {}).get("reconciliation", {}).items():
                wl.append([k, v])
            wlm = wb.create_sheet("Ledger Monthly")
            months = led.get("monthly") or []
            if months:
                keys = ["month"] + list(months[0].get("flows", {}).keys()) + ["ac_gap", "ok"]
                wlm.append(keys)
                for mrow in months:
                    flows = mrow.get("flows", {})
                    rec = mrow.get("reconciliation", {})
                    wlm.append(
                        [mrow.get("month")]
                        + [flows.get(k) for k in months[0].get("flows", {}).keys()]
                        + [rec.get("ac_balance_gap_mwh"), rec.get("ok")]
                    )

        ca = sim.get("cfe_analytics") or sim["kpis"].get("cfe_analytics")
        if ca:
            wcfe = wb.create_sheet("CFE Analytics")
            for k, v in ca.items():
                if k == "duration_curve":
                    continue
                wcfe.append([k, v if not isinstance(v, (dict, list)) else str(v)])

    out = data_dir() / "exports" / f"PowerTrain_Project{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out


def export_pdf(project_id: int, simulation_id: int | None = None) -> Path:
    project = get_project(project_id)
    sim = get_simulation(simulation_id) if simulation_id else None
    out = data_dir() / "exports" / f"PowerTrain_Project{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)

    styles = getSampleStyleSheet()
    title = ParagraphStyle("T", parent=styles["Heading1"], textColor=colors.HexColor("#0b2a4a"))
    body = styles["BodyText"]
    story = []
    story.append(Paragraph("PowerTrain Optimizer — Executive Report (V2)", title))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Project: <b>{project['name']}</b>", body))
    story.append(Paragraph(f"Model Version: {project['model_version']}", body))
    story.append(Paragraph(f"Generated: {datetime.utcnow().isoformat()}Z", body))
    story.append(Spacer(1, 12))

    if has_default_assumptions(project["config"]):
        story.append(
            Paragraph(
                "<b>DEFAULT ASSUMPTIONS IN USE</b> — replace with project-specific data before investment decisions.",
                body,
            )
        )
        story.append(Spacer(1, 8))

    story.append(Paragraph("Executive Summary", styles["Heading2"]))
    if sim:
        k = sim["kpis"]
        f = sim["financial"]
        feas = sim.get("feasibility") or (sim.get("validation") or {}).get("feasibility") or {}
        dq = sim.get("data_quality") or (sim.get("validation") or {}).get("data_quality") or {}
        data = [
            ["Metric", "Value"],
            ["Architecture", sim["structure"]],
            ["Feasibility", feas.get("status", "—")],
            ["Data quality", dq.get("overall", "—")],
            ["Annual RE %", f"{k['annual_re_pct']:.2f}"],
            ["Hourly CFE min %", f"{k['hourly_cfe_min_pct']:.2f}"],
            ["CFE pass mode", str((sim.get("compliance") or {}).get("hourly_cfe", {}).get("pass_mode", "—"))],
            ["Grid GWh", f"{k['grid_gwh']:.3f}"],
            ["Curtailment %", f"{k['curtailment_pct']:.2f}"],
            ["BESS", f"{k['bess_mw']:.1f} MW / {k['bess_mwh']:.1f} MWh"],
            ["TOTAL COST OF DELIVERED ENERGY ₹/kWh", f"{f['cost_per_kwh']:.4f}"],
            ["NPV (₹ Cr)", f"{f.get('npv_cr', 0):.2f}"],
            ["IRR %", f"{f.get('irr_pct') if f.get('irr_pct') is not None else '—'}"],
            ["Payback years", f"{f.get('payback_years') if f.get('payback_years') is not None else '—'}"],
            ["Economics basis", str(f.get("economics_basis", "—"))],
        ]
        t = Table(data, hAlign="LEFT")
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b2a4a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]
            )
        )
        story.append(t)
        story.append(Spacer(1, 12))
        if feas.get("binding_constraints"):
            story.append(Paragraph("Binding constraints", styles["Heading2"]))
            for b in feas["binding_constraints"][:8]:
                story.append(Paragraph(f"• <b>{b.get('code')}</b>: {b.get('message')}", body))
            story.append(Spacer(1, 8))
        db = f.get("discom_baseline") or {}
        if db:
            story.append(Paragraph("GRID-ONLY BASELINE (DISCOM)", styles["Heading2"]))
            story.append(
                Paragraph(
                    f"Cost ₹{db.get('cost_per_kwh', 0):.4f}/kWh — {db.get('reason', '')}",
                    body,
                )
            )
            story.append(Spacer(1, 8))
        story.append(Paragraph("Compliance", styles["Heading2"]))
        for key in ("annual_re", "hourly_cfe", "rpo", "rco", "eso"):
            block = sim["compliance"][key]
            story.append(Paragraph(f"<b>{key}</b>: {block.get('status', '')}", body))
            story.append(Spacer(1, 4))
        if sim.get("results_stale"):
            story.append(Paragraph("<b>STALE RESULTS</b> — re-run simulation before decisions.", body))
    else:
        story.append(Paragraph("No simulation selected. Run a simulation to populate results.", body))

    story.append(Spacer(1, 16))
    story.append(Paragraph("Disclaimer", styles["Heading2"]))
    story.append(Paragraph(DISCLAIMER, body))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Assumptions and methodology are available inside the application pages.", body))

    doc = SimpleDocTemplate(str(out), pagesize=A4)
    doc.build(story)
    return out
