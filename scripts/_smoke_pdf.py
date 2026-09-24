# -*- coding: utf-8 -*-
import importlib
import sys
import types
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

# Stub DB-heavy imports (SQLAlchemy 2 + Python 3.14 typing issue in this env).
for name in [
    "backend.services.project_service",
    "backend.services.run_service",
    "backend.database",
    "backend.database.init_db",
    "backend.database.session",
    "backend.models",
    "backend.models.db_models",
]:
    sys.modules.setdefault(name, types.ModuleType(name))

sys.modules["backend.services.project_service"].get_project = lambda *a, **k: {}
sys.modules["backend.services.run_service"].get_simulation = lambda *a, **k: {}
sys.modules["backend.services.run_service"].compare_architectures = lambda *a, **k: {}

# Force reload excel_pdf against stubs
sys.modules.pop("backend.reports.excel_pdf", None)
sys.modules.pop("backend.reports", None)
ep = importlib.import_module("backend.reports.excel_pdf")

print("font", ep._PDF_FONT)
print(ep._fmt_inr_kwh(5.3075), ep._fmt_cr(955.35))

out = Path("data/exports/_pdf_smoke_check.pdf")
out.parent.mkdir(parents=True, exist_ok=True)
styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle("Body", parent=styles["Normal"], fontName=ep._PDF_FONT, fontSize=9, textColor=ep._NAVY)
)
story = [
    Paragraph(
        "PowerTrain Optimizer",
        ParagraphStyle("T", fontName=ep._PDF_FONT_BOLD, fontSize=16, textColor=ep._NAVY),
    ),
    Spacer(1, 8),
    ep._styled_table(
        [
            ["Metric", "HYBRID"],
            ["Energy Cost", ep._fmt_inr_kwh(5.3075)],
            ["Annual energy bill", ep._fmt_cr(955.35)],
            ["Annual load", f"{ep._fmt_num(1800000, 2)} MWh"],
            ["Carbon saved", f"{ep._fmt_num(700000, 0)} tCO2"],
        ],
        col_widths=[180, 280],
    ),
    Spacer(1, 8),
    Paragraph(ep._safe_text("Buyer viewpoint: fixed Rs/kWh. tCO2 OK."), styles["Body"]),
]
doc = SimpleDocTemplate(
    str(out), pagesize=A4, leftMargin=36, rightMargin=36, topMargin=48, bottomMargin=52
)
doc.build(story, onFirstPage=ep._draw_page_chrome, onLaterPages=ep._draw_page_chrome)
txt = PdfReader(str(out)).pages[0].extract_text()
print(txt)
assert "Rs" in txt and "Energy Cost" in txt and "tCO2" in txt
assert "■" not in txt
print("SMOKE OK")
