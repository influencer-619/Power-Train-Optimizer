# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("frontend/dist/assets/app.js")
t = p.read_text(encoding="utf-8")
i = t.find("function pageEconomics()")
j = t.find("function pageReports()")
chunk = t[i:j]
print("m count before", chunk.count("const m = lfMetrics(s);"))

# Keep first m (after if !f), remove the one immediately before return
old = """    : \"\";
  const m = lfMetrics(s);
  return `
  ${compareBlock}
  ${architectureTabsHtml(\"economics\")}
  ${lfScenarioPickerHtml(s)}"""
new = """    : \"\";
  return `
  ${compareBlock}
  ${architectureTabsHtml(\"economics\")}
  ${lfScenarioPickerHtml(s)}"""

if old not in chunk:
    raise SystemExit("dup block not found in pageEconomics")
chunk2 = chunk.replace(old, new, 1)
print("m count after", chunk2.count("const m = lfMetrics(s);"))
t = t[:i] + chunk2 + t[j:]
p.write_text(t, encoding="utf-8")
print("OK")
