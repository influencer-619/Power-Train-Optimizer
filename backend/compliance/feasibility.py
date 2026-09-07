"""Unified feasibility status + binding-constraint diagnosis."""

from __future__ import annotations

from typing import Any

from config.defaults import LEGAL_REVIEW, has_default_assumptions, v


STATUSES = (
    "FEASIBLE",
    "NOT FEASIBLE",
    "INCOMPLETE INPUTS",
    "LEGAL REVIEW REQUIRED",
    "MODEL ERROR",
)


def evaluate_feasibility(
    config: dict,
    kpis: dict,
    compliance: dict,
    validation: dict | None = None,
    *,
    enforce_re: bool | None = None,
    enforce_cfe: bool | None = None,
    enforce_unserved: bool | None = None,
) -> dict[str, Any]:
    """
    Technical/compliance feasibility for the current configuration.
    Does NOT certify legal applicability — legal gates remain separate.
    """
    validation = validation or {}
    if validation.get("model_error") or validation.get("overall_ok") is False:
        me = validation.get("model_error") or {}
        return {
            "status": "MODEL ERROR",
            "can_recommend": False,
            "primary_issue": me.get("message") or "MODEL ERROR",
            "checks": {},
            "binding_constraints": [{"code": me.get("code") or "MODEL", "message": me.get("message") or "Model error"}],
        }

    # Incomplete: critical defaults still present AND user hasn't confirmed
    incomplete = bool(has_default_assumptions(config))

    enforce_re = bool(v(config, "optimization.enforce_re_target")) if enforce_re is None else enforce_re
    enforce_cfe = bool(v(config, "optimization.enforce_cfe_target")) if enforce_cfe is None else enforce_cfe
    enforce_unserved = (
        bool(v(config, "optimization.enforce_no_unserved")) if enforce_unserved is None else enforce_unserved
    )

    re = compliance.get("annual_re", {})
    cfe = compliance.get("hourly_cfe", {})
    re_t = float(re.get("target_pct") or v(config, "compliance.annual_re_target_pct"))
    cfe_t = float(cfe.get("target_pct") or v(config, "compliance.hourly_cfe_target_pct"))
    re_a = float(re.get("actual_pct") if re.get("actual_pct") is not None else kpis.get("annual_re_pct", 0))
    cfe_a = float(cfe.get("min_pct") if cfe.get("min_pct") is not None else kpis.get("hourly_cfe_min_pct", 0))
    unserved = float(kpis.get("unserved_mwh") or 0.0)

    checks = {
        "annual_re": {
            "actual_pct": re_a,
            "target_pct": re_t,
            "gap_pct": max(0.0, re_t - re_a),
            "status": re.get("status"),
            "enforced": enforce_re,
            "pass": re.get("status") == "Pass",
        },
        "hourly_cfe": {
            "actual_pct": float(cfe.get("actual_pct") if cfe.get("actual_pct") is not None else cfe_a),
            "min_pct": cfe_a,
            "mean_pct": float(cfe.get("mean_pct") or kpis.get("hourly_cfe_mean_pct") or 0),
            "target_pct": cfe_t,
            "gap_pct": max(0.0, cfe_t - float(cfe.get("actual_pct") if cfe.get("actual_pct") is not None else cfe_a)),
            "pass_mode": cfe.get("pass_mode"),
            "status": cfe.get("status"),
            "enforced": enforce_cfe,
            "pass": cfe.get("status") == "Pass",
        },
        "unserved": {
            "actual_mwh": unserved,
            "allowed_mwh": 0.0 if enforce_unserved else None,
            "enforced": enforce_unserved,
            "pass": (unserved <= 1e-3) if enforce_unserved else True,
        },
        "rpo": {"status": compliance.get("rpo", {}).get("status"), "pass": _reg_ok(compliance.get("rpo", {}))},
        "rco": {"status": compliance.get("rco", {}).get("status"), "pass": _reg_ok(compliance.get("rco", {}))},
        "eso": {"status": compliance.get("eso", {}).get("status"), "pass": _reg_ok(compliance.get("eso", {}))},
    }

    binding: list[dict[str, Any]] = []
    if enforce_unserved and not checks["unserved"]["pass"]:
        binding.append(
            {
                "code": "UNSERVED",
                "message": "Unserved energy above allowance",
                "actual": unserved,
                "target": 0.0,
                "remedies": ["increase grid capacity", "increase BESS power/energy", "reduce peak load"],
            }
        )
    if enforce_re and not checks["annual_re"]["pass"]:
        binding.append(
            {
                "code": "ANNUAL_RE",
                "message": "Annual RE below target",
                "actual": re_a,
                "target": re_t,
                "remedies": ["increase solar", "increase wind", "reduce curtailment via BESS", "relax RE target"],
            }
        )
    if enforce_cfe and not checks["hourly_cfe"]["pass"]:
        binding.append(
            {
                "code": "HOURLY_CFE",
                "message": f"Hourly CFE failed ({cfe.get('pass_mode')})",
                "actual": checks["hourly_cfe"]["actual_pct"],
                "target": cfe_t,
                "min_hourly": cfe_a,
                "remedies": ["increase BESS energy", "increase wind (night)", "increase BESS power", "relax CFE target or pass mode"],
            }
        )

    # Soft compliance visibility (not always hard-fail for Applicable-only)
    for key in ("rpo", "rco", "eso"):
        st = checks[key]["status"]
        if st == "Fail":
            binding.append(
                {
                    "code": key.upper(),
                    "message": f"{key.upper()} status Fail",
                    "actual": st,
                    "target": "Pass",
                    "remedies": ["adjust RE/storage", "review applicability", "buyout/REC routes if modelled"],
                }
            )

    legal_pending = any(
        compliance.get(k, {}).get("status") == LEGAL_REVIEW for k in ("rpo", "rco", "eso")
    )

    hard_fail = (
        (enforce_re and not checks["annual_re"]["pass"])
        or (enforce_cfe and not checks["hourly_cfe"]["pass"])
        or (enforce_unserved and not checks["unserved"]["pass"])
    )
    target_miss = re.get("status") == "Fail" or cfe.get("status") == "Fail" or unserved > 1e-3

    if target_miss or hard_fail:
        status = "NOT FEASIBLE"
        if re.get("status") == "Fail" and not any(b["code"] == "ANNUAL_RE" for b in binding):
            binding.append(
                {
                    "code": "ANNUAL_RE",
                    "message": "Annual RE below target (target miss)",
                    "actual": re_a,
                    "target": re_t,
                    "remedies": ["increase solar/wind/BESS", "relax target"],
                }
            )
        if cfe.get("status") == "Fail" and not any(b["code"] == "HOURLY_CFE" for b in binding):
            binding.append(
                {
                    "code": "HOURLY_CFE",
                    "message": "Hourly CFE below target (target miss)",
                    "actual": checks["hourly_cfe"]["actual_pct"],
                    "target": cfe_t,
                    "min_hourly": cfe_a,
                    "remedies": ["increase BESS/wind", "relax CFE target or pass mode"],
                }
            )
        if unserved > 1e-3 and not any(b["code"] == "UNSERVED" for b in binding):
            binding.append(
                {
                    "code": "UNSERVED",
                    "message": "Unserved energy > 0",
                    "actual": unserved,
                    "target": 0.0,
                    "remedies": ["increase grid or BESS"],
                }
            )
    elif incomplete:
        status = "INCOMPLETE INPUTS"
    elif legal_pending:
        status = "LEGAL REVIEW REQUIRED"
    else:
        status = "FEASIBLE"

    primary = binding[0] if binding else None
    approx_bess = None
    if primary and primary.get("code") == "HOURLY_CFE":
        # Heuristic: each extra MWh of BESS ≈ helps night CFE; rough gap scaling
        gap = max(0.0, cfe_t - cfe_a)
        current = float(kpis.get("bess_mwh") or 0.0)
        approx_bess = round(current + gap / 100.0 * float(kpis.get("annual_load_mwh") or 0) * 0.02, 1)

    return {
        "status": status,
        "can_recommend": status == "FEASIBLE",
        "primary_issue": (primary or {}).get("message"),
        "primary_binding": primary,
        "approximate_extra_bess_mwh": approx_bess,
        "checks": checks,
        "binding_constraints": binding,
        "incomplete_inputs": incomplete,
        "pass_mode_visible": cfe.get("pass_mode"),
    }


def _reg_ok(block: dict) -> bool:
    st = block.get("status")
    if st in ("Pass", "Not Applicable"):
        return True
    if st == LEGAL_REVIEW:
        return True  # not a hard technical fail
    return st != "Fail"


def explain_no_feasible(
    config: dict,
    candidates: list[dict],
    binding_counter: dict[str, int],
) -> dict[str, Any]:
    """Build a structured no-feasible explanation from optimization candidates."""
    if not candidates and not binding_counter:
        return {
            "headline": "NO FEASIBLE SOLUTION",
            "primary_binding_constraint": None,
            "message": "No candidates were evaluated.",
            "remedies": [],
        }

    # Prefer counter, else inspect candidates
    primary_label = None
    if binding_counter:
        primary_label = max(binding_counter.items(), key=lambda kv: kv[1])[0]

    best = None
    for c in candidates:
        if best is None:
            best = c
            continue
        # Prefer higher min CFE then RE
        if float(c["kpis"].get("hourly_cfe_min_pct", 0)) > float(best["kpis"].get("hourly_cfe_min_pct", 0)):
            best = c
        elif float(c["kpis"].get("hourly_cfe_min_pct", 0)) == float(best["kpis"].get("hourly_cfe_min_pct", 0)):
            if float(c["kpis"].get("annual_re_pct", 0)) > float(best["kpis"].get("annual_re_pct", 0)):
                best = c

    cfe_t = float(v(config, "compliance.hourly_cfe_target_pct"))
    re_t = float(v(config, "compliance.annual_re_target_pct"))
    best_cfe = float(best["kpis"]["hourly_cfe_min_pct"]) if best else None
    best_re = float(best["kpis"]["annual_re_pct"]) if best else None

    remedies = []
    code = "UNKNOWN"
    if primary_label and "CFE" in primary_label.upper():
        code = "HOURLY_CFE"
        remedies = ["increase BESS energy", "increase wind", "increase BESS power", "relax CFE target"]
    elif primary_label and "RE" in primary_label.upper():
        code = "ANNUAL_RE"
        remedies = ["increase solar", "increase wind", "relax RE target"]
    elif primary_label and "unserved" in primary_label.lower():
        code = "UNSERVED"
        remedies = ["increase grid capacity", "increase BESS", "reduce load"]
    else:
        remedies = ["widen capacity bounds", "relax targets", "switch search to Thorough"]

    approx = None
    if code == "HOURLY_CFE" and best_cfe is not None:
        gap = max(0.0, cfe_t - best_cfe)
        cur = float((best or {}).get("candidate", {}).get("bess_mwh") or 0)
        approx = round(cur + gap * 8.0, 1)  # rough heuristic from model results scale

    return {
        "headline": "NO FEASIBLE SOLUTION",
        "primary_binding_constraint": code if primary_label else None,
        "primary_label": primary_label,
        "target_cfe_pct": cfe_t,
        "best_achieved_cfe_min_pct": best_cfe,
        "target_re_pct": re_t,
        "best_achieved_re_pct": best_re,
        "best_candidate": (best or {}).get("candidate"),
        "additional_bess_mwh_approx": approx,
        "other_potential_remedies": remedies,
        "binding_counts": dict(binding_counter),
        "message": (
            f"Primary binding constraint: {primary_label or 'unknown'}. "
            + (
                f"CFE target {cfe_t}% — best achieved min hourly CFE {best_cfe:.1f}%."
                if best_cfe is not None and code == "HOURLY_CFE"
                else ""
            )
        ),
    }
