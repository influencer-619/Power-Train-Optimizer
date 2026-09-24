"""Proper-ish JS brace balance for diagnosing syntax errors."""
from pathlib import Path

js = Path("frontend/dist/assets/app.js").read_text(encoding="utf-8")

depth = 0
line = 1
stack = []
i = 0
n = len(js)
# mode stack: "code" | "squote" | "dquote" | "template" | "linecomment" | "blockcomment" | "regex"
modes = ["code"]
# For templates: when inside ${}, we push "code" on modes; closing } that matches ${ pops back
# Track brace depth at entry to each ${ expression
tpl_expr_depths = []  # depth values when ${ was entered
escape = False

def cur():
    return modes[-1]

def push_brace():
    global depth
    depth += 1
    stack.append(line)

def pop_brace():
    global depth
    depth -= 1
    if stack:
        stack.pop()
    if depth < 0:
        print(f"extra }} at line {line}")
        print(repr(js[max(0, i-60):i+40]))
        raise SystemExit(1)
    # Closing a template expression ${ ... }
    if tpl_expr_depths and depth == tpl_expr_depths[-1]:
        tpl_expr_depths.pop()
        if modes and modes[-1] == "code" and len(modes) > 1:
            modes.pop()  # leave expression code, back to template

while i < n:
    ch = js[i]
    nxt = js[i + 1] if i + 1 < n else ""
    mode = cur()

    if mode == "linecomment":
        if ch == "\n":
            modes.pop()
            line += 1
        i += 1
        continue

    if mode == "blockcomment":
        if ch == "*" and nxt == "/":
            modes.pop()
            i += 2
            continue
        if ch == "\n":
            line += 1
        i += 1
        continue

    if mode in ("squote", "dquote"):
        if escape:
            escape = False
        elif ch == "\\":
            escape = True
        elif (mode == "squote" and ch == "'") or (mode == "dquote" and ch == '"'):
            modes.pop()
        elif ch == "\n":
            line += 1
        i += 1
        continue

    if mode == "regex":
        if escape:
            escape = False
        elif ch == "\\":
            escape = True
        elif ch == "[":
            i += 1
            while i < n:
                c = js[i]
                if c == "\\" and i + 1 < n:
                    i += 2
                    continue
                if c == "]":
                    break
                if c == "\n":
                    line += 1
                i += 1
        elif ch == "/":
            i += 1
            while i < n and js[i].isalpha():
                i += 1
            modes.pop()
            continue
        elif ch == "\n":
            line += 1
        i += 1
        continue

    if mode == "template":
        if escape:
            escape = False
            i += 1
            continue
        if ch == "\\":
            escape = True
            i += 1
            continue
        if ch == "`":
            modes.pop()
            i += 1
            continue
        if ch == "$" and nxt == "{":
            push_brace()
            tpl_expr_depths.append(depth - 1)  # depth before the { of ${
            # wait: push_brace already incremented for `{` of ${
            # We want when depth returns to value before ${'s brace, i.e. depth-1 after push = old depth
            # Actually: before ${, depth=D. We push for `{`, depth=D+1. Expression closes when depth back to D.
            tpl_expr_depths[-1] = depth - 1  # close when depth == D
            modes.append("code")
            i += 2
            continue
        if ch == "\n":
            line += 1
        i += 1
        continue

    # code
    if ch == "'":
        modes.append("squote")
        i += 1
        continue
    if ch == '"':
        modes.append("dquote")
        i += 1
        continue
    if ch == "`":
        modes.append("template")
        i += 1
        continue
    if ch == "/" and nxt == "/":
        modes.append("linecomment")
        i += 2
        continue
    if ch == "/" and nxt == "*":
        modes.append("blockcomment")
        i += 2
        continue
    if ch == "/":
        j = i - 1
        while j >= 0 and js[j] in " \t\r\n":
            j -= 1
        prev = js[j] if j >= 0 else ""
        is_re = prev in "=([{,;!&|?:~+-*%^<>" 
        if not is_re and j >= 0:
            k = j
            while k >= 0 and (js[k].isalnum() or js[k] == "_"):
                k -= 1
            word = js[k + 1 : j + 1]
            if word in ("return", "throw", "case", "in", "of", "typeof", "void", "delete", "new", "instanceof", "else"):
                is_re = True
        if is_re:
            modes.append("regex")
            i += 1
            continue

    if ch == "{":
        push_brace()
    elif ch == "}":
        pop_brace()
    if ch == "\n":
        line += 1
    i += 1

print("final depth", depth, "modes", modes)
if depth != 0:
    print("unclosed opens at lines", stack[-15:])
    lines = js.splitlines()
    for last in stack[-5:]:
        print(f"\n--- opened at {last} ---")
        for ln in range(max(0, last - 2), min(len(lines), last + 4)):
            print(f"{ln+1}: {lines[ln][:140]}")
