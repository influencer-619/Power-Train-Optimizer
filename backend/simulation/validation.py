"""Input and dispatch validation."""

from __future__ import annotations

import numpy as np

from backend.simulation.energy_ledger import build_energy_ledger
from config.defaults import v


def validate_config(config: dict) -> list[dict]:
    issues: list[dict] = []

    def err(msg: str):
        issues.append({"level": "error", "message": msg})

    def warn(msg: str):
        issues.append({"level": "warning", "message": msg})

    peak = float(v(config, "load.peak_load_mw"))
    base = float(v(config, "load.base_load_mw"))
    lf = float(v(config, "load.load_factor_pct"))
    if peak <= 0:
        err("Load > 0 required: peak_load_mw must be positive.")
    if lf <= 0 or lf > 100:
        err("Load factor must be in (0, 100].")
    if base > peak + 1e-6:
        warn("Base load exceeds peak load after calculation.")

    for name, path in [
        ("Solar capacity", "solar.capacity_mw"),
        ("Wind capacity", "wind.capacity_mw"),
        ("BESS power", "bess.power_mw"),
        ("BESS energy", "bess.energy_mwh"),
        ("Grid max import", "grid.max_import_mw"),
    ]:
        if float(v(config, path)) < 0:
            err(f"{name} must be >= 0.")

    for label, path in [
        ("Charge efficiency", "bess.charge_efficiency_pct"),
        ("Discharge efficiency", "bess.discharge_efficiency_pct"),
        ("Initial SOC", "bess.initial_soc_pct"),
        ("Min SOC", "bess.min_soc_pct"),
        ("Max SOC", "bess.max_soc_pct"),
    ]:
        x = float(v(config, path))
        if x < 0 or x > 100:
            err(f"{label} must be within 0–100%.")

    if float(v(config, "bess.min_soc_pct")) > float(v(config, "bess.max_soc_pct")):
        err("Minimum SOC must be <= Maximum SOC.")
    if not (
        float(v(config, "bess.min_soc_pct"))
        <= float(v(config, "bess.initial_soc_pct"))
        <= float(v(config, "bess.max_soc_pct"))
    ):
        err("Initial SOC must lie between Min and Max SOC.")

    if float(v(config, "solar.sunrise_hour")) >= float(v(config, "solar.sunset_hour")):
        err("Sunrise hour must be < sunset hour.")

    hours = int(v(config, "general.model_hours"))
    if hours not in (8760, 8784):
        err("Model hours must be 8760 or 8784.")

    return issues


def validate_dispatch(d, config: dict) -> dict:
    tol = 1e-4
    abs_err = np.abs(d.balance_error_mw)
    fail_idx = np.where(abs_err > tol)[0]
    ok = len(fail_idx) == 0

    soc_min = float(v(config, "bess.min_soc_pct")) / 100.0 * float(d.meta.get("bess_energy_mwh") or 0.0)
    soc_max = float(v(config, "bess.max_soc_pct")) / 100.0 * float(d.meta.get("bess_energy_mwh") or 0.0)
    energy = float(d.meta.get("bess_energy_mwh") or 0.0)
    soc_ok = True
    if energy > 0:
        soc_ok = bool(np.all(d.soc_mwh >= soc_min - 1e-3) and np.all(d.soc_mwh <= soc_max + 1e-3))

    grid_cap = float(d.meta.get("grid_cap_effective_mw") or d.meta.get("grid_cap_mw") or 0.0)
    grid_ok = bool(np.all(d.grid_mw <= grid_cap + 1e-3))
    nonneg = bool(
        np.all(d.solar_mw >= -1e-9)
        and np.all(d.wind_mw >= -1e-9)
        and np.all(d.charge_mw >= -1e-9)
        and np.all(d.discharge_mw >= -1e-9)
        and np.all(d.grid_mw >= -1e-9)
        and np.all(d.curtailment_mw >= -1e-9)
    )
    cfe_ok = bool(np.all(d.hourly_cfe_pct <= 100.0 + 1e-6) and np.all(d.hourly_cfe_pct >= -1e-6))

    finite_ok = bool(
        np.all(np.isfinite(d.load_mw))
        and np.all(np.isfinite(d.solar_mw))
        and np.all(np.isfinite(d.wind_mw))
        and np.all(np.isfinite(d.soc_mwh))
        and np.all(np.isfinite(d.hourly_cfe_pct))
    )

    ledger = build_energy_ledger(d)
    energy_ok = bool(ledger["energy_balance_ok"])

    first_hour = int(fail_idx[0]) if len(fail_idx) else None
    model_error = None
    if not ok:
        h = first_hour if first_hour is not None else 0
        model_error = {
            "code": "POWER_BALANCE",
            "message": f"MODEL ERROR: Hourly power balance failed at hour {h}.",
            "hour": h,
            "balance_error_mw": float(d.balance_error_mw[h]),
            "expected_identity": "solar+wind+discharge+grid+unserved = load+charge+curtail",
        }
    elif not energy_ok:
        model_error = {
            "code": "ENERGY_BALANCE",
            "message": "MODEL ERROR: ENERGY BALANCE",
            "annual_reconciliation": ledger["annual"]["reconciliation"],
        }
    elif not soc_ok:
        model_error = {"code": "SOC_LIMIT", "message": "MODEL ERROR: BESS SOC outside limits."}
    elif not finite_ok:
        model_error = {"code": "NAN", "message": "MODEL ERROR: Non-finite values in dispatch arrays."}

    return {
        "power_balance_ok": ok,
        "energy_balance_ok": energy_ok,
        "first_balance_fail_hour": first_hour,
        "max_abs_balance_error_mw": float(abs_err.max()) if len(abs_err) else 0.0,
        "soc_ok": soc_ok,
        "grid_capacity_ok": grid_ok,
        "non_negative_ok": nonneg,
        "cfe_bounds_ok": cfe_ok,
        "finite_ok": finite_ok,
        "hours": int(len(d.load_mw)),
        "model_error": model_error,
        "overall_ok": bool(
            ok and energy_ok and soc_ok and grid_ok and nonneg and cfe_ok and finite_ok
        ),
    }
