from pathlib import Path
import re

p = Path("frontend/dist/assets/app.js")
t = p.read_text(encoding="utf-8")
idx = t.find("Lowest hour of Min(Load, Solar+Wind+CF-BESS)")
print("idx", idx)
if idx >= 0:
    frag = t[idx : idx + 90]
    print([hex(ord(c)) for c in frag])
    print(repr(frag))

new, n = re.subn(
    r'tip: "Lowest hour of Min\(Load, Solar\+Wind\+CF-BESS\)/Load .{1,3} 100\."',
    'tip: "Architecture Solar%+Wind%+BESS% (firm every hour)."',
    t,
)
print("replacements", n)
p.write_text(new, encoding="utf-8")

html = Path("frontend/dist/index.html")
h = html.read_text(encoding="utf-8")
for old in ("?v=137", "?v=136", "?v=135"):
    h = h.replace(old, "?v=138")
html.write_text(h, encoding="utf-8")
print("cache", "?v=138" in h)
