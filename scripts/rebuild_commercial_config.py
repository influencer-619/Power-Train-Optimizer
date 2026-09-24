# -*- coding: utf-8 -*-
"""Rebuild commercial product layers into config/defaults/config.py."""
from __future__ import annotations

import re
from pathlib import Path

CFG = Path(__file__).resolve().parents[1] / "config" / "defaults" / "config.py"


LOAD_HEAD = '''    "load": {
        "profile_source": P(
            "SYNTHETIC",
            "",
            DEFAULT_ASSUMPTION,
            "SYNTHETIC = parameterized generator. PROJECT DATA = imported hourly MW series (optional).",
            kind="select",
            options=["SYNTHETIC", "PROJECT DATA"],
        ),
        "it_load_mw": P(
            250.0,
            "MW",
            CALCULATED,
            "Same as Data Centre → IT capacity. Facility peak = IT Load × PUE.",
            minimum=0.01,
            step=0.1,
            editable=False,
        ),
        "pue": P(
            1.25,
            "x",
            DEFAULT_ASSUMPTION,
            "Power Usage Effectiveness. Total facility load = IT Load × PUE.",
            minimum=1.0,
            maximum=3.0,
            step=0.01,
        ),
        "peak_load_mw": P(
            250.0,
            "MW",
            CALCULATED,
            "Total facility load = it_load_mw × pue. Used for the hourly load profile over the study period.",
            minimum=0.01,
            step=0.1,
            editable=False,
        ),
        "load_factor_pct": P(
            70.0,
            "%",
            CALCULATED,
            "Primary load factor (synced from Scenario 1). Actual average = Total load × LF. "
            "Run Analysis evaluates four LF scenarios in one pass.",
            minimum=1,
            maximum=100,
            step=0.1,
            editable=False,
        ),
        "load_factor_s1_pct": P(
            70.0,
            "%",
            DEFAULT_ASSUMPTION,
            "Load-factor scenario 1. Actual Load = Total load × LF. All four scenarios run in one analysis.",
            minimum=1,
            maximum=100,
            step=0.1,
        ),
        "load_factor_s2_pct": P(
            80.0,
            "%",
            DEFAULT_ASSUMPTION,
            "Load-factor scenario 2. Actual Load = Total load × LF.",
            minimum=1,
            maximum=100,
            step=0.1,
        ),
        "load_factor_s3_pct": P(
            90.0,
            "%",
            DEFAULT_ASSUMPTION,
            "Load-factor scenario 3. Actual Load = Total load × LF.",
            minimum=1,
            maximum=100,
            step=0.1,
        ),
        "load_factor_s4_pct": P(
            100.0,
            "%",
            DEFAULT_ASSUMPTION,
            "Load-factor scenario 4. Actual Load = Total load × LF.",
            minimum=1,
            maximum=100,
            step=0.1,
        ),
        "base_load_mw": P(
            175.0,
            "MW",
            CALCULATED,
            "Actual average load = peak_load_mw × load_factor_pct / 100.",
            editable=False,
        ),
'''

GRID_EXCEL = '''
        "demand_charge_inr_per_kva_month": P(
            400.0,
            "₹/kVA-month",
            DEFAULT_ASSUMPTION,
            "DISCOM demand charge (₹/kVA/month). Engine uses ₹/MW-month = this × 1,000.",
            minimum=0,
            step=1,
        ),
        "meter_rent_inr_per_month": P(0.0, "₹/month", DEFAULT_ASSUMPTION, "Meter rent (monthly). Added to annual fixed grid cost × 12."),
        "liquidated_damages_inr_per_month": P(0.0, "₹/month", DEFAULT_ASSUMPTION, "Liquidated damages / default charge (monthly). Added × 12 to annual fixed cost."),
        "power_factor": P(0.95, "PU", DEFAULT_ASSUMPTION, "Power factor (PU). Documentation / optional kVArh framing."),
        "kvarh_lagging_inr_per_kvarh": P(0.0, "₹/kVArh", DEFAULT_ASSUMPTION, "kVArh charge for lagging PF (not auto-applied without reactive series)."),
        "kvarh_leading_inr_per_kvarh": P(0.0, "₹/kVArh", DEFAULT_ASSUMPTION, "kVArh surcharge for leading PF (not auto-applied without reactive series)."),
        "grid_restricted": P(False, "", DEFAULT_ASSUMPTION, "Grid restricted flag (contract / operational constraint marker).", kind="boolean"),
        "excel_discom_energy_inr_per_kwh": P(8.44, "₹/kWh", DEFAULT_ASSUMPTION, "DISCOM Energy Charges (base energy tariff).", step=0.01),
        "excel_discom_wheeling_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "DISCOM Wheeling charges.", step=0.01),
        "excel_discom_tod_inr_per_kwh": P(-0.56, "₹/kWh", DEFAULT_ASSUMPTION, "DISCOM net TOD adjustment (peak extra − off-peak rebate; may be negative).", step=0.01),
        "excel_discom_ed_inr_per_kwh": P(0.59, "₹/kWh", DEFAULT_ASSUMPTION, "DISCOM Electricity duty (₹/kWh).", step=0.01),
        "excel_discom_tose_inr_per_kwh": P(0.28, "₹/kWh", DEFAULT_ASSUMPTION, "DISCOM TOSE / other statutory surcharge (₹/kWh).", step=0.01),
        "excel_discom_other_volumetric_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "DISCOM other volumetric charges (FPPCA / misc ₹/kWh).", step=0.01),
        "excel_discom_total_inr_per_kwh": P(8.75, "₹/kWh", CALCULATED, "Total DISCOM = Energy + Wheeling + TOD + ED + TOSE + Other.", editable=False, step=0.01),
'''

COMMERCIAL_EXCEL = '''
        "cost_blend_basis": P(
            "TARGET_POWER_PCT",
            "",
            DEFAULT_ASSUMPTION,
            "CAPTIVE/DISCOM/HYBRID energy blend: TARGET_POWER_PCT = Architecture Percentage of power; "
            "SIMULATED_ENERGY_SHARE = 8760h dispatch Grid|RE shares.",
            kind="select",
            options=["TARGET_POWER_PCT", "SIMULATED_ENERGY_SHARE"],
        ),
        "excel_solar_ppa_inr_per_kwh": P(3.5, "₹/kWh", DEFAULT_ASSUMPTION, "Solar Energy Charges PPA (MH captive sample).", step=0.01),
        "excel_solar_energy_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Energy Charges (Solar; usually 0 when PPA is used).", step=0.01),
        "excel_solar_wheeling_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Wheeling (0 for EHV/STU captive; ~0.60 HT third-party).", step=0.01),
        "excel_solar_transmission_inr_per_kwh": P(0.50, "₹/kWh", DEFAULT_ASSUMPTION, "Transmission (MH RE OA sample ~0.49–0.50).", step=0.01),
        "excel_solar_transmission_loss_inr_per_kwh": P(0.11, "₹/kWh", DEFAULT_ASSUMPTION, "Transmission loss ₹/kWh proxy (~3.18% × PPA).", step=0.01),
        "excel_solar_css_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "CSS (0 for captive / GEOA exemption paths).", step=0.01),
        "excel_solar_as_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Additional surcharge (0 for captive / GEOA + demand charges).", step=0.01),
        "excel_solar_sldc_inr_per_kwh": P(0.05, "₹/kWh", DEFAULT_ASSUMPTION, "SLDC volumetric proxy (actual often ₹/MW/day).", step=0.01),
        "excel_solar_banking_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Banking ₹/kWh (MH GEOA is typically 8% in-kind).", step=0.01),
        "excel_solar_ed_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Electricity duty on solar.", step=0.01),
        "excel_solar_tose_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "TOSE on solar.", step=0.01),
        "excel_solar_total_inr_per_kwh": P(4.16, "₹/kWh", CALCULATED, "Sum of solar charge stack (PPA + charges).", editable=False, step=0.01),
        "excel_wind_ppa_inr_per_kwh": P(3.5, "₹/kWh", DEFAULT_ASSUMPTION, "Wind Energy Charges PPA (MH captive sample).", step=0.01),
        "excel_wind_energy_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Energy Charges (Wind).", step=0.01),
        "excel_wind_wheeling_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Wheeling (0 for EHV/STU captive; ~0.60 HT third-party).", step=0.01),
        "excel_wind_transmission_inr_per_kwh": P(0.50, "₹/kWh", DEFAULT_ASSUMPTION, "Transmission (MH RE OA sample ~0.49–0.50).", step=0.01),
        "excel_wind_transmission_loss_inr_per_kwh": P(0.11, "₹/kWh", DEFAULT_ASSUMPTION, "Transmission loss ₹/kWh proxy (~3.18% × PPA).", step=0.01),
        "excel_wind_css_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "CSS (0 for captive / GEOA exemption paths).", step=0.01),
        "excel_wind_as_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Additional surcharge (0 for captive / GEOA + demand charges).", step=0.01),
        "excel_wind_sldc_inr_per_kwh": P(0.05, "₹/kWh", DEFAULT_ASSUMPTION, "SLDC volumetric proxy (actual often ₹/MW/day).", step=0.01),
        "excel_wind_banking_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Banking ₹/kWh (MH GEOA is typically 8% in-kind).", step=0.01),
        "excel_wind_ed_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Electricity duty (Wind).", step=0.01),
        "excel_wind_tose_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "TOSE (Wind).", step=0.01),
        "excel_wind_total_inr_per_kwh": P(4.16, "₹/kWh", CALCULATED, "Sum of wind charge stack.", editable=False, step=0.01),
        "excel_bess_ppa_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "BESS Energy Charges PPA (usually 0 for captive; cost via CAPEX/OPEX).", step=0.01),
        "excel_bess_energy_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Energy Charges (BESS).", step=0.01),
        "excel_bess_wheeling_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Wheeling charges (BESS).", step=0.01),
        "excel_bess_transmission_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Transmission charges (BESS).", step=0.01),
        "excel_bess_transmission_loss_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Transmission losses (BESS).", step=0.01),
        "excel_bess_css_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Cross subsidy (BESS).", step=0.01),
        "excel_bess_as_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Additional surcharge (BESS).", step=0.01),
        "excel_bess_sldc_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "SLDC charges (BESS).", step=0.01),
        "excel_bess_banking_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Banking cost (BESS).", step=0.01),
        "excel_bess_ed_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Electricity duty (BESS).", step=0.01),
        "excel_bess_tose_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "TOSE (BESS).", step=0.01),
        "excel_bess_total_inr_per_kwh": P(0.0, "₹/kWh", CALCULATED, "Sum of BESS charge stack.", editable=False, step=0.01),
'''

COMPLIANCE = '''    "compliance": {
        "rpo_rco_applicability": P(
            "Unknown / Legal Review Required",
            "",
            CONCEPT_NOTE,
            "Integrated RPO/RCO applicability (purchase + consumption obligation). "
            "User-declared — the model does not infer it.",
            kind="select",
            options=["Applicable", "Not Applicable", "Unknown / Legal Review Required"],
        ),
        "rpo_rco_target_pct": P(
            0.0,
            "%",
            DEFAULT_ASSUMPTION,
            "Integrated RPO/RCO target (% of DC load that must be met from RE). "
            "One target covers both Renewable Purchase and Consumption Obligation.",
            minimum=0,
            maximum=100,
            step=0.1,
        ),
        "rpo_rco_compliance_route": P(
            "Buyout",
            "",
            DEFAULT_ASSUMPTION,
            "How shortfall is costed if Applicable (Buyout or REC).",
            kind="select",
            options=["Buyout", "REC", "Self-generation", "Unknown", "Other"],
        ),
        "rpo_rco_buyout_inr_per_kwh": P(
            1.00,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "RPO/RCO shortfall buyout cost when route is Buyout (or not REC).",
        ),
        "rpo_rco_rec_inr_per_kwh": P(
            1.00,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "REC cost used when RPO/RCO compliance route is REC.",
        ),
        "eso_applicability": P(
            "Unknown / Legal Review Required",
            "",
            CONCEPT_NOTE,
            "ESO applicability is user-declared.",
            kind="select",
            options=["Applicable", "Not Applicable", "Unknown / Legal Review Required"],
        ),
        "eso_target_pct": P(
            2.5,
            "%",
            CONCEPT_NOTE,
            "Single ESO storage obligation target (% of annual DC load).",
            minimum=0,
            maximum=100,
            step=0.1,
        ),
        "eso_re_origin_min_pct": P(
            85.0,
            "%",
            CONCEPT_NOTE,
            "Minimum renewable-origin share of stored energy under the ESO requirement.",
        ),
        "eso_buyout_inr_per_kwh": P(1.20, "₹/kWh", DEFAULT_ASSUMPTION, "ESO shortfall / origin-failure cost if applicable."),
        "annual_re_target_pct": P(90.0, "%", CONCEPT_NOTE, "Selected annual RE / Architecture CFE mix target."),
        "hourly_cfe_target_pct": P(
            90.0,
            "%",
            CONCEPT_NOTE,
            "24×7 CFE target. Pass = every hour’s CFE% from "
            "Min(Load, Solar+Wind+CF-BESS)/Load × 100 meets this target; otherwise Fail.",
            minimum=0,
            maximum=100,
            step=0.1,
        ),
        "grid_emission_factor_tco2_per_mwh": P(
            0.82,
            "tCO2/MWh",
            DEFAULT_ASSUMPTION,
            "Grid emission factor for carbon accounting (baseline and DISCOM share).",
            minimum=0,
            step=0.01,
        ),
    },
'''

GENERAL_EXTRA = '''
        "study_start_month": P(
            1,
            "",
            DEFAULT_ASSUMPTION,
            "Study period start month (1=Jan). Model hours = days in range × 24.",
            kind="integer",
            minimum=1,
            maximum=12,
        ),
        "study_end_month": P(
            12,
            "",
            DEFAULT_ASSUMPTION,
            "Study period end month (1=Jan … 12=Dec).",
            kind="integer",
            minimum=1,
            maximum=12,
        ),
'''

RECOMPUTE = '''def recompute_calculated(config: dict) -> dict:
    """Refresh calculated fields (peak, LF, stack totals, study hours, migrations)."""
    # Study period → model hours
    try:
        from backend.simulation.calendar import clamp_month, hours_in_month_range

        general = config.get("general") or {}
        if "study_start_month" in general and "study_end_month" in general:
            sm = clamp_month(int(v(config, "general.study_start_month")))
            em = clamp_month(int(v(config, "general.study_end_month")))
            if sm > em:
                em = sm
            general["study_start_month"]["value"] = sm
            general["study_end_month"]["value"] = em
            auto_h = int(hours_in_month_range(sm, em, leap=False))
            if "model_hours" in general:
                mh = general["model_hours"]
                if mh.get("source") == USER_INPUT:
                    try:
                        h = int(mh.get("value") or auto_h)
                    except Exception:
                        h = auto_h
                    h = max(24, min(8784, h))
                    mh["value"] = h
                    if h == auto_h:
                        mh["source"] = CALCULATED
                else:
                    mh["value"] = auto_h
                    mh["source"] = CALCULATED
            model_h = int(v(config, "general.model_hours")) if "model_hours" in general else auto_h
            load = config.get("load") or {}
            if "operating_hours" in load:
                load["operating_hours"]["value"] = int(model_h)
                load["operating_hours"]["source"] = CALCULATED
                load["operating_hours"]["editable"] = False
            if "study_years" in load:
                n_months = em - sm + 1
                load["study_years"]["value"] = round(n_months / 12.0, 6)
                load["study_years"]["source"] = CALCULATED
                load["study_years"]["editable"] = False
    except Exception:
        pass

    # Force Seasonal TOD as sole load shape when present
    try:
        if "load_model" in config.get("load", {}):
            config["load"]["load_model"]["value"] = "Seasonal TOD"
            config["load"]["load_model"]["editable"] = False
    except Exception:
        pass

    # IT capacity (Data Centre) → IT load; IT × PUE → peak
    try:
        load = config.get("load") or {}
        dc = config.get("data_center") or {}
        if "it_capacity_mw" in dc and "it_load_mw" in load:
            it = float(v(config, "data_center.it_capacity_mw"))
            load["it_load_mw"]["value"] = round(it, 6)
            load["it_load_mw"]["source"] = CALCULATED
            load["it_load_mw"]["editable"] = False
        if "it_load_mw" in load and "pue" in load:
            it = float(v(config, "load.it_load_mw"))
            pue = float(v(config, "load.pue"))
            total_mw = round(it * pue, 6)
            config["load"]["peak_load_mw"]["value"] = total_mw
            config["load"]["peak_load_mw"]["source"] = CALCULATED
            if config["load"]["peak_load_mw"].get("editable") is not False:
                config["load"]["peak_load_mw"]["editable"] = False
        else:
            total_mw = float(v(config, "load.peak_load_mw"))
    except Exception:
        total_mw = float(v(config, "load.peak_load_mw"))

    # Sync primary LF from scenario 1 unless SCENARIO/USER override
    try:
        s1 = float(v(config, "load.load_factor_s1_pct"))
        lf_src = str(config["load"]["load_factor_pct"].get("source") or "").upper()
        if lf_src not in ("SCENARIO", "USER"):
            config["load"]["load_factor_pct"]["value"] = s1
            config["load"]["load_factor_pct"]["source"] = CALCULATED
            if config["load"]["load_factor_pct"].get("editable") is not False:
                config["load"]["load_factor_pct"]["editable"] = False
    except Exception:
        pass

    lf = float(v(config, "load.load_factor_pct")) / 100.0
    config["load"]["base_load_mw"]["value"] = round(total_mw * lf, 6)
    try:
        config["grid"]["connection_voltage_kv"]["value"] = v(config, "data_center.grid_connection_kv")
    except Exception:
        pass

    # DISCOM / Solar / Wind / BESS stack totals + demand ₹/kVA → ₹/MW
    try:
        other_vol = 0.0
        try:
            other_vol = float(v(config, "grid.excel_discom_other_volumetric_inr_per_kwh"))
        except Exception:
            other_vol = 0.0
        discom_total = (
            float(v(config, "grid.excel_discom_energy_inr_per_kwh"))
            + float(v(config, "grid.excel_discom_wheeling_inr_per_kwh"))
            + float(v(config, "grid.excel_discom_tod_inr_per_kwh"))
            + float(v(config, "grid.excel_discom_ed_inr_per_kwh"))
            + float(v(config, "grid.excel_discom_tose_inr_per_kwh"))
            + other_vol
        )
        if "excel_discom_total_inr_per_kwh" in config.get("grid", {}):
            config["grid"]["excel_discom_total_inr_per_kwh"]["value"] = round(discom_total, 6)
            config["grid"]["excel_discom_total_inr_per_kwh"]["source"] = CALCULATED
    except Exception:
        pass
    try:
        grid = config.get("grid") or {}
        if "demand_charge_inr_per_kva_month" in grid and "demand_charge_inr_per_mw_month" in grid:
            kva = float(v(config, "grid.demand_charge_inr_per_kva_month"))
            grid["demand_charge_inr_per_mw_month"]["value"] = round(kva * 1000.0, 6)
            grid["demand_charge_inr_per_mw_month"]["source"] = CALCULATED
            grid["demand_charge_inr_per_mw_month"]["editable"] = False
    except Exception:
        pass
    try:
        for asset in ("solar", "wind", "bess"):
            total_key = f"excel_{asset}_total_inr_per_kwh"
            if total_key not in config.get("commercial", {}):
                continue
            parts = [
                f"excel_{asset}_ppa_inr_per_kwh",
                f"excel_{asset}_energy_inr_per_kwh",
                f"excel_{asset}_wheeling_inr_per_kwh",
                f"excel_{asset}_transmission_inr_per_kwh",
                f"excel_{asset}_transmission_loss_inr_per_kwh",
                f"excel_{asset}_css_inr_per_kwh",
                f"excel_{asset}_as_inr_per_kwh",
                f"excel_{asset}_sldc_inr_per_kwh",
                f"excel_{asset}_banking_inr_per_kwh",
                f"excel_{asset}_ed_inr_per_kwh",
                f"excel_{asset}_tose_inr_per_kwh",
            ]
            s = 0.0
            for k in parts:
                try:
                    s += float(v(config, f"commercial.{k}"))
                except Exception:
                    pass
            config["commercial"][total_key]["value"] = round(s, 6)
            config["commercial"][total_key]["source"] = CALCULATED
    except Exception:
        pass

    # Architecture flags + mix before syncing legacy RE/grid aliases
    _normalize_architecture_flags(config)
    ensure_architecture_mix_sums_to_100(config)

    # Architecture mix aliases
    try:
        commercial = config.get("commercial") or {}
        g = float(v(config, "commercial.mix_discom_pct")) if commercial.get("include_discom", {}).get("value", True) else 0.0
        s = float(v(config, "commercial.mix_solar_pct")) if commercial.get("include_solar", {}).get("value", True) else 0.0
        w = float(v(config, "commercial.mix_wind_pct")) if commercial.get("include_wind", {}).get("value", True) else 0.0
        b = float(v(config, "commercial.mix_bess_pct")) if commercial.get("include_bess", {}).get("value", True) else 0.0
        if "grid_power_pct" in commercial:
            commercial["grid_power_pct"]["value"] = g
            commercial["grid_power_pct"]["source"] = CALCULATED
            commercial["grid_power_pct"]["editable"] = False
        if "captive_re_pct" in commercial:
            commercial["captive_re_pct"]["value"] = s + w + b
            commercial["captive_re_pct"]["source"] = CALCULATED
            commercial["captive_re_pct"]["editable"] = False
    except Exception:
        pass

    # Migrate legacy RPO/RCO splits → integrated
    try:
        comp = config.get("compliance") or {}
        legacy_split = 0.0
        for key in (
            "rpo_solar_target_pct",
            "rpo_wind_target_pct",
            "rpo_hydro_target_pct",
            "rpo_other_target_pct",
        ):
            if key in comp:
                try:
                    legacy_split += float(comp[key].get("value") or 0.0)
                except Exception:
                    pass
        if "rpo_rco_target_pct" in comp:
            cur = float(comp["rpo_rco_target_pct"].get("value") or 0.0)
            legacy_tgt = 0.0
            for key in ("rpo_target_pct", "rco_target_pct"):
                if key in comp:
                    try:
                        legacy_tgt = max(legacy_tgt, float(comp[key].get("value") or 0.0))
                    except Exception:
                        pass
            pick = max(legacy_tgt, legacy_split)
            if cur == 0.0 and pick > 0.0:
                comp["rpo_rco_target_pct"]["value"] = pick
                comp["rpo_rco_target_pct"]["source"] = CALCULATED
        for key in (
            "rpo_solar_target_pct",
            "rpo_wind_target_pct",
            "rpo_hydro_target_pct",
            "rpo_other_target_pct",
            "rpo_applicability",
            "rpo_target_pct",
            "rpo_buyout_inr_per_kwh",
            "rco_applicability",
            "rco_target_pct",
            "rco_compliance_route",
            "rco_buyout_inr_per_kwh",
            "rco_rec_inr_per_kwh",
            "eso_fy2026_27_pct",
            "eso_fy2027_28_pct",
            "eso_fy2028_29_pct",
            "eso_fy2029_30_pct",
            "eso_active_year",
            "cfe_pass_mode",
            "cfe_hour_share_target_pct",
            "enforce_cfe_target",
        ):
            comp.pop(key, None)
        if "eso_target_pct" not in comp and "eso_applicability" in comp:
            from copy import deepcopy as _dc
            defaults = get_default_config()
            if "eso_target_pct" in defaults.get("compliance", {}):
                comp["eso_target_pct"] = _dc(defaults["compliance"]["eso_target_pct"])
    except Exception:
        pass

    return config
'''


def replace_block(text: str, start_pat: str, end_pat: str, new_block: str) -> str:
    m0 = re.search(start_pat, text)
    if not m0:
        raise SystemExit(f"start not found: {start_pat}")
    m1 = re.search(end_pat, text[m0.start() :])
    if not m1:
        raise SystemExit(f"end not found after start: {end_pat}")
    end = m0.start() + m1.start()
    return text[: m0.start()] + new_block + text[end:]


def main() -> None:
    text = CFG.read_text(encoding="utf-8")

    # general: insert study months before model_hours if missing
    if "study_start_month" not in text:
        text = text.replace(
            '        "model_hours": P(',
            GENERAL_EXTRA + '        "model_hours": P(',
            1,
        )

    # load head replace through base_load_mw; keep original operating_hours onward
    text = replace_block(
        text,
        r'    "load": \{',
        r'        "operating_hours": P\(',
        LOAD_HEAD,
    )

    # Force Seasonal TOD option present
    text = text.replace(
        'options=["Flat", "Daily Pattern", "Weekday/Weekend", "Seasonal", "Custom Parameterized"],',
        'options=["Seasonal TOD", "Flat", "Daily Pattern", "Weekday/Weekend", "Seasonal", "Custom Parameterized"],',
        1,
    )

    # grid excel insert before banking_enabled close of grid
    if "excel_discom_energy_inr_per_kwh" not in text:
        text = text.replace(
            '        "banking_enabled": P(False, "", DEFAULT_ASSUMPTION, "Legacy Grid-tab banking switch. RE banking uses commercial.re_banking_enabled.", kind="boolean"),\n    },',
            '        "banking_enabled": P(False, "", DEFAULT_ASSUMPTION, "Legacy Grid-tab banking switch. RE banking uses commercial.re_banking_enabled.", kind="boolean"),'
            + GRID_EXCEL
            + "    },",
            1,
        )

    # commercial excel + flags — insert after include_generation if missing, else after structure
    if "excel_solar_ppa_inr_per_kwh" not in text:
        # after include_bess block
        marker = '            "Include BESS. Selectable for CAPTIVE, HYBRID and OPEN ACCESS. Off for DISCOM.",\n            kind="boolean",\n        ),\n'
        if marker in text:
            text = text.replace(marker, marker + COMMERCIAL_EXCEL, 1)
        else:
            raise SystemExit("commercial insert marker not found")

    if "include_generation_capex" in text and text.count("include_generation_capex") > 1:
        # may duplicate — leave; merge_missing handles
        pass

    # Replace compliance section; keep original financial key
    text = replace_block(
        text,
        r'    "compliance": \{',
        r'    "financial": \{',
        COMPLIANCE,
    )

    # Replace recompute_calculated; keep original _OBSOLETE_BESS_KEYS marker
    text = replace_block(
        text,
        r'def recompute_calculated\(config: dict\) -> dict:',
        r'\n\n_OBSOLETE_BESS_KEYS',
        RECOMPUTE,
    )

    # Buyer-path default: tariff stacks, not plant CAPEX
    text = text.replace(
        '"include_generation_capex": P(\n            True,\n            "",\n            DEFAULT_ASSUMPTION,\n'
        '            "If true, solar/wind/BESS CAPEX enters the cash-flow (typical for hybrid ownership). '
        'If false, generation is treated as a tariff (typical for some OA/captive contracts).",\n'
        '            kind="boolean",\n        ),',
        '"include_generation_capex": P(\n            False,\n            "",\n            DEFAULT_ASSUMPTION,\n'
        '            "Data-centre buyer path: energy priced via Architecture tariff / PPA stacks only. '
        'Plant generation CAPEX/OPEX excluded when False.",\n'
        '            kind="boolean",\n        ),',
        1,
    )

    # Restore apply_architecture_profile if missing (wiped by git restore)
    if "def apply_architecture_profile" not in text:
        arch_helpers = '''
def _apply_first_time_structure_includes(commercial: dict, structure: str) -> None:
    """Sensible include_* defaults when no per-architecture memory exists yet."""

    def set_flag(key: str, val: bool) -> None:
        p = commercial.get(key)
        if isinstance(p, dict) and "value" in p:
            p["value"] = val

    if structure == "DISCOM":
        set_flag("include_discom", True)
        set_flag("include_solar", False)
        set_flag("include_wind", False)
        set_flag("include_bess", False)
    elif structure == "CAPTIVE":
        set_flag("include_discom", False)
        set_flag("include_solar", True)
        set_flag("include_wind", True)
        set_flag("include_bess", True)
    else:
        set_flag("include_discom", True)
        set_flag("include_solar", True)
        set_flag("include_wind", True)
        set_flag("include_bess", True)


def apply_architecture_profile(config: dict, structure: str) -> dict:
    """Apply saved per-architecture edits (mix %, assets, commercial) then set structure.

    Used by architecture comparison so each column uses that architecture's user-saved
    profile from ``config["_architecture_memory"]``, not only the currently selected structure.
    Shared Setup values (load, solar capacity, tariffs, etc.) remain from the project config.
    """
    structure = str(structure or "HYBRID")
    commercial = config.get("commercial")
    if not isinstance(commercial, dict):
        return config

    mem = config.get("_architecture_memory")
    snap = mem.get(structure) if isinstance(mem, dict) else None
    if isinstance(snap, dict) and snap:
        for key, saved in snap.items():
            p = commercial.get(key)
            if not isinstance(p, dict) or "value" not in p:
                continue
            if isinstance(saved, dict) and "value" in saved:
                p["value"] = saved["value"]
                if saved.get("source"):
                    p["source"] = saved["source"]
            else:
                p["value"] = saved
    else:
        _apply_first_time_structure_includes(commercial, structure)

    structure_p = commercial.get("structure")
    if isinstance(structure_p, dict) and "value" in structure_p:
        structure_p["value"] = structure

    _normalize_architecture_flags(config)
    ensure_architecture_mix_sums_to_100(config)
    return config


'''
        text = text.replace(
            "\ndef merge_missing_defaults(config: dict) -> dict:",
            "\n" + arch_helpers + "def merge_missing_defaults(config: dict) -> dict:",
            1,
        )

    # CAPTIVE also forces solar/wind/bess on in normalize
    if 'elif structure == "CAPTIVE":\n        # Captive: Solar / Wind / BESS only' in text and 'set_flag("include_solar", True)' not in text.split('elif structure == "CAPTIVE":')[1][:400]:
        text = text.replace(
            '''    elif structure == "CAPTIVE":
        # Captive: Solar / Wind / BESS only — DISCOM is not an option
        set_flag("include_discom", False)


def ''',
            '''    elif structure == "CAPTIVE":
        # Captive: Solar / Wind / BESS only — DISCOM is not an option
        set_flag("include_discom", False)
        set_flag("include_solar", True)
        set_flag("include_wind", True)
        set_flag("include_bess", True)


def ''',
            1,
        )

    # CRITICAL paths update if present
    text = text.replace(
        '"compliance.rpo_applicability"',
        '"compliance.rpo_rco_applicability"',
    )
    text = text.replace(
        '"compliance.rco_applicability"',
        '"compliance.eso_applicability"',
    )

    CFG.write_text(text, encoding="utf-8", newline="\n")
    print("wrote", CFG, "bytes", CFG.stat().st_size)


if __name__ == "__main__":
    main()
