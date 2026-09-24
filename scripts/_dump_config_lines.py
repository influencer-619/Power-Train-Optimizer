# -*- coding: utf-8 -*-
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


def dump_line(idx: int) -> None:
    lines = TRANSCRIPT.read_text(encoding="utf-8").splitlines()
    obj = json.loads(lines[idx])
    n = 0
    for part in obj.get("message", {}).get("content", []):
        if part.get("type") != "tool_use":
            continue
        inp = part.get("input") or {}
        path = str(inp.get("path") or "")
        if "config.py" not in path:
            continue
        ns = inp.get("new_string") or ""
        os_ = inp.get("old_string") or ""
        (OUT / f"L{idx}_{n}_new.txt").write_text(ns, encoding="utf-8")
        (OUT / f"L{idx}_{n}_old.txt").write_text(os_, encoding="utf-8")
        n += 1
    (OUT / f"L{idx}_meta.txt").write_text(f"n={n}\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for idx in (836, 1016, 1125, 1182, 1317, 1446, 1550, 1614, 1627, 1631, 1633, 1634):
        try:
            dump_line(idx)
        except Exception as e:
            (OUT / f"L{idx}_err.txt").write_text(str(e), encoding="utf-8")
    # Find largest new_string containing it_load_mw AND load_factor_s1
    best = (0, -1, "")
    for i, line in enumerate(TRANSCRIPT.read_text(encoding="utf-8").splitlines()):
        if "it_load_mw" not in line or "load_factor_s1" not in line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        for part in obj.get("message", {}).get("content", []):
            ns = (part.get("input") or {}).get("new_string") or ""
            if "it_load_mw" in ns and "load_factor_s1" in ns and len(ns) > best[0]:
                best = (len(ns), i, ns)
    if best[2]:
        (OUT / "best_load_block.txt").write_text(best[2], encoding="utf-8")
    (OUT / "best_meta.txt").write_text(f"len={best[0]} line={best[1]}\n", encoding="utf-8")

    # largest recompute with SCENARIO
    best2 = (0, -1, "")
    for i, line in enumerate(TRANSCRIPT.read_text(encoding="utf-8").splitlines()):
        if "SCENARIO" not in line or "recompute_calculated" not in line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        for part in obj.get("message", {}).get("content", []):
            ns = (part.get("input") or {}).get("new_string") or ""
            if "SCENARIO" in ns and ("load_factor" in ns) and len(ns) > best2[0]:
                best2 = (len(ns), i, ns)
    if best2[2]:
        (OUT / "best_scenario_block.txt").write_text(best2[2], encoding="utf-8")
    (OUT / "best2_meta.txt").write_text(f"len={best2[0]} line={best2[1]}\n", encoding="utf-8")


if __name__ == "__main__":
    main()
