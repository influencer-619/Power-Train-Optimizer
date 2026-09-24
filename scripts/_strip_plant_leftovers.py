"""One-shot: remove plant leftover keys from DEFAULT_CONFIG and strengthen strip-on-load."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "config" / "defaults" / "config.py"
text = path.read_text(encoding="utf-8")

# --- Remove whole sections from DEFAULT_CONFIG ---
for section in ("bess", "optimization"):
    # Match section dict at DEFAULT_CONFIG indentation
    pat = rf'\n    "{section}": \{{(?:[^{{}}]|\{{\{{(?:[^{{}}]|\{{\{{[^{{}}]*\}}\}})*\}}\}})*\n    \}},'
    m = re.search(pat, text)
    if not m:
        # fallback: non-greedy until next top-level key or closing
        pat2 = rf'\n    "{section}": \{{.*?\n    \}},'
        m = re.search(pat2, text, flags=re.S)
    if m:
        text = text[: m.start()] + text[m.end() :]
        print(f"removed section {section}")
    else:
        print(f"WARN: section {section} not found")

# --- Remove specific keys inside solar / wind / grid / financial ---
KEY_REMOVALS = {
    "solar": [
        "capacity_mw",
        "degradation_pct",
        "project_life_yr",
        "capex_inr_per_mw",
        "opex_inr_per_mw_year",
        "energy_cost_inr_per_kwh",
    ],
    "wind": [
        "capacity_mw",
        "degradation_pct",
        "project_life_yr",
        "capex_inr_per_mw",
        "opex_inr_per_mw_year",
        "energy_cost_inr_per_kwh",
    ],
    "grid": ["max_import_mw"],
    "financial": [
        "inflation_pct",
        "residual_value_pct",
        "financing_enabled",
        "debt_pct",
        "interest_rate_pct",
        "debt_tenor_yr",
    ],
}


def remove_key_block(src: str, section: str, key: str) -> str:
    # Find section start
    sec = re.search(rf'\n    "{section}": \{{', src)
    if not sec:
        print(f"WARN: section {section} missing for key {key}")
        return src
    # Find next sibling section or end of DEFAULT_CONFIG
    nxt = re.search(r'\n    "[a-z_]+": \{', src[sec.end() :])
    end = sec.end() + (nxt.start() if nxt else len(src) - sec.end())
    block = src[sec.start() : end]
    # Remove key P(...) entry — from "key": P( to matching ),
    # Use brace/paren depth walk from key
    marker = f'"{key}": P('
    idx = block.find(marker)
    if idx < 0:
        print(f"skip missing {section}.{key}")
        return src
    # include leading whitespace/newline
    start = idx
    while start > 0 and block[start - 1] in " \t":
        start -= 1
    if start > 0 and block[start - 1] == "\n":
        start -= 1
    i = idx + len(marker)
    depth_p = 1
    depth_b = 0
    while i < len(block) and depth_p > 0:
        ch = block[i]
        if ch == "(":
            depth_p += 1
        elif ch == ")":
            depth_p -= 1
        elif ch == "{":
            depth_b += 1
        elif ch == "}":
            depth_b -= 1
        i += 1
    # consume trailing comma
    while i < len(block) and block[i] in " \t":
        i += 1
    if i < len(block) and block[i] == ",":
        i += 1
    new_block = block[:start] + block[i:]
    print(f"removed {section}.{key}")
    return src[: sec.start()] + new_block + src[end:]


for section, keys in KEY_REMOVALS.items():
    for key in keys:
        text = remove_key_block(text, section, key)

# --- Replace obsolete strip logic with comprehensive retire list ---
old_obs = '''_OBSOLETE_BESS_KEYS = (
    "charge_efficiency_pct",
    "discharge_efficiency_pct",
    "round_trip_efficiency_pct",
    "max_charge_mw",
    "max_discharge_mw",
)'''

new_obs = '''# Plant / owner leftovers — removed from buyer config (strip on load for old .pto.zip).
RETIRED_SECTIONS = ("bess", "optimization", "scenarios")

RETIRED_KEYS: dict[str, tuple[str, ...]] = {
    "solar": (
        "capacity_mw",
        "degradation_pct",
        "project_life_yr",
        "capex_inr_per_mw",
        "opex_inr_per_mw_year",
        "energy_cost_inr_per_kwh",
    ),
    "wind": (
        "capacity_mw",
        "degradation_pct",
        "project_life_yr",
        "capex_inr_per_mw",
        "opex_inr_per_mw_year",
        "energy_cost_inr_per_kwh",
    ),
    "grid": ("max_import_mw",),
    "financial": (
        "inflation_pct",
        "residual_value_pct",
        "financing_enabled",
        "debt_pct",
        "interest_rate_pct",
        "debt_tenor_yr",
    ),
    "bess": (),  # whole section retired
}

_OBSOLETE_BESS_KEYS = (
    "charge_efficiency_pct",
    "discharge_efficiency_pct",
    "round_trip_efficiency_pct",
    "max_charge_mw",
    "max_discharge_mw",
    "power_mw",
    "energy_mwh",
    "initial_soc_pct",
    "min_soc_pct",
    "max_soc_pct",
    "calendar_degradation_pct",
    "cycle_degradation_pct",
    "capex_inr_per_mw",
    "capex_inr_per_mwh",
    "opex_inr_per_year",
    "project_life_yr",
    "replacement_year",
    "replacement_cost_pct",
    "allow_grid_charge",
)


def strip_plant_leftovers(config: dict) -> dict:
    """Delete generation-plant leftovers from config (buyer = contracted energy only)."""
    for section in RETIRED_SECTIONS:
        config.pop(section, None)
    for section, keys in RETIRED_KEYS.items():
        sec = config.get(section)
        if not isinstance(sec, dict):
            continue
        for key in keys:
            sec.pop(key, None)
        if section == "bess":
            config.pop("bess", None)
    bess = config.get("bess")
    if isinstance(bess, dict):
        for key in _OBSOLETE_BESS_KEYS:
            bess.pop(key, None)
        if not bess:
            config.pop("bess", None)
    return config'''

if old_obs in text:
    text = text.replace(old_obs, new_obs)
    print("replaced obsolete keys block")
else:
    print("WARN: obsolete block not found for replace")

# Patch merge_missing_defaults to call strip_plant_leftovers
old_merge_snip = '''    # Drop retired BESS fields so they no longer appear in Setup / Assumptions
    bess = config.get("bess")
    if isinstance(bess, dict):
        for key in _OBSOLETE_BESS_KEYS:
            bess.pop(key, None)
    for section in ("compliance", "optimization"):
        sec = config.get(section)
        if isinstance(sec, dict):
            sec.pop("enforce_cfe_target", None)
    commercial = config.get("commercial")
    if isinstance(commercial, dict):
        commercial.pop("include_generation_capex", None)
    load = config.get("load")
    if isinstance(load, dict):
        load.pop("growth_rate_pct", None)'''

new_merge_snip = '''    strip_plant_leftovers(config)
    for section in ("compliance", "optimization"):
        sec = config.get(section)
        if isinstance(sec, dict):
            sec.pop("enforce_cfe_target", None)
    commercial = config.get("commercial")
    if isinstance(commercial, dict):
        commercial.pop("include_generation_capex", None)
    load = config.get("load")
    if isinstance(load, dict):
        load.pop("growth_rate_pct", None)'''

if old_merge_snip in text:
    text = text.replace(old_merge_snip, new_merge_snip)
    print("patched merge_missing_defaults")
else:
    print("WARN: merge snip not found")

# Simplify PLANT_LEFTOVER to safety net for any stray keys
old_plant = '''# Generation-plant leftovers — hidden from Assumptions (DC = energy consumer at fixed rates).
PLANT_LEFTOVER_PATHS = frozenset(
    {
        "solar.capacity_mw",
        "solar.capex_inr_per_mw",
        "solar.opex_inr_per_mw_year",
        "solar.project_life_yr",
        "solar.energy_cost_inr_per_kwh",
        "wind.capacity_mw",
        "wind.capex_inr_per_mw",
        "wind.opex_inr_per_mw_year",
        "wind.project_life_yr",
        "wind.energy_cost_inr_per_kwh",
        "bess.power_mw",
        "bess.energy_mwh",
        "bess.capex_inr_per_mw",
        "bess.capex_inr_per_mwh",
        "bess.opex_inr_per_year",
        "bess.replacement_year",
        "bess.replacement_cost_pct",
        "bess.project_life_yr",
        "bess.initial_soc_pct",
        "bess.min_soc_pct",
        "bess.max_soc_pct",
        "bess.calendar_degradation_pct",
        "bess.cycle_degradation_pct",
        "bess.allow_grid_charge",
        "grid.max_import_mw",
        "financial.financing_enabled",
        "financial.debt_pct",
        "financial.interest_rate_pct",
        "financial.debt_tenor_yr",
        "financial.residual_value_pct",
        "financial.inflation_pct",
    }
)

PLANT_LEFTOVER_PREFIXES = (
    "optimization.",
    "scenarios.",
    "bess.",
)'''

new_plant = '''# Safety net: never show retired plant keys if an old project still carries them.
PLANT_LEFTOVER_PATHS = frozenset()
PLANT_LEFTOVER_PREFIXES = (
    "optimization.",
    "scenarios.",
    "bess.",
    "solar.capacity_mw",
    "solar.capex_",
    "solar.opex_",
    "solar.project_life",
    "solar.energy_cost",
    "solar.degradation",
    "wind.capacity_mw",
    "wind.capex_",
    "wind.opex_",
    "wind.project_life",
    "wind.energy_cost",
    "wind.degradation",
    "grid.max_import_mw",
    "financial.financing",
    "financial.debt_",
    "financial.interest_rate",
    "financial.residual_value",
    "financial.inflation",
)'''

# Fix is_plant_leftover to use startswith on prefixes properly
# existing function already does startswith on prefixes — good if we use full path prefixes

if old_plant in text:
    text = text.replace(old_plant, new_plant)
    print("updated PLANT_LEFTOVER lists")
else:
    print("WARN: PLANT_LEFTOVER block not found")

# Patch get_default_config to strip after deepcopy
# Find get_default_config
if "def get_default_config():" in text and "strip_plant_leftovers" not in text[text.find("def get_default_config()") : text.find("def get_default_config()") + 400]:
    text2 = text
    # insert after return deepcopy(DEFAULT_CONFIG) or similar
    text2 = re.sub(
        r"(def get_default_config\(\):\n(?:.*\n){0,8}?)(\s+return deepcopy\((?:DEFAULT_CONFIG|defaults)\))",
        r"\1    cfg = deepcopy(DEFAULT_CONFIG)\n    return strip_plant_leftovers(cfg)",
        text,
        count=1,
    )
    # simpler approach
    if text2 == text:
        text = text.replace(
            "def get_default_config():\n    return deepcopy(DEFAULT_CONFIG)",
            "def get_default_config():\n    return strip_plant_leftovers(deepcopy(DEFAULT_CONFIG))",
        )
        if "strip_plant_leftovers(deepcopy(DEFAULT_CONFIG))" in text:
            print("patched get_default_config")
        else:
            # try alternate body
            m = re.search(r"def get_default_config\(\):\n((?:.+\n){1,12})", text)
            print("get_default_config body:\n", m.group(0) if m else "NOT FOUND")
    else:
        text = text2
        print("patched get_default_config via regex")

path.write_text(text, encoding="utf-8")
print("OK wrote", path)
