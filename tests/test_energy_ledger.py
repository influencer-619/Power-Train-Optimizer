"""Phase 1: energy ledger reconciliation + fingerprint + edge dispatch cases."""

from copy import deepcopy

import numpy as np
import pytest

from backend.simulation.energy_ledger import build_energy_ledger
from backend.simulation.engine import run_simulation
from backend.simulation.fingerprint import config_fingerprint
from config.defaults import get_default_config, recompute_calculated


def _cfg(**overrides):
    cfg = recompute_calculated(get_default_config())
    for path, value in overrides.items():
        section, key = path.split(".", 1)
        cfg[section][key]["value"] = value
    return recompute_calculated(cfg)


def test_energy_ledger_reconciles_default_hybrid():
    bundle = run_simulation(_cfg(), structure="HYBRID")
    assert bundle.energy_ledger is not None
    assert bundle.energy_ledger["energy_balance_ok"] is True
    assert bundle.validation["energy_balance_ok"] is True
    assert bundle.validation["overall_ok"] is True
    assert bundle.config_hash
    assert len(bundle.config_hash) == 64


def test_energy_ledger_discom_grid_only():
    bundle = run_simulation(_cfg(), structure="DISCOM")
    flows = bundle.energy_ledger["annual"]["flows"]
    assert flows["solar_generation_mwh"] == 0.0
    assert flows["wind_generation_mwh"] == 0.0
    assert flows["load_from_grid_mwh"] + flows["unserved_mwh"] == pytest.approx(
        flows["load_mwh"], abs=1e-2
    )
    assert bundle.energy_ledger["energy_balance_ok"] is True


def test_energy_ledger_zero_bess():
    cfg = _cfg(**{"bess.power_mw": 0.0, "bess.energy_mwh": 0.0, "bess.max_charge_mw": 0.0, "bess.max_discharge_mw": 0.0})
    bundle = run_simulation(cfg, structure="HYBRID")
    assert bundle.energy_ledger["energy_balance_ok"] is True
    assert bundle.kpis["bess_discharge_mwh"] == 0.0


def test_energy_ledger_no_renewables():
    cfg = _cfg(**{"solar.capacity_mw": 0.0, "wind.capacity_mw": 0.0})
    bundle = run_simulation(cfg, structure="HYBRID")
    assert bundle.kpis["annual_re_pct"] < 1.0
    assert bundle.energy_ledger["energy_balance_ok"] is True


def test_fingerprint_changes_with_inputs():
    a = _cfg()
    b = deepcopy(a)
    b["solar"]["capacity_mw"]["value"] = float(b["solar"]["capacity_mw"]["value"]) + 10.0
    assert config_fingerprint(a) != config_fingerprint(b)


def test_solar_wind_flow_identity():
    bundle = run_simulation(_cfg(), structure="HYBRID")
    d = bundle.dispatch
    assert np.allclose(
        d.solar_mw,
        d.solar_to_load_mw + d.solar_to_bess_mw + d.solar_curtailment_mw,
        atol=1e-4,
    )
    assert np.allclose(
        d.wind_mw,
        d.wind_to_load_mw + d.wind_to_bess_mw + d.wind_curtailment_mw,
        atol=1e-4,
    )


def test_bess_duration_and_losses_reported():
    bundle = run_simulation(_cfg(), structure="HYBRID")
    assert bundle.kpis["bess_duration_h"] == pytest.approx(
        bundle.kpis["bess_mwh"] / bundle.kpis["bess_mw"], rel=1e-6
    )
    assert bundle.kpis["bess_losses_mwh"] >= 0.0
    assert "bess_utilization_definition" in bundle.kpis
