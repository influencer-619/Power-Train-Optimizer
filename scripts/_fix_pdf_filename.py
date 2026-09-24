from pathlib import Path

p = Path("frontend/dist/assets/app.js")
text = p.read_text(encoding="utf-8")
needle = 'a.download = (res.headers.get("content-disposition") || "file").split("filename=").pop() || "export";'
if needle not in text:
    raise SystemExit("needle not found")

# Replace the whole reports dl block by locating markers
start = text.find('  if (state.page === "reports") {')
end = text.find('    document.getElementById("btn-backup")', start)
if start < 0 or end < 0:
    raise SystemExit(f"markers missing start={start} end={end}")

new_block = r'''  if (state.page === "reports") {
    const filenameFromDisposition = (header, fallback) => {
      const raw = header || "";
      const star = /filename\*\s*=\s*UTF-8''([^;]+)/i.exec(raw);
      if (star) {
        try {
          return decodeURIComponent(star[1].trim().replace(/^["']|["']$/g, ""));
        } catch (_) { /* fall through */ }
      }
      const plain = /filename\s*=\s*"([^"]+)"|filename\s*=\s*([^;]+)/i.exec(raw);
      let name = plain ? (plain[1] || plain[2] || "") : "";
      name = String(name || fallback || "export").trim().replace(/^["']+|["']+$/g, "");
      // Quotes in Content-Disposition were kept and Windows/browser turned " into _
      name = name.replace(/^_+|_+$/g, "");
      return name || fallback || "export";
    };
    const dl = async (path, body, fallbackName) => {
      const res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (!res.ok) {
        const payload = await readResponsePayload(res);
        throw new Error(errorMessageFromPayload(payload, res.statusText || "Export failed"));
      }
      const blob = await res.blob();
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filenameFromDisposition(res.headers.get("content-disposition"), fallbackName);
      a.click();
      URL.revokeObjectURL(a.href);
    };
    document.getElementById("btn-xlsx").onclick = () =>
      dl("/api/reports/excel", { project_id: state.project.id, simulation_id: state.lastSim?.id }, `PowerTrain_Project${state.project.id}.xlsx`)
        .catch((e) => alert(e.message || String(e)));
    document.getElementById("btn-pdf").onclick = () =>
      dl("/api/reports/pdf", { project_id: state.project.id, simulation_id: state.lastSim?.id }, `PowerTrain_Project${state.project.id}.pdf`)
        .catch((e) => alert(e.message || String(e)));
  }
'''

text = text[:start] + new_block + text[end:]
p.write_text(text, encoding="utf-8")
print("patched ok")
