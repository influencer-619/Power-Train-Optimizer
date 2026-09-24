# -*- coding: utf-8 -*-
"""Replace SVG <title> tooltips with data-tip (floating tip only; no white native tip)."""
from pathlib import Path
import re

p = Path("frontend/dist/assets/charts.js")
c = p.read_text(encoding="utf-8")

pat = re.compile(
    r"(<(?:path|rect|circle)\b[^>]*?)>\s*<title>\$\{esc\(([^)]+)\)\}</title></(path|rect|circle)>",
    re.S,
)


def fix(m):
    open_tag, expr, tag = m.group(1), m.group(2), m.group(3)
    if "data-tip=" not in open_tag:
        open_tag = open_tag + f' data-tip="${{esc({expr})}}"'
    return f"{open_tag}></{tag}>"


c2, n = pat.subn(fix, c)
print("replaced", n)

# leftover static titles like -20% / +20% — leave or convert; convert to data-tip
pat2 = re.compile(
    r'(<(?:path|rect|circle)\b[^>]*?)>\s*<title>([^<]+)</title></(path|rect|circle)>',
    re.S,
)


def fix2(m):
    open_tag, text, tag = m.group(1), m.group(2), m.group(3)
    if "data-tip=" not in open_tag:
        # escape quotes in static text for attribute
        safe = text.replace('"', "&quot;")
        open_tag = open_tag + f' data-tip="{safe}"'
    return f"{open_tag}></{tag}>"


c2, n2 = pat2.subn(fix2, c2)
print("static title replaced", n2)
print("remaining <title>", c2.count("<title>"))
p.write_text(c2, encoding="utf-8")

idx = Path("frontend/dist/index.html")
h = idx.read_text(encoding="utf-8")
h = re.sub(r"app\.js\?v=\d+", "app.js?v=154", h)
h = re.sub(r"charts\.js\?v=\d+", "charts.js?v=154", h)
h = re.sub(r"styles\.css\?v=\d+", "styles.css?v=154", h)
idx.write_text(h, encoding="utf-8")
print("v154")
