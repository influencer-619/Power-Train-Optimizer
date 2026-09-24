# -*- coding: utf-8 -*-
from pathlib import Path
import re

app = Path("frontend/dist/assets/app.js")
t = app.read_text(encoding="utf-8")

if "setupFloatingTips" in t:
    print("already hooked")
else:
    needle = '  window.addEventListener("beforeunload", signalCloseTab);\n})();'
    insert = r'''  window.addEventListener("beforeunload", signalCloseTab);

  // Floating formula tips (position:fixed — not clipped by .table-wrap overflow)
  (function setupFloatingTips() {
    let tip = document.getElementById("pto-float-tip");
    if (!tip) {
      tip = document.createElement("div");
      tip.id = "pto-float-tip";
      tip.setAttribute("role", "tooltip");
      document.body.appendChild(tip);
    }
    let active = null;
    const place = (el, clientX, clientY) => {
      const text = el.getAttribute("data-tip");
      if (!text) return;
      tip.textContent = text;
      tip.classList.add("show");
      const pad = 10;
      tip.style.left = "0px";
      tip.style.top = "0px";
      const tw = tip.offsetWidth || 240;
      const th = tip.offsetHeight || 60;
      let x = clientX + 14;
      let y = clientY + 18;
      if (x + tw > window.innerWidth - pad) x = clientX - tw - 12;
      if (y + th > window.innerHeight - pad) y = clientY - th - 14;
      if (x < pad) x = pad;
      if (y < pad) y = pad;
      tip.style.left = x + "px";
      tip.style.top = y + "px";
    };
    const hide = () => {
      active = null;
      tip.classList.remove("show");
    };
    document.addEventListener("pointerover", (e) => {
      const el = e.target && e.target.closest ? e.target.closest("[data-tip]") : null;
      if (!el) return;
      active = el;
      place(el, e.clientX, e.clientY);
    }, true);
    document.addEventListener("pointermove", (e) => {
      if (!active) return;
      const el = e.target && e.target.closest ? e.target.closest("[data-tip]") : null;
      if (el !== active) return;
      place(active, e.clientX, e.clientY);
    }, true);
    document.addEventListener("pointerout", (e) => {
      if (!active) return;
      const to = e.relatedTarget;
      if (to && active.contains(to)) return;
      if (e.target && active.contains(e.target) && (!to || !active.contains(to))) hide();
    }, true);
    document.addEventListener("scroll", hide, true);
  })();
})();'''
    if needle not in t:
        raise SystemExit("needle not found")
    app.write_text(t.replace(needle, insert, 1), encoding="utf-8")
    print("app.js tip hook OK")

idx = Path("frontend/dist/index.html")
h = idx.read_text(encoding="utf-8")
h = re.sub(r"styles\.css\?v=\d+", "styles.css?v=146", h)
h = re.sub(r"charts\.js\?v=\d+", "charts.js?v=146", h)
h = re.sub(r"app\.js\?v=\d+", "app.js?v=146", h)
idx.write_text(h, encoding="utf-8")
print("index v=146")
