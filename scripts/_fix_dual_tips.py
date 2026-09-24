# -*- coding: utf-8 -*-
"""Remove native title= when data-tip is present so only the floating tip shows."""
from pathlib import Path
import re

app = Path("frontend/dist/assets/app.js")
t = app.read_text(encoding="utf-8")

# kpiCard: only data-tip
t2 = t.replace(
    '  const tipAttr = tip\n    ? ` data-tip="${escHtml(tip)}" title="${escHtml(tip)}"`\n    : "";',
    '  const tipAttr = tip\n    ? ` data-tip="${escHtml(tip)}"`\n    : "";',
)
if t2 == t:
    print("WARN kpi tipAttr pattern missed")
else:
    t = t2
    print("OK kpi tipAttr")

# data-tip=... title=...  (same tip duplicated)
pat1 = re.compile(
    r'(data-tip="\$\{escHtml\(([^)]+)\)\}")\s+title="\$\{escHtml\(\2\)\}"'
)
t, n1 = pat1.subn(r"\1", t)
print("OK strip title after data-tip escHtml same arg:", n1)

# title=... data-tip=... (reverse order, same tip)
pat2 = re.compile(
    r'title="\$\{escHtml\(([^)]+)\)\}"\s+(data-tip="\$\{escHtml\(\1\)\}")'
)
t, n2 = pat2.subn(r"\2", t)
print("OK strip title before data-tip:", n2)

# Literal string tips: data-tip="${escHtml("...")}" title="${escHtml("...")}"
pat3 = re.compile(
    r'(data-tip="\$\{escHtml\("((?:\\.|[^"\\])*)"\)\}")\s+title="\$\{escHtml\("\2"\)\}"'
)
t, n3 = pat3.subn(r"\1", t)
print("OK strip literal title dup:", n3)

# Broader: any title= right after data-tip= in template attrs (same line-ish)
# data-tip="..." title="..." where both are ${escHtml(...)} possibly different
pat4 = re.compile(
    r'(data-tip="(?:\\"|[^"])*")\s+title="(?:\\"|[^"])*"'
)
t, n4 = pat4.subn(r"\1", t)
print("OK strip any title after data-tip:", n4)

pat5 = re.compile(
    r'title="(?:\\"|[^"])*"\s+(data-tip="(?:\\"|[^"])*")'
)
t, n5 = pat5.subn(r"\1", t)
print("OK strip any title before data-tip:", n5)

# Defensive: when showing floating tip, clear native title so browser never shows white tip
old = '''    const place = (el, clientX, clientY) => {
      const text = el.getAttribute("data-tip");
      if (!text) return;
      tip.textContent = text;
      tip.classList.add("show");'''
new = '''    const place = (el, clientX, clientY) => {
      const text = el.getAttribute("data-tip");
      if (!text) return;
      // Native title= duplicates the floating tip (white browser bubble) — suppress it.
      if (el.hasAttribute("title")) {
        if (!el.getAttribute("data-title-bak")) el.setAttribute("data-title-bak", el.getAttribute("title") || "");
        el.removeAttribute("title");
      }
      tip.textContent = text;
      tip.classList.add("show");'''
if old in t:
    t = t.replace(old, new, 1)
    print("OK suppress title on hover")
else:
    print("WARN place() block missed")

app.write_text(t, encoding="utf-8")

# charts.js: SVG <title> also shows white native tooltips; keep if no floating tip on parent.
# Legend uses data-tip + title often — strip title next to data-tip there too.
ch = Path("frontend/dist/assets/charts.js")
c = ch.read_text(encoding="utf-8")
c2, nc = re.subn(
    r'(data-tip="\$\{[^}]+\}")\s+title="\$\{[^}]+\}"',
    r"\1",
    c,
)
c2, nc2 = re.subn(
    r'title="\$\{[^}]+\}"\s+(data-tip="\$\{[^}]+\}")',
    r"\1",
    c2,
)
# Also: title="${esc(tip)}" data-tip="${esc(tip)}"
c2, nc3 = re.subn(
    r'(?:title="\$\{esc\([^)]+\)\}"\s+)?(data-tip="\$\{esc\([^)]+\)\}")(?:\s+title="\$\{esc\([^)]+\)\}")?',
    r"\1",
    c2,
)
if c2 != c:
    ch.write_text(c2, encoding="utf-8")
    print(f"OK charts strip title n={nc}+{nc2}+{nc3}")
else:
    print("charts unchanged")

idx = Path("frontend/dist/index.html")
h = idx.read_text(encoding="utf-8")
h = re.sub(r"app\.js\?v=\d+", "app.js?v=154", h)
h = re.sub(r"charts\.js\?v=\d+", "charts.js?v=154", h)
h = re.sub(r"styles\.css\?v=\d+", "styles.css?v=154", h)
idx.write_text(h, encoding="utf-8")
print("v154")

# verify remaining dual
t = app.read_text(encoding="utf-8")
left = len(re.findall(r'data-tip="[^"]*"\s+title="', t))
left2 = len(re.findall(r'title="[^"]*"\s+data-tip="', t))
print("remaining dual", left, left2)
