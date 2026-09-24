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

    from config.defaults import v_opt

    enforce_re = (
        bool(v_opt(config, "optimization.enforce_re_target", False))
        if enforce_re is None
        else enforce_re
    )
    # CFE Pass/Fail is always reported from the formula; it is not a feasibility gate.
    enforce_cfe = False if enforce_cfe is None else enforce_cfe
    # Buyer path: plant-shaped 8760 unserved is diagnostic only (BESS plant = 0 by design).
    # Never gate Captive/Hybrid/DISCOM feasibility on profile unserved unless explicitly forced.
    try:
        structure = str(v(config, "commercial.structure") or "")
    except Exception:
        structure = ""
    buyer_path = structure in ("DISCOM", "CAPTIVE", "HYBRID", "OPEN_ACCESS")
    if enforce_unserved is None:
        enforce_unserved = False if buyer_path else bool(v_opt(config, "optimization.enforce_no_unserved", False))

    re = compliance.get("annual_re", {})
    cfe = compliance.get("hourly_cfe", {})
    re_t = float(re.get("target_pct") or v(config, "compliance.annual_re_target_pct"))
    cfe_t = float(cfe.get("target_pct") or v(config, "compliance.hourly_cfe_target_pct"))
    re_a = float(re.get("actual_pct") if re.get("actual_pct") is not None else kpis.get("annual_re_pct", 0))
    cfe_a = float(cfe.get("min_pct") if cfe.get("min_pct") is not None else kpis.get("hourly_cfe_min_pct", 0))
    # Commercial KPI unserved is 0 on buyer path; fall back to dispatch diagnostic only if enforced
    unserved = float(kpis.get("unserved_mwh") or 0.0)
    dispatch_unserved = float(kpis.get("dispatch_unserved_mwh") or unserved)

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
            "dispatch_mwh": dispatch_unserved,
            "allowed_mwh": 0.0 if enforce_unserved else None,
            "enforced": enforce_unserved,
            "pass": (unserved <= 1e-3) if enforce_unserved else True,
            "note": "Buyer path ignores plant-profile unserved" if buyer_path and not enforce_unserved else None,
        },
        "rpo_rco": {
            "status": (compliance.get("rpo_rco") or compliance.get("rpo") or {}).get("status"),
            "pass": _reg_ok(compliance.get("rpo_rco") or compliance.get("rpo") or {}),
        },
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
                "remedies": [
                    "raise Architecture DISCOM mix % (grid backup)",
                    "raise contracted Solar/Wind/BESS mix %",
                    "reduce peak / study load",
                ],
            }
        )
    if enforce_re and not checks["annual_re"]["pass"]:
        binding.append(
            {
                "code": "ANNUAL_RE",
                "message": "Annual RE below target",
                "actual": re_a,
                "target": re_t,
                "remedies": [
                    "raise Architecture Solar% / Wind% / BESS%",
                    "lower annual RE target",
                ],
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
                "remedies": [
                    "raise Architecture Solar%+Wind%+BESS% (firm CFE)",
                    "lower hourly CFE target",
                ],
            }
        )

    # Soft compliance visibility (not always hard-fail for Applicable-only)
    for key in ("rpo_rco", "eso"):
        st = checks[key]["status"]
        if st == "Fail":
            label = "RPO/RCO" if key == "rpo_rco" else "ESO"
            binding.append(
                {
                    "code": "RPO_RCO" if key == "rpo_rco" else "ESO",
                    "message": f"{label} status Fail",
                    "actual": st,
                    "target": "Pass",
                    "remedies": [
                        "raise Architecture RE / BESS mix %",
                        "review applicability",
                        "use buyout/REC route if modelled",
                    ],
                }
            )

    legal_pending = any(
        (compliance.get(k) or {}).get("status") == LEGAL_REVIEW for k in ("rpo_rco", "rpo", "rco", "eso")
    )

    hard_fail = (
        (enforce_re and not checks["annual_re"]["pass"])
        or (enforce_cfe and not checks["hourly_cfe"]["pass"])
        or (enforce_unserved and not checks["unserved"]["pass"])
    )
    # Buyer Architecture: feasibility = RE/CFE targets only (not plant-profile unserved)
    target_miss = re.get("status") == "Fail" or cfe.get("status") == "Fail"
    if enforce_unserved and unserved > 1e-3:
        target_miss = True

    if target_miss or hard_fail:
        status = "NOT FEASIBLE"
        if re.get("status") == "Fail" and not any(b["code"] == "ANNUAL_RE" for b in binding):
            binding.append(
                {
                    "code": "ANNUAL_RE",
                    "message": "Annual RE below target (target miss)",
                    "actual": re_a,
                    "target": re_t,
                    "remedies": ["raise Architecture Solar%/Wind%/BESS%", "lower annual RE target"],
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
                    "remedies": ["raise Architecture Solar%+Wind%+BESS%", "lower hourly CFE target"],
                }
            )
        if enforce_unserved and unserved > 1e-3 and not any(b["code"] == "UNSERVED" for b in binding):
            binding.append(
                {
                    "code": "UNSERVED",
                    "message": "Unserved energy > 0",
                    "actual": unserved,
                    "target": 0.0,
                    "remedies": ["raise Architecture DISCOM or RE mix %"],
                }
            )
    elif incomplete:
        status = "INCOMPLETE INPUTS"
    elif legal_pending:
        status = "LEGAL REVIEW REQUIRED"
    else:
        status = "FEASIBLE"

    primary = binding[0] if binding else None
    # Architecture gap vs target (pp), not plant BESS MWh
    approx_mix_pp = None
    if primary and primary.get("code") in ("HOURLY_CFE", "ANNUAL_RE"):
        gap = max(0.0, float(primary.get("target") or 0) - float(primary.get("actual") or primary.get("min_hourly") or 0))
        approx_mix_pp = round(gap, 1)

    return {
        "status": status,
        "can_recommend": status == "FEASIBLE",
        "primary_issue": (primary or {}).get("message"),
        "primary_binding": primary,
        "approximate_extra_architecture_re_pp": approx_mix_pp,
        "approximate_extra_bess_mwh": None,  # plant sizing removed on buyer path
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
        remedies = ["raise Architecture Solar%+Wind%+BESS%", "lower hourly CFE target"]
    elif primary_label and "RE" in primary_label.upper():
        code = "ANNUAL_RE"
        remedies = ["raise Architecture Solar%/Wind%/BESS%", "lower annual RE target"]
    elif primary_label and "unserved" in primary_label.lower():
        code = "UNSERVED"
        remedies = ["raise Architecture DISCOM or RE mix %", "reduce load"]
    else:
        remedies = ["raise Architecture RE mix %", "relax compliance targets"]

    approx = None
    if code in ("HOURLY_CFE", "ANNUAL_RE") and best_cfe is not None:
        gap = max(0.0, cfe_t - best_cfe) if code == "HOURLY_CFE" else max(0.0, re_t - (best_re or 0.0))
        approx = round(gap, 1)

    return {
        "headline": "NO FEASIBLE SOLUTION",
        "primary_binding_constraint": code if primary_label else None,
        "primary_label": primary_label,
        "target_cfe_pct": cfe_t,
        "best_achieved_cfe_min_pct": best_cfe,
        "target_re_pct": re_t,
        "best_achieved_re_pct": best_re,
        "best_candidate": (best or {}).get("candidate"),
        "additional_architecture_re_pp_approx": approx,
        "additional_bess_mwh_approx": None,
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
