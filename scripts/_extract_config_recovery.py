# -*- coding: utf-8 -*-
"""Extract largest recent config.py Write/StrReplace payloads from transcript."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "_config_recovery"
TRANSCRIPT = Path(
    r"C:\Users\5863.AVAADA\.cursor\projects\d-Sachin-Python-PowerTrainOptimizer"
    r"\agent-transcripts\f33339ce-8789-4df6-a168-c1e85622279b"
    r"\f33339ce-8789-4df6-a168-c1e85622279b.jsonl"
)

OUT.mkdir(exist_ok=True)


def main() -> None:
    lines = TRANSCRIPT.read_text(encoding="utf-8").splitlines()
    candidates: list[tuple[int, int, str, str]] = []
    for i, line in enumerate(lines):
        if "config.py" not in line or "new_string" not in line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        for part in obj.get("message", {}).get("content", []):
            if part.get("type") != "tool_use":
                continue
            inp = part.get("input") or {}
            path = str(inp.get("path") or "")
            if "config.py" not in path.replace("\\", "/"):
                continue
            ns = inp.get("new_string") or ""
            if len(ns) < 200:
                continue
            name = part.get("name") or ""
            candidates.append((len(ns), i, name, ns))

    summary = []
    for rank, (ln, i, name, ns) in enumerate(candidates[:40]):
        fn = OUT / f"cand_{rank:02d}_line{i}_len{ln}.txt"
        fn.write_text(ns, encoding="utf-8")
        head = ns[:80].replace("\n", " | ")
        summary.append(f"{rank:02d} line={i} len={ln} tool={name} head={head}")
    (OUT / "summary.txt").write_text("\n".join(summary), encoding="utf-8")
    print(f"wrote {min(40, len(candidates))} candidates + summary")

    # Also find if any Write wrote the whole file
    for i, line in enumerate(lines):
        if '"Write"' not in line or "config.py" not in line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        for part in obj.get("message", {}).get("content", []):
            if part.get("type") != "tool_use" or part.get("name") != "Write":
                continue
            inp = part.get("input") or {}
            if "config.py" not in str(inp.get("path") or ""):
                continue
            contents = inp.get("contents") or ""
            if contents:
                (OUT / f"write_line{i}.py").write_text(contents, encoding="utf-8")
                print("WRITE", i, len(contents))


if __name__ == "__main__":
    main()
