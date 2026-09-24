# -*- coding: utf-8 -*-
"""Replace export_pdf() body in excel_pdf.py with polished version."""
from pathlib import Path

NEW = r'''
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
    story.append(Paragraph("PowerTrain Optimizer", styles["CoverTitle"]))
    story.append(Paragraph("Data Centre Power Economics Report", styles["CoverSub"]))
    story.append(
        Paragraph(
            _safe_text("Captive & Hybrid procurement - Tariff / PPA stacks - CFE & carbon"),
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
        title=f"PowerTrain - {name}",
        author="Avaada PowerTrain Optimizer",
    )
    doc.build(story, onFirstPage=_draw_page_chrome, onLaterPages=_draw_page_chrome)
    return out
'''

path = Path("backend/reports/excel_pdf.py")
t = path.read_text(encoding="utf-8")
start = t.find("def export_pdf(")
if start < 0:
    raise SystemExit("export_pdf not found")
# keep trailing newline at EOF
path.write_text(t[:start].rstrip() + "\n\n" + NEW.lstrip() + "\n", encoding="utf-8")
print("OK replaced export_pdf")

# Also fix excel sheet "Power cost" labels quickly
t = path.read_text(encoding="utf-8")
t = t.replace('Power cost (₹/kWh)', 'Energy Cost (Rs/kWh)')
t = t.replace('Power cost ₹/kWh', 'Energy Cost Rs/kWh')
t = t.replace('["Power cost (₹/kWh)"', '["Energy Cost (Rs/kWh)"')
t = t.replace('["Power cost (₹/kWh)", s.get("power_cost")]', '["Energy Cost (Rs/kWh)", s.get("energy_cost", s.get("power_cost"))]')
# remaining Power cost in excel section
t = t.replace('"Power cost (₹/kWh)"', '"Energy Cost (Rs/kWh)"')
t = t.replace("₹/kWh", "Rs/kWh")
t = t.replace("(₹ Cr)", "(Rs Cr)")
t = t.replace("(₹)", "(Rs)")
path.write_text(t, encoding="utf-8")
print("OK excel label cleanup")
