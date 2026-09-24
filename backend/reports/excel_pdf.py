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
from config.defaults import DISCLAIMER, MODEL_VERSION, flatten_assumptions, has_default_assumptions


def _xlsx_header_fill():
    from openpyxl.styles import PatternFill

    return PatternFill("solid", fgColor="0B2A4A")


def _xlsx_alt_fill():
    from openpyxl.styles import PatternFill

    return PatternFill("solid", fgColor="F4F7FA")


def _xlsx_gold_fill():
    from openpyxl.styles import PatternFill

    return PatternFill("solid", fgColor="C4A35A")


def _xlsx_fonts():
    from openpyxl.styles import Font

    return {
        "title": Font(name="Calibri", bold=True, size=16, color="0B2A4A"),
        "subtitle": Font(name="Calibri", size=11, color="5B6B7A"),
        "section": Font(name="Calibri", bold=True, size=12, color="0B2A4A"),
        "header": Font(name="Calibri", bold=True, size=10, color="FFFFFF"),
        "label": Font(name="Calibri", bold=True, size=10, color="0B2A4A"),
        "body": Font(name="Calibri", size=10, color="0B2A4A"),
        "muted": Font(name="Calibri", italic=True, size=9, color="5B6B7A"),
    }


def _style_header_row(ws, row: int, cols: int):
    from openpyxl.styles import Alignment, Border, Side

    fonts = _xlsx_fonts()
    fill = _xlsx_header_fill()
    thin = Border(
        left=Side(style="thin", color="D0D7DE"),
        right=Side(style="thin", color="D0D7DE"),
        top=Side(style="thin", color="D0D7DE"),
        bottom=Side(style="thin", color="D0D7DE"),
    )
    for c in range(1, cols + 1):
        cell = ws.cell(row, c)
        cell.fill = fill
        cell.font = fonts["header"]
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin


def _style_body_block(ws, start_row: int, end_row: int, cols: int):
    from openpyxl.styles import Alignment, Border, Side

    fonts = _xlsx_fonts()
    alt = _xlsx_alt_fill()
    thin = Border(
        left=Side(style="thin", color="D0D7DE"),
        right=Side(style="thin", color="D0D7DE"),
        top=Side(style="thin", color="D0D7DE"),
        bottom=Side(style="thin", color="D0D7DE"),
    )
    for r in range(start_row, end_row + 1):
        for c in range(1, cols + 1):
            cell = ws.cell(r, c)
            cell.font = fonts["body"]
            cell.border = thin
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            if c > 1:
                cell.alignment = Alignment(horizontal="right", vertical="center", wrap_text=True)
            if (r - start_row) % 2 == 1:
                cell.fill = alt


def _autosize(ws, min_w=12, max_w=42):
    for col in ws.columns:
        letter = col[0].column_letter
        width = min_w
        for cell in col:
            if cell.value is None:
                continue
            width = max(width, min(max_w, len(str(cell.value)) + 2))
        ws.column_dimensions[letter].width = width


def _write_kv_table(ws, start_row: int, headers: list, rows: list[list], title: str | None = None) -> int:
    fonts = _xlsx_fonts()
    r = start_row
    if title:
        ws.cell(r, 1, title).font = fonts["section"]
        r += 1
    for c, h in enumerate(headers, 1):
        ws.cell(r, c, h)
    _style_header_row(ws, r, len(headers))
    r += 1
    body_start = r
    for row in rows:
        for c, val in enumerate(row, 1):
            ws.cell(r, c, _excel_safe(val))
        r += 1
    if rows:
        _style_body_block(ws, body_start, r - 1, len(headers))
    return r + 1


def _excel_safe(val):
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, (list, dict, tuple, set)):
        try:
            import json

            return json.dumps(val, ensure_ascii=False)
        except Exception:
            return str(val)
    try:
        if hasattr(val, "item"):
            return val.item()
    except Exception:
        pass
    return str(val)


def export_excel(project_id: int, simulation_id: int | None = None) -> Path:
    """Professional workbook aligned with Run Analysis (Captive + Hybrid + DISCOM baseline)."""
    from openpyxl.styles import Alignment, Font
    from openpyxl.utils import get_column_letter

    from backend.services.run_service import compare_architectures

    project = get_project(project_id)
    cfg = project["config"]
    fonts = _xlsx_fonts()
    generated = datetime.now().strftime("%d %b %Y, %H:%M")
    period = _study_period_label(cfg)
    name = project.get("name") or _v(cfg, "general.project_name", "Data Centre Project")

    compare = None
    try:
        compare = compare_architectures(project_id)
    except Exception:
        compare = None

    snaps: dict[str, dict] = {}
    if compare and compare.get("architectures"):
        for key in ("DISCOM", "CAPTIVE", "HYBRID"):
            if key in compare["architectures"]:
                snap = _arch_snapshot(compare["architectures"][key])
                snap["structure"] = key
                snaps[key] = snap
    else:
        single = get_simulation(simulation_id) if simulation_id else None
        if single:
            snap = _arch_snapshot(single)
            key = str(single.get("structure") or "RUN")
            snap["structure"] = key
            snaps[key] = snap

    wb = Workbook()

    # —— Cover ——
    ws = wb.active
    ws.title = "Cover"
    ws["A1"] = "AVAADA · Data Center PowerTrain"
    ws["A1"].font = fonts["title"]
    ws["A2"] = "Data Centre Power Economics — Excel Report"
    ws["A2"].font = fonts["subtitle"]
    ws["A3"] = "Captive & Hybrid procurement · Tariff / PPA stacks · CFE & carbon"
    ws["A3"].font = fonts["muted"]
    cover_meta = [
        ["Project", str(name)],
        ["Study period", period],
        ["Model version", str(project.get("model_version") or MODEL_VERSION)],
        ["Generated", generated],
        ["Scope", "Captive + Hybrid (equal analysis); DISCOM = savings baseline only"],
        ["Viewpoint", "DC buys Solar / Wind / BESS energy at fixed Rs/kWh — no plant CAPEX/MW"],
    ]
    r = _write_kv_table(ws, 5, ["Field", "Value"], cover_meta)
    ws.cell(r, 1, DISCLAIMER).font = fonts["muted"]
    ws.merge_cells(start_row=r, start_column=1, end_row=r + 3, end_column=2)
    ws.cell(r, 1).alignment = Alignment(wrap_text=True, vertical="top")
    _autosize(ws)

    # —— Setup ——
    ws_s = wb.create_sheet("Setup")
    ws_s["A1"] = "1. Project setup snapshot"
    ws_s["A1"].font = fonts["section"]
    it = _v(cfg, "load.it_load_mw", _v(cfg, "data_center.it_capacity_mw"))
    pue = _v(cfg, "load.pue", _v(cfg, "data_center.pue"))
    peak = _v(cfg, "load.peak_load_mw")
    lf1 = _v(cfg, "load.load_factor_s1_pct", _v(cfg, "load.load_factor_pct"))
    storage = _v(cfg, "commercial.excel_bess_ppa_inr_per_kwh", 0)
    blend = _v(cfg, "commercial.cost_blend_basis", "TARGET_POWER_PCT")
    cfe_t = _v(cfg, "compliance.hourly_cfe_target_pct", 90)
    re_t = _v(cfg, "compliance.annual_re_target_pct", 90)
    setup_rows = [
        ["IT load (MW)", it],
        ["PUE", pue],
        ["Peak load (MW)", peak],
        ["Load factor S1 (%)", lf1],
        ["Storage tariff (Rs/kWh)", storage],
        ["Cost blend basis", str(blend)],
        ["Annual RE target (%)", re_t],
        ["Hourly CFE target (%)", cfe_t],
        ["CFE Pass rule", "Every hour CFE% ≥ target (min hourly CFE ≥ target)"],
        [
            "Captive mix G|S|W|B (%)",
            f"{_v(cfg, 'commercial.mix_discom_pct', 0)}|{_v(cfg, 'commercial.mix_solar_pct', 0)}|"
            f"{_v(cfg, 'commercial.mix_wind_pct', 0)}|{_v(cfg, 'commercial.mix_bess_pct', 0)}",
        ],
    ]
    # Prefer architecture profiles if present — show generic commercial mix from last config
    _write_kv_table(ws_s, 3, ["Parameter", "Value"], setup_rows)
    _autosize(ws_s)

    # —— Comparison ——
    ws_c = wb.create_sheet("Comparison")
    ws_c["A1"] = "2. Architecture comparison (Run Analysis)"
    ws_c["A1"].font = fonts["section"]
    ws_c["A2"] = "DISCOM is baseline only. Captive and Hybrid are analysed equally."
    ws_c["A2"].font = fonts["muted"]

    arch_order = [k for k in ("DISCOM", "CAPTIVE", "HYBRID") if k in snaps]
    if arch_order:
        headers = ["Metric"] + arch_order

        def _row(label, getter):
            return [label] + [getter(snaps[a]) for a in arch_order]

        compare_rows = [
            _row("Energy Cost (Rs/kWh)", lambda s: round(float(s["power_cost"]), 4) if s.get("power_cost") is not None else None),
            _row("Blended energy rate (Rs/kWh)", lambda s: round(float(s["blended"]), 4) if s.get("blended") is not None else None),
            _row("Annual bill (Rs Cr)", lambda s: round(float(s["bill_cr"]), 2) if s.get("bill_cr") is not None else None),
            _row(
                "Savings vs DISCOM Y1 (Rs Cr)",
                lambda s: None if s.get("structure") == "DISCOM" else (round(float(s["savings_cr"]), 2) if s.get("savings_cr") is not None else None),
            ),
            _row(
                "NPV of savings (Rs Cr)",
                lambda s: None if s.get("structure") == "DISCOM" else (round(float(s["npv_cr"]), 2) if s.get("npv_cr") is not None else None),
            ),
            _row("Contracted RE / CFE mix (%)", lambda s: round(float(s["re_pct"]), 1) if s.get("re_pct") is not None else None),
            _row("Target Grid (%)", lambda s: round(float(s["target_grid"]), 1) if s.get("target_grid") is not None else None),
            _row("Target RE (%)", lambda s: round(float(s["target_re"]), 1) if s.get("target_re") is not None else None),
            _row("Simulated Grid (%)", lambda s: round(float(s["sim_grid"]), 1) if s.get("sim_grid") is not None else None),
            _row("Simulated RE (%)", lambda s: round(float(s["sim_re"]), 1) if s.get("sim_re") is not None else None),
            _row("Hourly CFE min (%)", lambda s: round(float(s["cfe_min"]), 1) if s.get("cfe_min") is not None else None),
            _row("Hourly CFE mean (%)", lambda s: round(float(s["cfe_mean"]), 1) if s.get("cfe_mean") is not None else None),
            _row("Hours ≥ CFE target (%)", lambda s: round(float(s["hours_meet"]), 1) if s.get("hours_meet") is not None else None),
            _row("Hourly CFE Pass/Fail", lambda s: s.get("cfe_status")),
            _row("Annual RE Pass/Fail", lambda s: s.get("re_status")),
            _row(
                "Carbon saved (tCO₂)",
                lambda s: None if s.get("structure") == "DISCOM" else (round(float(s["carbon_saved"]), 0) if s.get("carbon_saved") is not None else None),
            ),
            _row("Annual load (MWh)", lambda s: round(float(s["load_mwh"]), 2) if s.get("load_mwh") is not None else None),
        ]
        _write_kv_table(ws_c, 4, headers, compare_rows)
    else:
        ws_c["A4"] = "No analysis results. Run Analysis in the app, then export again."
        ws_c["A4"].font = fonts["body"]
    _autosize(ws_c)

    # —— Per-architecture detail sheets ——
    for arch in ("CAPTIVE", "HYBRID", "DISCOM"):
        if arch not in snaps:
            continue
        s = snaps[arch]
        raw = (compare or {}).get("architectures", {}).get(arch) or {}
        fin = raw.get("financial") or {}
        xt = fin.get("excel_tariff") or {}
        ws_a = wb.create_sheet(arch.title() if arch != "DISCOM" else "DISCOM_Baseline")
        ws_a["A1"] = f"{arch} — economics, mix & CFE"
        ws_a["A1"].font = fonts["section"]

        detail = [
            ["Energy Cost (Rs/kWh)", s.get("power_cost")],
            ["Blended energy rate (Rs/kWh)", s.get("blended")],
            ["DISCOM rate (Rs/kWh)", s.get("discom_rate")],
            ["Solar stack (Rs/kWh)", s.get("solar_rate")],
            ["Wind stack (Rs/kWh)", s.get("wind_rate")],
            ["Storage tariff (Rs/kWh)", s.get("bess_rate")],
            ["Grid %", s.get("grid_pct")],
            ["Solar %", s.get("solar_pct")],
            ["Wind %", s.get("wind_pct")],
            ["BESS %", s.get("bess_pct")],
            ["RE / CFE mix %", s.get("re_pct")],
            ["Target Grid | RE %", f"{s.get('target_grid')} | {s.get('target_re')}"],
            ["Simulated Grid | RE %", f"{s.get('sim_grid')} | {s.get('sim_re')}"],
            ["Cost blend basis", s.get("blend_basis")],
            ["Annual load (MWh)", s.get("load_mwh")],
            ["Annual bill (Rs Cr)", s.get("bill_cr")],
            ["Savings vs DISCOM Y1 (Rs Cr)", s.get("savings_cr")],
            ["NPV of savings (Rs Cr)", s.get("npv_cr")],
            ["Carbon baseline (tCO₂)", s.get("baseline_tco2")],
            ["Carbon actual (tCO₂)", s.get("actual_tco2")],
            ["Carbon saved (tCO₂)", s.get("carbon_saved")],
            ["Hourly CFE min %", s.get("cfe_min")],
            ["Hourly CFE mean %", s.get("cfe_mean")],
            ["Hours ≥ target %", s.get("hours_meet")],
            ["Hourly CFE status", s.get("cfe_status")],
            ["Annual RE %", s.get("annual_re")],
            ["Annual RE status", s.get("re_status")],
        ]
        r = _write_kv_table(ws_a, 3, ["Item", "Value"], detail, title=None)

        # Tariff stack lines from excel_tariff cost components if present
        stack_rows = []
        for key, label in (
            ("grid_energy_cost_inr", "Grid energy cost (Rs)"),
            ("solar_energy_cost_inr", "Solar energy cost (Rs)"),
            ("wind_energy_cost_inr", "Wind energy cost (Rs)"),
            ("bess_energy_cost_inr", "BESS / Storage cost (Rs)"),
            ("annual_energy_inr", "Total energy cost (Rs)"),
        ):
            if xt.get(key) is not None:
                stack_rows.append([label, xt.get(key)])
        if stack_rows:
            r = _write_kv_table(ws_a, r, ["Bill component", "Amount"], stack_rows, title="Tariff bill components")

        # Monthly for this architecture if available
        monthly = raw.get("monthly") or []
        if monthly:
            keys = list(monthly[0].keys())
            mrows = [[m.get(k) for k in keys] for m in monthly]
            r = _write_kv_table(ws_a, r, keys, mrows, title="Monthly energy aggregates")

        _autosize(ws_a)

    # —— Assumptions register (buyer-facing) ——
    ws_as = wb.create_sheet("Assumptions")
    ws_as["A1"] = "Assumptions register (buyer-facing — plant leftovers excluded)"
    ws_as["A1"].font = fonts["section"]
    arows = []
    for row in flatten_assumptions(cfg):
        arows.append(
            [
                row["parameter"],
                row["value"],
                row["unit"],
                row["source"],
                row.get("type"),
                row.get("description"),
            ]
        )
    _write_kv_table(
        ws_as,
        3,
        ["Parameter", "Value", "Unit", "Source", "Type", "Description"],
        arows,
    )
    _autosize(ws_as, max_w=48)

    # —— Methodology ——
    ws_m = wb.create_sheet("Methodology")
    ws_m["A1"] = "Methodology (commercial buyer)"
    ws_m["A1"].font = fonts["section"]
    notes = [
        ["Bill", "Annual load × blended Rs/kWh (+ demand/fixed/compliance if configured)"],
        ["Blended Rs/kWh", "Discom×G% + Solar×S% + Wind×W% + Storage×B% (Architecture mix)"],
        ["Savings vs DISCOM", "100% DISCOM bill − architecture bill (Year 1)"],
        ["NPV of savings", "PV of yearly bill savings over project life at discount rate (no plant CAPEX)"],
        ["BESS", "Storage tariff Rs/kWh only — no plant MW/MWh"],
        ["Hourly CFE Pass", "Min hourly CFE ≥ target and 100% of hours ≥ target"],
        ["Hourly CFE formula", "Min(Load, Load×(Solar%+Wind%+BESS%)/100) / Load × 100 — Architecture mix, firm every hour"],
        ["Target vs Simulated", "Both = Architecture contracted mix % on the buyer path"],
        ["Illustrative profiles", "Removed — Solar/Wind/BESS MW are firm Architecture mix × load (no plant shapes)"],
    ]
    _write_kv_table(ws_m, 3, ["Topic", "Rule"], notes)
    ws_m.cell(14, 1, DISCLAIMER).font = fonts["muted"]
    ws_m.merge_cells("A14:B18")
    ws_m["A14"].alignment = Alignment(wrap_text=True, vertical="top")
    _autosize(ws_m, max_w=60)

    # Freeze panes / print setup on key sheets
    for sheet in wb.worksheets:
        sheet.freeze_panes = "A2" if sheet.title != "Cover" else None
        sheet.print_title_rows = "1:1"
        sheet.page_setup.orientation = "landscape"
        sheet.page_setup.fitToPage = True
        sheet.page_setup.fitToWidth = 1
        sheet.page_setup.fitToHeight = 0

    out = data_dir() / "exports" / f"PowerTrain_Project{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out


# —— Professional PDF helpers ——

_NAVY = colors.HexColor("#0B2A4A")
_TEAL = colors.HexColor("#1B6B5A")
_GOLD = colors.HexColor("#C4A35A")
_LIGHT = colors.HexColor("#F4F7FA")
_LINE = colors.HexColor("#D0D7DE")
_MUTED = colors.HexColor("#5B6B7A")
_WHITE = colors.white
_FAIL = colors.HexColor("#B42318")
_PASS = colors.HexColor("#067647")

# Helvetica cannot draw ₹ / ₂ / • — register Arial (Windows) when available.
_PDF_FONT = "Helvetica"
_PDF_FONT_BOLD = "Helvetica-Bold"
_PDF_FONT_ITALIC = "Helvetica-Oblique"
try:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    _arial = Path(r"C:\Windows\Fonts\arial.ttf")
    _arial_bd = Path(r"C:\Windows\Fonts\arialbd.ttf")
    _arial_i = Path(r"C:\Windows\Fonts\ariali.ttf")
    if _arial.exists() and _arial_bd.exists():
        pdfmetrics.registerFont(TTFont("PTOArial", str(_arial)))
        pdfmetrics.registerFont(TTFont("PTOArial-Bold", str(_arial_bd)))
        _PDF_FONT = "PTOArial"
        _PDF_FONT_BOLD = "PTOArial-Bold"
        if _arial_i.exists():
            pdfmetrics.registerFont(TTFont("PTOArial-Italic", str(_arial_i)))
            _PDF_FONT_ITALIC = "PTOArial-Italic"
except Exception:
    pass


def _v(cfg: dict, path: str, default=None):
    try:
        node = cfg
        for p in path.split("."):
            node = node[p]
        return node["value"] if isinstance(node, dict) and "value" in node else node
    except Exception:
        return default


def _fmt_num(x, d=2, suffix="") -> str:
    if x is None:
        return "—"
    try:
        n = float(x)
    except (TypeError, ValueError):
        return str(x)
    if not (n == n):  # NaN
        return "—"
    # Indian-style grouping for large energy / carbon figures (readable, no Lakh rounding).
    if abs(n) >= 1000 and d == 0:
        return f"{n:,.0f}{suffix}".replace(",", ",")
    return f"{n:,.{d}f}{suffix}"


def _fmt_inr_kwh(x) -> str:
    return f"Rs {_fmt_num(x, 4)}/kWh" if x is not None else "—"


def _fmt_cr(x) -> str:
    return f"Rs {_fmt_num(x, 2)} Cr" if x is not None else "—"


def _pct(x, d=1) -> str:
    return _fmt_num(x, d, "%")


def _safe_text(s: str) -> str:
    """Normalize glyphs that break in PDF fonts / extraction."""
    if s is None:
        return ""
    t = str(s)
    repl = {
        "₹": "Rs ",
        "₂": "2",
        "×": "x",
        "≥": ">=",
        "–": "-",
        "—": "-",
        "·": "-",
        "•": "-",
        "⚠": "",
        "\u00a0": " ",
    }
    for a, b in repl.items():
        t = t.replace(a, b)
    return t


def _cell(text, style=None) -> Paragraph:
    """Wrap table cell text so long labels wrap instead of clipping."""
    st = style or ParagraphStyle(
        "Cell",
        fontName=_PDF_FONT,
        fontSize=8.5,
        textColor=_NAVY,
        leading=11,
    )
    return Paragraph(_safe_text(text).replace("\n", "<br/>"), st)


def _study_period_label(cfg: dict) -> str:
    months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    try:
        sm = int(_v(cfg, "general.study_start_month", 1) or 1)
        em = int(_v(cfg, "general.study_end_month", 12) or 12)
        year = _v(cfg, "general.calendar_year", "")
        return f"{months[sm]}-{months[em]} {year}".strip()
    except Exception:
        return "—"


def _styled_table(data, col_widths=None, header=True) -> Table:
    # Ensure all cells are Paragraphs for wrapping + unicode-safe font.
    cell_style = ParagraphStyle(
        "TblCell",
        fontName=_PDF_FONT,
        fontSize=8.5,
        textColor=_NAVY,
        leading=11,
    )
    head_style = ParagraphStyle(
        "TblHead",
        fontName=_PDF_FONT_BOLD,
        fontSize=8.5,
        textColor=_WHITE,
        leading=11,
        alignment=1,
    )
    norm = []
    for ri, row in enumerate(data):
        out_row = []
        for ci, val in enumerate(row):
            if isinstance(val, Paragraph):
                out_row.append(val)
            else:
                st = head_style if (header and ri == 0) else cell_style
                out_row.append(_cell("" if val is None else str(val), st))
        norm.append(out_row)

    t = Table(norm, colWidths=col_widths, hAlign="LEFT", repeatRows=1 if header else 0)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), _PDF_FONT),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), _NAVY),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.4, _LINE),
        ("BOX", (0, 0), (-1, -1), 0.8, _NAVY),
    ]
    if header and norm:
        style.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), _WHITE),
                ("FONTNAME", (0, 0), (-1, 0), _PDF_FONT_BOLD),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ]
        )
        for i in range(1, len(norm)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), _LIGHT))
    t.setStyle(TableStyle(style))
    return t


def _section_title(text: str, styles) -> Paragraph:
    return Paragraph(_safe_text(text), styles["Section"])


def _arch_snapshot(row: dict) -> dict:
    """Normalize one architecture run into buyer-facing metrics."""
    fin = row.get("financial") or {}
    xt = fin.get("excel_tariff") or {}
    k = row.get("kpis") or {}
    ca = row.get("cfe_analytics") or k.get("cfe_analytics") or {}
    carbon = fin.get("carbon") or {}
    comp = row.get("compliance") or {}
    cfe_block = comp.get("hourly_cfe") or {}
    re_block = comp.get("annual_re") or {}
    bill = xt.get("annual_bill_cr")
    if bill is None:
        bill = xt.get("annual_energy_cr")
    if bill is None:
        bill = float(fin.get("total_annual_cost_inr") or 0.0) / 1e7
    # Headline Energy Cost = blended / DISCOM rate (commercial path).
    energy_cost = fin.get("energy_cost_per_kwh")
    if energy_cost is None:
        energy_cost = xt.get("blended_rate_inr_per_kwh")
    if energy_cost is None:
        energy_cost = fin.get("cost_per_kwh")
    delivered = fin.get("delivered_cost_per_kwh")
    if delivered is None:
        delivered = fin.get("cost_per_kwh")
    return {
        "structure": row.get("structure") or xt.get("structure"),
        "energy_cost": energy_cost,
        "power_cost": energy_cost,  # alias for older excel rows
        "delivered_cost": delivered,
        "blended": xt.get("blended_rate_inr_per_kwh"),
        "discom_rate": xt.get("discom_rate_inr_per_kwh"),
        "solar_rate": xt.get("solar_rate_inr_per_kwh"),
        "wind_rate": xt.get("wind_rate_inr_per_kwh"),
        "bess_rate": xt.get("bess_rate_inr_per_kwh"),
        "grid_pct": xt.get("grid_pct"),
        "solar_pct": xt.get("solar_pct"),
        "wind_pct": xt.get("wind_pct"),
        "bess_pct": xt.get("bess_pct"),
        "re_pct": xt.get("re_pct") if xt.get("re_pct") is not None else xt.get("cfe_pct"),
        "target_grid": xt.get("target_grid_pct"),
        "target_re": xt.get("target_re_pct"),
        "sim_grid": xt.get("simulated_grid_pct"),
        "sim_re": xt.get("simulated_re_pct"),
        "bill_cr": bill,
        "total_bill_cr": xt.get("total_bill_cr"),
        "savings_cr": xt.get("savings_vs_discom_cr"),
        "npv_cr": fin.get("npv_cr"),
        "load_mwh": xt.get("annual_load_mwh") or carbon.get("annual_load_mwh") or k.get("annual_load_mwh"),
        "carbon_saved": xt.get("carbon_saved_tco2") or carbon.get("carbon_saved_tco2"),
        "baseline_tco2": xt.get("baseline_tco2") or carbon.get("baseline_tco2"),
        "actual_tco2": xt.get("actual_tco2") or carbon.get("actual_tco2"),
        "annual_re": k.get("annual_re_pct"),
        "cfe_min": ca.get("min_hourly_cfe_pct", k.get("hourly_cfe_min_pct")),
        "cfe_mean": ca.get("mean_hourly_cfe_pct", k.get("hourly_cfe_mean_pct")),
        "hours_meet": ca.get("pct_hours_ge_target", k.get("hours_meeting_cfe_target_pct")),
        "cfe_status": cfe_block.get("status") or ("Pass" if ca.get("passed") else ("Fail" if ca.get("passed") is False else None)),
        "re_status": re_block.get("status"),
        "cfe_target": cfe_block.get("target_pct") or ca.get("target_pct"),
        "blend_basis": xt.get("cost_blend_basis") or "TARGET_POWER_PCT",
        "lf_scenarios": row.get("lf_scenarios") or fin.get("lf_scenarios") or [],
    }


def _draw_page_chrome(canvas, doc):
    canvas.saveState()
    w, h = A4
    # Top brand bar
    canvas.setFillColor(_NAVY)
    canvas.rect(0, h - 28, w, 28, fill=1, stroke=0)
    canvas.setFillColor(_GOLD)
    canvas.rect(0, h - 30, w, 2.5, fill=1, stroke=0)
    canvas.setFillColor(_WHITE)
    canvas.setFont(_PDF_FONT_BOLD, 8)
    canvas.drawString(36, h - 18, "AVAADA  |  Data Center PowerTrain")
    canvas.setFont(_PDF_FONT, 7.5)
    canvas.drawRightString(w - 36, h - 18, "Captive & Hybrid · Energy Cost · CFE")
    # Footer
    canvas.setStrokeColor(_LINE)
    canvas.setLineWidth(0.6)
    canvas.line(36, 40, w - 36, 40)
    canvas.setFillColor(_MUTED)
    canvas.setFont(_PDF_FONT, 7)
    canvas.drawString(36, 28, "Confidential - for internal techno-economic evaluation")
    canvas.drawRightString(w - 36, 28, f"Page {doc.page}")
    canvas.restoreState()

def export_pdf(project_id: int, simulation_id: int | None = None) -> Path:
    """Professional multi-page PDF aligned with Dashboard / Economics / Hourly CFE."""
    from backend.services.run_service import compare_architectures

    project = get_project(project_id)
    cfg = project["config"]
    out = data_dir() / "exports" / f"PowerTrain_Project{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)

    # Prefer full Captive + Hybrid compare (same as Run Analysis)
    compare = None
    try:
        compare = compare_architectures(project_id)
    except Exception:
        compare = None

    single = get_simulation(simulation_id) if simulation_id else None

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            "CoverTitle",
            parent=styles["Title"],
            fontName=_PDF_FONT_BOLD,
            fontSize=20,
            textColor=_NAVY,
            spaceAfter=6,
            leading=24,
        )
    )
    styles.add(
        ParagraphStyle(
            "CoverSub",
            parent=styles["Normal"],
            fontName=_PDF_FONT,
            fontSize=10,
            textColor=_MUTED,
            spaceAfter=4,
            leading=13,
        )
    )
    styles.add(
        ParagraphStyle(
            "Section",
            parent=styles["Heading2"],
            fontName=_PDF_FONT_BOLD,
            fontSize=11,
            textColor=_NAVY,
            spaceBefore=14,
            spaceAfter=8,
            borderPadding=2,
            leading=14,
        )
    )
    styles.add(
        ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontName=_PDF_FONT,
            fontSize=9,
            textColor=_NAVY,
            leading=12,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            "Muted",
            parent=styles["Normal"],
            fontName=_PDF_FONT,
            fontSize=8,
            textColor=_MUTED,
            leading=11,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            "FootNote",
            parent=styles["Normal"],
            fontName=_PDF_FONT_ITALIC,
            fontSize=7.5,
            textColor=_MUTED,
            leading=10,
        )
    )

    story: list = []
    generated = datetime.now().strftime("%d %b %Y, %H:%M")
    period = _study_period_label(cfg)
    name = project.get("name") or _v(cfg, "general.project_name", "Data Centre Project")

    # —— Cover ——
    story.append(Paragraph("Data Center PowerTrain", styles["CoverTitle"]))
    story.append(Paragraph(_safe_text("Captive & Hybrid · Energy Cost · CFE"), styles["CoverSub"]))
    story.append(
        Paragraph(
            _safe_text("Data centre power economics - Tariff / PPA stacks - CFE & carbon"),
            styles["CoverSub"],
        )
    )
    story.append(Spacer(1, 10))
    meta = [
        ["Project", str(name)],
        ["Study period", period],
        ["Model version", str(project.get("model_version") or MODEL_VERSION)],
        ["Generated", generated],
        ["Report scope", "Captive + Hybrid (equal analysis). DISCOM = savings baseline only"],
    ]
    story.append(_styled_table(meta, col_widths=[120, 340], header=False))
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            _safe_text(
                "This report summarises Year-1 Energy Cost (Rs/kWh), annual energy bill, "
                "savings vs 100% DISCOM, NPV of savings, Architecture RE mix %, Storage tariff, "
                "and Hourly CFE Pass/Fail - matching the in-app analysis."
            ),
            styles["Body"],
        )
    )

    # —— Setup snapshot ——
    story.append(_section_title("1. Project setup snapshot", styles))
    it = _v(cfg, "load.it_load_mw", _v(cfg, "data_center.it_capacity_mw", "—"))
    pue = _v(cfg, "load.pue", _v(cfg, "data_center.pue", "—"))
    peak = _v(cfg, "load.peak_load_mw", "—")
    lf1 = _v(cfg, "load.load_factor_s1_pct", _v(cfg, "load.load_factor_pct", "—"))
    lf2 = _v(cfg, "load.load_factor_s2_pct", None)
    lf3 = _v(cfg, "load.load_factor_s3_pct", None)
    lf4 = _v(cfg, "load.load_factor_s4_pct", None)
    storage = _v(cfg, "commercial.excel_bess_ppa_inr_per_kwh", 0)
    blend = _v(cfg, "commercial.cost_blend_basis", "TARGET_POWER_PCT")
    cfe_t = _v(cfg, "compliance.hourly_cfe_target_pct", 90)
    re_t = _v(cfg, "compliance.annual_re_target_pct", 90)
    lf_line = f"S1 {_pct(lf1, 0)}"
    for i, lf in enumerate((lf2, lf3, lf4), start=2):
        if lf is not None:
            lf_line += f" | S{i} {_pct(lf, 0)}"
    blend_label = str(blend).replace("_", " ").title().replace("Pct", "%")
    setup_rows = [
        ["Parameter", "Value"],
        ["IT load / PUE / Peak", f"{_fmt_num(it, 1)} MW | PUE {_fmt_num(pue, 2)} | Peak {_fmt_num(peak, 1)} MW"],
        ["Load factors (S1-S4)", lf_line],
        ["Storage tariff (BESS)", _fmt_inr_kwh(storage)],
        ["Cost blend basis", blend_label],
        ["Annual RE target", _pct(re_t, 0)],
        ["Hourly CFE target (24x7)", _pct(cfe_t, 0)],
        ["Pass rule", "Every hour CFE% >= Hourly CFE target (min hourly CFE >= target)"],
    ]
    story.append(_styled_table(setup_rows, col_widths=[160, 300]))
    story.append(
        Paragraph(
            _safe_text(
                "Buyer viewpoint: Solar / Wind / BESS are contracted energy at fixed Rs/kWh. "
                "No generation-plant MW, CAPEX or OPEX is modelled in the bill."
            ),
            styles["Muted"],
        )
    )

    # Build architecture snapshots
    snaps: dict[str, dict] = {}
    if compare and compare.get("architectures"):
        for key in ("DISCOM", "CAPTIVE", "HYBRID"):
            if key in compare["architectures"]:
                snap = _arch_snapshot(compare["architectures"][key])
                snap["structure"] = snap.get("structure") or key
                snaps[key] = snap
    elif single:
        snap = _arch_snapshot(single)
        key = str(snap.get("structure") or single.get("structure") or "RUN")
        snap["structure"] = key
        snaps[key] = snap

    # —— Comparison ——
    story.append(_section_title("2. Architecture comparison (Run Analysis)", styles))
    if snaps:
        arch_order = [k for k in ("CAPTIVE", "HYBRID") if k in snaps]
        if "DISCOM" not in snaps and not arch_order:
            arch_order = list(snaps.keys())
        headers = ["Metric"] + (["DISCOM baseline"] if "DISCOM" in snaps else []) + arch_order

        def cols(getter):
            return [
                getter(snaps[a]) if a in snaps else "—"
                for a in ((["DISCOM"] if "DISCOM" in snaps else []) + arch_order)
            ]

        compare_data = [
            headers,
            ["Energy Cost Rs/kWh"] + cols(lambda s: _fmt_inr_kwh(s.get("energy_cost"))),
            ["Annual energy bill"] + cols(lambda s: _fmt_cr(s.get("bill_cr"))),
            ["Savings vs DISCOM (Y1)"] + cols(
                lambda s: "—" if s.get("structure") == "DISCOM" else _fmt_cr(s.get("savings_cr"))
            ),
            ["NPV of savings"] + cols(
                lambda s: "—" if s.get("structure") == "DISCOM" else _fmt_cr(s.get("npv_cr"))
            ),
            ["RE mix %"] + cols(
                lambda s: "0%*" if s.get("structure") == "DISCOM" else _pct(s.get("re_pct"))
            ),
            ["Target Grid | RE %"] + cols(
                lambda s: f"{_pct(s.get('target_grid'), 0)} | {_pct(s.get('target_re'), 0)}"
            ),
            ["Hourly CFE min %"] + cols(
                lambda s: "0%*" if s.get("structure") == "DISCOM" else _pct(s.get("cfe_min"))
            ),
            ["Hours >= CFE target"] + cols(lambda s: _pct(s.get("hours_meet"))),
            ["Hourly CFE Pass/Fail"] + cols(lambda s: str(s.get("cfe_status") or "—")),
            ["Carbon saved (tCO2)"] + cols(
                lambda s: "—" if s.get("structure") == "DISCOM" else _fmt_num(s.get("carbon_saved"), 0)
            ),
            ["Annual load (MWh)"] + cols(lambda s: _fmt_num(s.get("load_mwh"), 2)),
        ]
        n = len(headers)
        widths = [128] + [332 / (n - 1)] * (n - 1) if n > 1 else [460]
        story.append(_styled_table(compare_data, col_widths=widths))
        story.append(
            Paragraph(
                _safe_text(
                    "* DISCOM is the 100% grid baseline for savings / NPV only - not a selectable architecture. "
                    "Energy Cost = blended rate (Captive/Hybrid) or DISCOM stack rate. "
                    "Annual energy bill = Energy Cost x load kWh (demand/fixed separate)."
                ),
                styles["Muted"],
            )
        )
    else:
        story.append(
            Paragraph(
                "No analysis results available. Run Analysis in the app, then export again.",
                styles["Body"],
            )
        )

    # —— Load-factor scenarios ——
    story.append(_section_title("3. Load-factor scenarios", styles))
    lf_any = False
    for arch in ("CAPTIVE", "HYBRID"):
        if arch not in snaps:
            continue
        rows_lf = snaps[arch].get("lf_scenarios") or []
        if not rows_lf:
            continue
        lf_any = True
        story.append(Paragraph(arch, styles["Body"]))
        lf_tbl = [
            ["Scenario", "LF %", "Energy MWh", "Energy Cost", "Bill Cr", "Savings Cr", "RE %", "CFE min %", "NPV Cr"]
        ]
        for r in rows_lf:
            lf_tbl.append(
                [
                    str(r.get("label") or f"S{r.get('id')}"),
                    _pct(r.get("load_factor_pct"), 0),
                    _fmt_num(r.get("annual_load_mwh"), 2),
                    _fmt_inr_kwh(r.get("cost_per_kwh")),
                    _fmt_cr(r.get("annual_bill_cr") or r.get("annual_energy_cr")),
                    _fmt_cr(r.get("savings_vs_discom_cr")),
                    _pct(r.get("cfe_pct"), 1),
                    _pct(r.get("hourly_cfe_min_pct"), 1),
                    _fmt_cr(r.get("npv_cr")),
                ]
            )
        story.append(
            _styled_table(
                lf_tbl,
                col_widths=[58, 36, 62, 58, 48, 52, 36, 48, 52],
            )
        )
    if not lf_any:
        story.append(
            Paragraph(
                "Load-factor scenario detail not available for this run. Re-run Analysis and export again.",
                styles["Muted"],
            )
        )

    # —— Per-architecture detail ——
    sec_n = 4
    for arch in ("CAPTIVE", "HYBRID"):
        if arch not in snaps:
            continue
        s = snaps[arch]
        story.append(_section_title(f"{sec_n}. {arch.title()} - economics & mix", styles))
        sec_n += 1
        mix_tbl = [
            ["Item", "Value"],
            [
                "Power % (G | S | W | B)",
                f"{_pct(s.get('grid_pct'), 1)} | {_pct(s.get('solar_pct'), 1)} | {_pct(s.get('wind_pct'), 1)} | {_pct(s.get('bess_pct'), 1)}",
            ],
            ["Target power % (Grid | RE)", f"{_pct(s.get('target_grid'), 1)} | {_pct(s.get('target_re'), 1)}"],
            [
                "Simulated energy share (Grid | RE)",
                f"{_pct(s.get('sim_grid'), 1)} | {_pct(s.get('sim_re'), 1)}",
            ],
            ["DISCOM rate", _fmt_inr_kwh(s.get("discom_rate"))],
            ["Solar stack total", _fmt_inr_kwh(s.get("solar_rate"))],
            ["Wind stack total", _fmt_inr_kwh(s.get("wind_rate"))],
            ["Storage tariff (BESS)", _fmt_inr_kwh(s.get("bess_rate"))],
            ["Energy Cost (blended / DISCOM)", _fmt_inr_kwh(s.get("energy_cost"))],
            ["Delivered cost (all-in)", _fmt_inr_kwh(s.get("delivered_cost"))],
            ["Annual load", f"{_fmt_num(s.get('load_mwh'), 2)} MWh"],
            ["Annual energy bill", _fmt_cr(s.get("bill_cr"))],
            ["Savings vs DISCOM (Year 1)", _fmt_cr(s.get("savings_cr"))],
            ["NPV of savings", _fmt_cr(s.get("npv_cr"))],
            [
                "Carbon - baseline / actual / saved",
                f"{_fmt_num(s.get('baseline_tco2'), 0)} / {_fmt_num(s.get('actual_tco2'), 0)} / {_fmt_num(s.get('carbon_saved'), 0)} tCO2",
            ],
        ]
        story.append(_styled_table(mix_tbl, col_widths=[200, 260]))
        story.append(
            Paragraph(
                _safe_text(
                    "Energy Cost = Discom x G% + Solar x S% + Wind x W% + Storage x B% "
                    "(Architecture contracted mix). Annual energy bill = Energy Cost x load kWh."
                ),
                styles["Muted"],
            )
        )

        story.append(_section_title(f"   {arch.title()} - Hourly CFE & compliance", styles))
        cfe_tbl = [
            ["Metric", "Value"],
            ["Hourly CFE target", _pct(s.get("cfe_target") or cfe_t, 0)],
            ["Min hourly CFE %", _pct(s.get("cfe_min"))],
            ["Mean hourly CFE %", _pct(s.get("cfe_mean"))],
            ["Hours >= target %", _pct(s.get("hours_meet"))],
            ["Hourly CFE status", str(s.get("cfe_status") or "—")],
            ["Annual RE % (dispatch diagnostic)", _pct(s.get("annual_re"))],
            ["Annual RE status", str(s.get("re_status") or "—")],
        ]
        story.append(_styled_table(cfe_tbl, col_widths=[200, 260]))
        story.append(
            Paragraph(
                _safe_text(
                    "Pass = min hourly CFE >= target and 100% of hours meet the target. "
                    "Hourly CFE% = Min(Load, Solar+Wind+RE-origin BESS) / Load x 100 "
                    "(TOD availability; solar ~0 at night). "
                    "Bill uses contracted mix %; CFE uses availability."
                ),
                styles["Muted"],
            )
        )

    # —— Methodology ——
    story.append(_section_title(f"{sec_n}. Methodology (commercial buyer)", styles))
    sec_n += 1
    bullets = [
        "Energy Cost Rs/kWh = blended rate (Captive/Hybrid) or DISCOM stack rate.",
        "Annual energy bill = Energy Cost x annual load kWh (demand / fixed / compliance shown separately).",
        "Blended = Discom x G% + Solar x S% + Wind x W% + Storage tariff x B% from Architecture mix.",
        "Savings vs DISCOM = 100% DISCOM energy bill - architecture energy bill (Year 1).",
        "NPV of savings = present value of yearly bill savings over project life at the financial discount rate (no plant CAPEX at Year 0).",
        "BESS on Captive/Hybrid = Storage tariff Rs/kWh only (no plant MW/MWh).",
    ]
    for b in bullets:
        story.append(Paragraph(_safe_text(f"- {b}"), styles["Body"]))

    story.append(_section_title(f"{sec_n}. Disclaimer", styles))
    story.append(Paragraph(_safe_text(DISCLAIMER), styles["FootNote"]))
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            _safe_text(
                "Assumptions register and full methodology are available in the application. "
                "This PDF is a point-in-time export of the latest Run Analysis results."
            ),
            styles["Muted"],
        )
    )

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=48,
        bottomMargin=52,
        title=f"Data Center PowerTrain - {name}",
        author="Avaada Data Center PowerTrain",
    )
    doc.build(story, onFirstPage=_draw_page_chrome, onLaterPages=_draw_page_chrome)
    return out

