"""Central default configuration for PowerTrain Optimizer.

Every numeric/text assumption lives here. Nothing required by the model
should be hard-coded in simulation or UI modules.

Source tags:
  CONCEPT_NOTE         — stated in the Design Concept Note
  DEFAULT_ASSUMPTION   — required to run the model; not a source-document fact
  USER_INPUT           — replaced by the user
  CALCULATED           — derived from other parameters
"""

from __future__ import annotations

from copy import deepcopy

MODEL_VERSION = "2.0.0"

CONCEPT_NOTE = "CONCEPT_NOTE"
DEFAULT_ASSUMPTION = "DEFAULT_ASSUMPTION"
USER_INPUT = "USER_INPUT"
CALCULATED = "CALCULATED"

DISCLAIMER = (
    "This model is a decision-support tool. Regulatory applicability, legal "
    "interpretation, commercial eligibility and final compliance requirements "
    "should be independently validated by the appropriate legal, regulatory "
    "and commercial advisors."
)

LEGAL_REVIEW = "LEGAL REVIEW REQUIRED"
APPLICABILITY_BANNER = (
    "Legal/regulatory applicability requires validation. The concept note "
    "raises whether a Data Centre SPV with a 220 kV connection and the "
    "chosen electricity procurement structure qualifies as a Designated "
    "Consumer for RCO purposes. This application does not determine that."
)


def P(
    value,
    unit: str,
    source: str,
    description: str,
    editable: bool = True,
    kind: str = "number",
    options: list | None = None,
    minimum=None,
    maximum=None,
    step=None,
):
    return {
        "value": value,
        "unit": unit,
        "source": source,
        "description": description,
        "editable": editable,
        "kind": kind,
        "options": options or [],
        "minimum": minimum,
        "maximum": maximum,
        "step": step,
    }


DEFAULT_CONFIG = {
    "general": {
        "project_name": P(
            "Default Data Centre - 250 MW",
            "",
            DEFAULT_ASSUMPTION,
            "Display name for the demonstration project.",
            kind="text",
        ),
        "location": P(
            "Maharashtra",
            "",
            DEFAULT_ASSUMPTION,
            "Site location used only as a label. DISCOM naming in the concept note references MSEDCL.",
            kind="text",
        ),
        "currency": P(
            "INR",
            "",
            DEFAULT_ASSUMPTION,
            "Reporting currency. UI may display ₹ for INR.",
            kind="select",
            options=["INR", "USD", "EUR"],
        ),
        "model_hours": P(
            8760,
            "h",
            CONCEPT_NOTE,
            "Normal-year hourly resolution required by the concept note. Leap years are not modelled in v1.",
            editable=False,
            kind="integer",
        ),
        "calendar_year": P(
            2026,
            "",
            DEFAULT_ASSUMPTION,
            "Study year shown as 01 Jan – 31 Dec in the top bar. Choose any year 2020–2100. "
            "The hourly engine still runs 8,760 non-leap hours (29 Feb is not modelled).",
            kind="integer",
            minimum=2020,
            maximum=2100,
        ),
        "re_curtailment_scope": P(
            "Solar + Wind",
            "",
            DEFAULT_ASSUMPTION,
            "Which renewable generation the curtailment % applies to: Solar only, Wind only, or Solar + Wind.",
            kind="select",
            options=["Solar + Wind", "Solar only", "Wind only"],
        ),
        "re_curtailment_pct": P(
            0.0,
            "% of RE",
            DEFAULT_ASSUMPTION,
            "Assumed / forced curtailment as a percentage of the selected RE scope (see RE curtailment scope). "
            "That share is removed before serving load or charging BESS. Additional curtailment can still "
            "occur if leftover RE cannot be absorbed. Editable input — not only a calculated KPI.",
            minimum=0,
            maximum=100,
            step=0.1,
        ),
        "random_seed": P(
            42,
            "",
            DEFAULT_ASSUMPTION,
            "Deterministic seed for synthetic solar/wind variability.",
            kind="integer",
        ),
        "notes": P(
            "",
            "",
            DEFAULT_ASSUMPTION,
            "Free-text project notes.",
            kind="text",
        ),
    },
    "data_center": {
        "facility_name": P(
            "Default Data Centre - 250 MW",
            "",
            DEFAULT_ASSUMPTION,
            "Facility name for reports.",
            kind="text",
        ),
        "it_capacity_mw": P(
            250.0,
            "MW",
            DEFAULT_ASSUMPTION,
            "Nameplate IT capacity used to label the default project.",
            minimum=0,
            step=1,
        ),
        "grid_connection_kv": P(
            220.0,
            "kV",
            CONCEPT_NOTE,
            "Grid connection voltage stated in the concept note.",
            minimum=0,
            step=1,
        ),
        "designated_consumer_status": P(
            "Unknown / Legal Review Required",
            "",
            CONCEPT_NOTE,
            "RCO designated-consumer status is not determined by this model. Concept note flags 220 kV SPV structure for legal review.",
            kind="select",
            options=["Applicable", "Not Applicable", "Unknown / Legal Review Required"],
        ),
    },
    "load": {
        "profile_source": P(
            "SYNTHETIC",
            "",
            DEFAULT_ASSUMPTION,
            "SYNTHETIC = parameterized generator. PROJECT DATA = imported 8,760 hourly MW series (optional).",
            kind="select",
            options=["SYNTHETIC", "PROJECT DATA"],
        ),
        "peak_load_mw": P(
            250.0,
            "MW",
            DEFAULT_ASSUMPTION,
            "Peak data-centre demand used to generate the 8,760 profile.",
            minimum=0.01,
            step=0.1,
        ),
        "load_factor_pct": P(
            80.0,
            "%",
            DEFAULT_ASSUMPTION,
            "Target annual load factor. Actual realised load factor is calculated from the generated profile.",
            minimum=1,
            maximum=100,
            step=0.1,
        ),
        "base_load_mw": P(
            200.0,
            "MW",
            CALCULATED,
            "peak_load_mw × load_factor_pct / 100 for the default flat interpretation. Recalculated on edit.",
            editable=False,
        ),
        "operating_hours": P(
            8760,
            "h",
            DEFAULT_ASSUMPTION,
            "Hours the load is considered online. Profile still has 8,760 steps; unused hours are zero if < 8760.",
            minimum=1,
            maximum=8760,
            kind="integer",
        ),
        "load_model": P(
            "Custom Parameterized",
            "",
            DEFAULT_ASSUMPTION,
            "How the 8,760-hour load shape is generated.",
            kind="select",
            options=["Flat", "Daily Pattern", "Weekday/Weekend", "Seasonal", "Custom Parameterized"],
        ),
        "weekday_multiplier": P(
            1.0,
            "x",
            DEFAULT_ASSUMPTION,
            "Weekday (Mon–Fri) shape multiplier before load-factor scaling.",
            minimum=0,
            step=0.01,
        ),
        "weekend_multiplier": P(
            0.98,
            "x",
            DEFAULT_ASSUMPTION,
            "Weekend shape multiplier before load-factor scaling.",
            minimum=0,
            step=0.01,
        ),
        "growth_rate_pct": P(
            0.0,
            "%/yr",
            DEFAULT_ASSUMPTION,
            "Not applied inside a single 8,760-hour year. Reserved for multi-year cash-flow load growth.",
            step=0.1,
        ),
        "study_years": P(
            1,
            "yr",
            DEFAULT_ASSUMPTION,
            "Hourly engine always runs one 8,760-hour year. Financial model uses project life separately.",
            kind="integer",
            minimum=1,
            maximum=1,
            editable=False,
        ),
        "month_multiplier_1": P(1.00, "x", DEFAULT_ASSUMPTION, "January load-shape multiplier.", minimum=0, step=0.01),
        "month_multiplier_2": P(1.00, "x", DEFAULT_ASSUMPTION, "February load-shape multiplier.", minimum=0, step=0.01),
        "month_multiplier_3": P(1.01, "x", DEFAULT_ASSUMPTION, "March load-shape multiplier.", minimum=0, step=0.01),
        "month_multiplier_4": P(1.02, "x", DEFAULT_ASSUMPTION, "April load-shape multiplier.", minimum=0, step=0.01),
        "month_multiplier_5": P(1.03, "x", DEFAULT_ASSUMPTION, "May load-shape multiplier.", minimum=0, step=0.01),
        "month_multiplier_6": P(1.03, "x", DEFAULT_ASSUMPTION, "June load-shape multiplier.", minimum=0, step=0.01),
        "month_multiplier_7": P(1.02, "x", DEFAULT_ASSUMPTION, "July load-shape multiplier.", minimum=0, step=0.01),
        "month_multiplier_8": P(1.02, "x", DEFAULT_ASSUMPTION, "August load-shape multiplier.", minimum=0, step=0.01),
        "month_multiplier_9": P(1.01, "x", DEFAULT_ASSUMPTION, "September load-shape multiplier.", minimum=0, step=0.01),
        "month_multiplier_10": P(1.00, "x", DEFAULT_ASSUMPTION, "October load-shape multiplier.", minimum=0, step=0.01),
        "month_multiplier_11": P(0.99, "x", DEFAULT_ASSUMPTION, "November load-shape multiplier.", minimum=0, step=0.01),
        "month_multiplier_12": P(0.98, "x", DEFAULT_ASSUMPTION, "December load-shape multiplier.", minimum=0, step=0.01),
        **{
            f"hour_multiplier_{h}": P(
                v,
                "x",
                DEFAULT_ASSUMPTION,
                f"Hour {h:02d}:00–{h:02d}:59 diurnal multiplier before scaling.",
                minimum=0,
                step=0.01,
            )
            for h, v in enumerate(
                [
                    0.94, 0.93, 0.92, 0.92, 0.93, 0.95,
                    0.98, 1.02, 1.05, 1.06, 1.06, 1.05,
                    1.04, 1.05, 1.06, 1.06, 1.07, 1.08,
                    1.06, 1.02, 0.98, 0.96, 0.95, 0.94,
                ]
            )
        },
    },
    "solar": {
        "profile_source": P(
            "SYNTHETIC",
            "",
            DEFAULT_ASSUMPTION,
            "SYNTHETIC = CF/diurnal generator. PROJECT DATA = imported 8,760 hourly MW series (optional).",
            kind="select",
            options=["SYNTHETIC", "PROJECT DATA"],
        ),
        "capacity_mw": P(450.0, "MW", DEFAULT_ASSUMPTION, "Installed solar AC capacity.", minimum=0, step=1),
        "capacity_factor_pct": P(22.0, "%", DEFAULT_ASSUMPTION, "Target annual capacity factor used to scale the synthetic profile.", minimum=0, maximum=80, step=0.1),
        "sunrise_hour": P(6.0, "h", DEFAULT_ASSUMPTION, "Hour of day (0–24) at which generation becomes non-zero.", minimum=0, maximum=12, step=0.5),
        "sunset_hour": P(18.0, "h", DEFAULT_ASSUMPTION, "Hour of day at which generation returns to zero.", minimum=12, maximum=24, step=0.5),
        "peak_generation_hour": P(12.0, "h", DEFAULT_ASSUMPTION, "Hour of day of the diurnal peak.", minimum=0, maximum=24, step=0.5),
        "hourly_variability": P(0.12, "frac", DEFAULT_ASSUMPTION, "Deterministic relative noise amplitude applied in daylight hours.", minimum=0, maximum=1, step=0.01),
        "degradation_pct": P(0.50, "%/yr", DEFAULT_ASSUMPTION, "Annual generation degradation applied in the financial years after year 1.", minimum=0, step=0.05),
        "project_life_yr": P(25, "yr", DEFAULT_ASSUMPTION, "Solar asset life for annualisation.", kind="integer", minimum=1, maximum=40),
        "capex_inr_per_mw": P(45_000_000.0, "₹/MW", DEFAULT_ASSUMPTION, "Solar overnight CAPEX."),
        "opex_inr_per_mw_year": P(600_000.0, "₹/MW-yr", DEFAULT_ASSUMPTION, "Solar fixed OPEX."),
        "energy_cost_inr_per_kwh": P(2.50, "₹/kWh", DEFAULT_ASSUMPTION, "Contracted solar energy price when the commercial structure uses an energy tariff rather than CAPEX recovery."),
        "seasonal_winter": P(
            0.80,
            "x",
            DEFAULT_ASSUMPTION,
            "Solar seasonal factor for Winter (Dec–Feb).",
            minimum=0,
            step=0.01,
        ),
        "seasonal_summer": P(
            1.11,
            "x",
            DEFAULT_ASSUMPTION,
            "Solar seasonal factor for Summer (Mar–May).",
            minimum=0,
            step=0.01,
        ),
        "seasonal_monsoon": P(
            0.96,
            "x",
            DEFAULT_ASSUMPTION,
            "Solar seasonal factor for Monsoon (Jun–Sep).",
            minimum=0,
            step=0.01,
        ),
        "seasonal_post_monsoon": P(
            0.98,
            "x",
            DEFAULT_ASSUMPTION,
            "Solar seasonal factor for Post-monsoon (Oct–Nov).",
            minimum=0,
            step=0.01,
        ),
    },
    "wind": {
        "profile_source": P(
            "SYNTHETIC",
            "",
            DEFAULT_ASSUMPTION,
            "SYNTHETIC = CF/seasonal generator. PROJECT DATA = imported 8,760 hourly MW series (optional).",
            kind="select",
            options=["SYNTHETIC", "PROJECT DATA"],
        ),
        "capacity_mw": P(300.0, "MW", DEFAULT_ASSUMPTION, "Installed wind AC capacity.", minimum=0, step=1),
        "capacity_factor_pct": P(32.0, "%", DEFAULT_ASSUMPTION, "Target annual capacity factor used to scale the synthetic profile.", minimum=0, maximum=80, step=0.1),
        "hourly_variability": P(0.28, "frac", DEFAULT_ASSUMPTION, "Deterministic relative noise amplitude for hourly wind.", minimum=0, maximum=1, step=0.01),
        "degradation_pct": P(0.25, "%/yr", DEFAULT_ASSUMPTION, "Annual wind degradation applied after year 1.", minimum=0, step=0.05),
        "project_life_yr": P(25, "yr", DEFAULT_ASSUMPTION, "Wind asset life for annualisation.", kind="integer", minimum=1, maximum=40),
        "capex_inr_per_mw": P(65_000_000.0, "₹/MW", DEFAULT_ASSUMPTION, "Wind overnight CAPEX."),
        "opex_inr_per_mw_year": P(1_200_000.0, "₹/MW-yr", DEFAULT_ASSUMPTION, "Wind fixed OPEX."),
        "energy_cost_inr_per_kwh": P(3.20, "₹/kWh", DEFAULT_ASSUMPTION, "Contracted wind energy price when used as a tariff."),
        "seasonal_winter": P(
            0.72,
            "x",
            DEFAULT_ASSUMPTION,
            "Wind seasonal factor for Winter (Dec–Feb).",
            minimum=0,
            step=0.01,
        ),
        "seasonal_summer": P(
            0.95,
            "x",
            DEFAULT_ASSUMPTION,
            "Wind seasonal factor for Summer (Mar–May).",
            minimum=0,
            step=0.01,
        ),
        "seasonal_monsoon": P(
            1.28,
            "x",
            DEFAULT_ASSUMPTION,
            "Wind seasonal factor for Monsoon (Jun–Sep).",
            minimum=0,
            step=0.01,
        ),
        "seasonal_post_monsoon": P(
            0.83,
            "x",
            DEFAULT_ASSUMPTION,
            "Wind seasonal factor for Post-monsoon (Oct–Nov).",
            minimum=0,
            step=0.01,
        ),
    },
    "bess": {
        "power_mw": P(
            150.0,
            "MW",
            DEFAULT_ASSUMPTION,
            "BESS power rating — used as both maximum charge and discharge power.",
            minimum=0,
            step=1,
        ),
        "energy_mwh": P(600.0, "MWh", DEFAULT_ASSUMPTION, "Usable energy capacity at 100% SOC window before min/max SOC.", minimum=0, step=1),
        "initial_soc_pct": P(50.0, "%", DEFAULT_ASSUMPTION, "Starting state of charge.", minimum=0, maximum=100, step=1),
        "min_soc_pct": P(10.0, "%", DEFAULT_ASSUMPTION, "Lower SOC bound.", minimum=0, maximum=100, step=1),
        "max_soc_pct": P(95.0, "%", DEFAULT_ASSUMPTION, "Upper SOC bound.", minimum=0, maximum=100, step=1),
        "calendar_degradation_pct": P(2.0, "%/yr", DEFAULT_ASSUMPTION, "Calendar fade used in multi-year energy availability."),
        "cycle_degradation_pct": P(0.005, "%/cycle", DEFAULT_ASSUMPTION, "Throughput fade per equivalent full cycle."),
        "capex_inr_per_mw": P(5_000_000.0, "₹/MW", DEFAULT_ASSUMPTION, "Power-side BESS CAPEX."),
        "capex_inr_per_mwh": P(18_000_000.0, "₹/MWh", DEFAULT_ASSUMPTION, "Energy-side BESS CAPEX."),
        "opex_inr_per_year": P(12_900_000.0, "₹/yr", DEFAULT_ASSUMPTION, "Annual BESS O&M. Default ≈ 2% of power-side CAPEX for the 150 MW default."),
        "project_life_yr": P(15, "yr", DEFAULT_ASSUMPTION, "BESS operating life before replacement.", kind="integer", minimum=1),
        "replacement_year": P(15, "yr", DEFAULT_ASSUMPTION, "Year in which replacement CAPEX is incurred (1-indexed).", kind="integer", minimum=1),
        "replacement_cost_pct": P(70.0, "%", DEFAULT_ASSUMPTION, "Replacement cost as % of initial BESS CAPEX."),
        "allow_grid_charge": P(False, "", DEFAULT_ASSUMPTION, "If true, residual grid energy may charge BESS after serving load.", kind="boolean"),
    },
    "grid": {
        "connection_voltage_kv": P(220.0, "kV", CONCEPT_NOTE, "Grid interconnection voltage from the concept note."),
        "max_import_mw": P(250.0, "MW", DEFAULT_ASSUMPTION, "Maximum grid import capacity in any hour."),
        "energy_tariff_inr_per_kwh": P(8.50, "₹/kWh", DEFAULT_ASSUMPTION, "Flat energy tariff if time-of-day is disabled."),
        "use_tod": P(True, "", DEFAULT_ASSUMPTION, "Apply peak/off-peak energy tariffs.", kind="boolean"),
        "tod_peak_start_hour": P(18, "h", DEFAULT_ASSUMPTION, "Start of peak TOD window.", kind="integer", minimum=0, maximum=23),
        "tod_peak_end_hour": P(22, "h", DEFAULT_ASSUMPTION, "End of peak TOD window (exclusive).", kind="integer", minimum=1, maximum=24),
        "tod_peak_tariff": P(11.00, "₹/kWh", DEFAULT_ASSUMPTION, "Peak-window energy tariff."),
        "tod_offpeak_tariff": P(7.50, "₹/kWh", DEFAULT_ASSUMPTION, "Off-peak energy tariff."),
        "demand_charge_inr_per_mw_month": P(400_000.0, "₹/MW-month", DEFAULT_ASSUMPTION, "Applied to the annual peak grid import."),
        "fixed_charge_inr_per_year": P(12_000_000.0, "₹/yr", DEFAULT_ASSUMPTION, "Annual fixed grid/connection charge."),
        "transmission_inr_per_kwh": P(
            0.40,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "DISCOM / grid import transmission charge. Used when Network charges on grid is True.",
        ),
        "wheeling_inr_per_kwh": P(
            0.30,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "DISCOM / grid import wheeling charge. Used when Network charges on grid is True.",
        ),
        "banking_inr_per_kwh": P(0.10, "₹/kWh", DEFAULT_ASSUMPTION, "Legacy banking unit rate (kept for Grid tab). RE banking uses commercial.re_banking_inr_per_kwh."),
        "other_charges_inr_per_kwh": P(
            0.15,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "DISCOM / grid import other volumetric charges. Used when Network charges on grid is True.",
        ),
        "loss_pct": P(3.0, "%", DEFAULT_ASSUMPTION, "Grid/network loss applied to wheeled RE in captive/OA structures."),
        "availability_pct": P(99.5, "%", DEFAULT_ASSUMPTION, "Deterministic availability: first (1-a)×8760 hours of each year are scaled; implemented as a constant derate of max import."),
        "tariff_escalation_pct": P(4.0, "%/yr", DEFAULT_ASSUMPTION, "Grid tariff escalation in the financial model."),
        "banking_enabled": P(False, "", DEFAULT_ASSUMPTION, "Legacy Grid-tab banking switch. RE banking uses commercial.re_banking_enabled.", kind="boolean"),
    },
    "commercial": {
        "structure": P(
            "HYBRID",
            "",
            CONCEPT_NOTE,
            "Selected commercial structure. Hybrid is the primary optimisation architecture in the concept note.",
            kind="select",
            options=["DISCOM", "CAPTIVE", "HYBRID", "OPEN_ACCESS"],
        ),
        "include_discom": P(
            True,
            "",
            DEFAULT_ASSUMPTION,
            "Include DISCOM / grid supply in this architecture. For DISCOM structure this is always on. "
            "Selectable for HYBRID and OPEN ACCESS.",
            kind="boolean",
        ),
        "include_solar": P(
            True,
            "",
            DEFAULT_ASSUMPTION,
            "Include solar generation. Selectable for CAPTIVE, HYBRID and OPEN ACCESS. Off for DISCOM.",
            kind="boolean",
        ),
        "include_wind": P(
            True,
            "",
            DEFAULT_ASSUMPTION,
            "Include wind generation. Selectable for CAPTIVE, HYBRID and OPEN ACCESS. Off for DISCOM.",
            kind="boolean",
        ),
        "include_bess": P(
            True,
            "",
            DEFAULT_ASSUMPTION,
            "Include BESS. Selectable for CAPTIVE, HYBRID and OPEN ACCESS. Off for DISCOM.",
            kind="boolean",
        ),
        "discom_name": P("MSEDCL", "", CONCEPT_NOTE, "DISCOM counterparty name referenced in the concept note DISCOM structure.", kind="text"),
        "captive_ownership_pct": P(26.0, "%", DEFAULT_ASSUMPTION, "Captive ownership share. Not a legal qualification test."),
        "captive_allocation_pct": P(100.0, "%", DEFAULT_ASSUMPTION, "Share of RE project output allocated to this data centre."),
        "captive_energy_price": P(3.80, "₹/kWh", DEFAULT_ASSUMPTION, "Captive delivered energy price before network charges."),
        "oa_energy_price": P(4.20, "₹/kWh", DEFAULT_ASSUMPTION, "Open-access RE energy price before OA charges."),
        "include_generation_capex": P(
            True,
            "",
            DEFAULT_ASSUMPTION,
            "If true, solar/wind/BESS CAPEX enters the cash-flow (typical for hybrid ownership). If false, generation is treated as a tariff (typical for some OA/captive contracts).",
            kind="boolean",
        ),
        "apply_network_charges_to_re": P(
            True,
            "",
            DEFAULT_ASSUMPTION,
            "Legacy combined RE network flag (migrated into Solar / Wind flags). Kept for older projects.",
            kind="boolean",
        ),
        "apply_network_charges_to_solar": P(
            True,
            "",
            DEFAULT_ASSUMPTION,
            "Apply Solar-specific transmission/wheeling/banking/other charges to annual solar generation.",
            kind="boolean",
        ),
        "apply_network_charges_to_wind": P(
            True,
            "",
            DEFAULT_ASSUMPTION,
            "Apply Wind-specific transmission/wheeling/banking/other charges to annual wind generation.",
            kind="boolean",
        ),
        "apply_network_charges_to_bess": P(
            True,
            "",
            DEFAULT_ASSUMPTION,
            "Apply BESS-specific transmission/wheeling/banking/other charges to annual BESS discharge energy.",
            kind="boolean",
        ),
        "apply_network_charges_to_grid": P(
            False,
            "",
            DEFAULT_ASSUMPTION,
            "Apply DISCOM/grid-specific transmission/wheeling/other charges to grid import in addition to the energy tariff.",
            kind="boolean",
        ),
        "re_transmission_inr_per_kwh": P(
            0.40,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "Legacy combined RE transmission rate (migrated into Solar / Wind rates).",
        ),
        "re_wheeling_inr_per_kwh": P(0.30, "₹/kWh", DEFAULT_ASSUMPTION, "Legacy combined RE wheeling rate."),
        "re_other_charges_inr_per_kwh": P(0.15, "₹/kWh", DEFAULT_ASSUMPTION, "Legacy combined RE other volumetric rate."),
        "re_banking_enabled": P(False, "", DEFAULT_ASSUMPTION, "Legacy combined RE banking switch.", kind="boolean"),
        "re_banking_inr_per_kwh": P(0.10, "₹/kWh", DEFAULT_ASSUMPTION, "Legacy combined RE banking rate."),
        "solar_transmission_inr_per_kwh": P(
            0.40,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "Solar network transmission charge. Independent of Wind and DISCOM rates.",
        ),
        "solar_wheeling_inr_per_kwh": P(
            0.30,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "Solar network wheeling charge. Independent of Wind and DISCOM rates.",
        ),
        "solar_other_charges_inr_per_kwh": P(
            0.15,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "Solar other volumetric network charges.",
        ),
        "solar_banking_enabled": P(
            False,
            "",
            DEFAULT_ASSUMPTION,
            "If false, Solar banking charges are zero regardless of the Solar banking unit rate.",
            kind="boolean",
        ),
        "solar_banking_inr_per_kwh": P(
            0.10,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "Solar banking-related charge. Applied only when Solar banking is enabled.",
        ),
        "wind_transmission_inr_per_kwh": P(
            0.40,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "Wind network transmission charge. Independent of Solar and DISCOM rates.",
        ),
        "wind_wheeling_inr_per_kwh": P(
            0.30,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "Wind network wheeling charge. Independent of Solar and DISCOM rates.",
        ),
        "wind_other_charges_inr_per_kwh": P(
            0.15,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "Wind other volumetric network charges.",
        ),
        "wind_banking_enabled": P(
            False,
            "",
            DEFAULT_ASSUMPTION,
            "If false, Wind banking charges are zero regardless of the Wind banking unit rate.",
            kind="boolean",
        ),
        "wind_banking_inr_per_kwh": P(
            0.10,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "Wind banking-related charge. Applied only when Wind banking is enabled.",
        ),
        "bess_transmission_inr_per_kwh": P(
            0.40,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "BESS network transmission charge on discharge energy. Independent of Solar / Wind / DISCOM rates.",
        ),
        "bess_wheeling_inr_per_kwh": P(
            0.30,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "BESS network wheeling charge on discharge energy.",
        ),
        "bess_other_charges_inr_per_kwh": P(
            0.15,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "BESS other volumetric network charges on discharge energy.",
        ),
        "bess_banking_enabled": P(
            False,
            "",
            DEFAULT_ASSUMPTION,
            "If false, BESS banking charges are zero regardless of the BESS banking unit rate.",
            kind="boolean",
        ),
        "bess_banking_inr_per_kwh": P(
            0.10,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "BESS banking-related charge. Applied only when BESS banking is enabled.",
        ),
    },
    "compliance": {
        "rpo_applicability": P(
            "Unknown / Legal Review Required",
            "",
            CONCEPT_NOTE,
            "RPO applicability is user-declared. The model does not infer it.",
            kind="select",
            options=["Applicable", "Not Applicable", "Unknown / Legal Review Required"],
        ),
        "rpo_solar_target_pct": P(0.0, "%", DEFAULT_ASSUMPTION, "Solar RPO target. The concept note does not state a numeric RPO split."),
        "rpo_wind_target_pct": P(0.0, "%", DEFAULT_ASSUMPTION, "Wind RPO target. The concept note does not state a numeric RPO split."),
        "rpo_hydro_target_pct": P(0.0, "%", DEFAULT_ASSUMPTION, "Hydro RPO target."),
        "rpo_other_target_pct": P(0.0, "%", DEFAULT_ASSUMPTION, "Other-renewable RPO target."),
        "rpo_buyout_inr_per_kwh": P(1.00, "₹/kWh", DEFAULT_ASSUMPTION, "RPO shortfall cost if applicability is Applicable."),
        "rco_applicability": P(
            "Unknown / Legal Review Required",
            "",
            CONCEPT_NOTE,
            "RCO designated-consumer applicability requires legal review (220 kV SPV structure).",
            kind="select",
            options=["Applicable", "Not Applicable", "Unknown / Legal Review Required"],
        ),
        "rco_target_pct": P(0.0, "%", DEFAULT_ASSUMPTION, "RCO target %. The concept note does not state a numeric RCO obligation."),
        "rco_compliance_route": P("Unknown", "", DEFAULT_ASSUMPTION, "Intended compliance route.", kind="select", options=["Unknown", "Self-generation", "REC", "Buyout", "Other"]),
        "rco_buyout_inr_per_kwh": P(1.50, "₹/kWh", DEFAULT_ASSUMPTION, "RCO buyout / alternative compliance cost."),
        "rco_rec_inr_per_kwh": P(1.00, "₹/kWh", DEFAULT_ASSUMPTION, "REC cost if that route is selected."),
        "eso_applicability": P(
            "Unknown / Legal Review Required",
            "",
            CONCEPT_NOTE,
            "ESO applicability is user-declared. Trajectory values below come from the concept note.",
            kind="select",
            options=["Applicable", "Not Applicable", "Unknown / Legal Review Required"],
        ),
        "eso_fy2026_27_pct": P(2.5, "%", CONCEPT_NOTE, "ESO trajectory for FY2026-27 from the concept note."),
        "eso_fy2027_28_pct": P(3.0, "%", DEFAULT_ASSUMPTION, "Linear interpolation between 2.5% (FY26-27) and 4.0% (FY29-30)."),
        "eso_fy2028_29_pct": P(3.5, "%", DEFAULT_ASSUMPTION, "Linear interpolation between 2.5% (FY26-27) and 4.0% (FY29-30)."),
        "eso_fy2029_30_pct": P(4.0, "%", CONCEPT_NOTE, "ESO trajectory for FY2029-30 from the concept note."),
        "eso_active_year": P(
            "FY2026-27",
            "",
            DEFAULT_ASSUMPTION,
            "Which ESO year-target is used for the current 8,760-hour study.",
            kind="select",
            options=["FY2026-27", "FY2027-28", "FY2028-29", "FY2029-30"],
        ),
        "eso_re_origin_min_pct": P(
            85.0,
            "%",
            CONCEPT_NOTE,
            "Minimum renewable-origin share of stored energy under the ESO requirement.",
        ),
        "eso_buyout_inr_per_kwh": P(1.20, "₹/kWh", DEFAULT_ASSUMPTION, "ESO shortfall / origin-failure cost if applicable."),
        "annual_re_target_pct": P(90.0, "%", CONCEPT_NOTE, "Selected annual RE target. Concept note prepopulates 90 / 95 / 99."),
        "hourly_cfe_target_pct": P(90.0, "%", CONCEPT_NOTE, "Selected hourly CFE target. Concept note prepopulates 90 / 95 / 99 / 100."),
        "cfe_pass_mode": P(
            "All hours >= target",
            "",
            DEFAULT_ASSUMPTION,
            "Pass rule for hourly CFE. Strict 24×7 interpretation: every hour's CFE must be at least the target.",
            kind="select",
            options=["All hours >= target", "Mean hourly CFE >= target", "Share of hours >= target"],
        ),
        "cfe_hour_share_target_pct": P(100.0, "%", DEFAULT_ASSUMPTION, "Used only when pass mode is 'Share of hours >= target'."),
    },
    "financial": {
        "project_life_yr": P(25, "yr", DEFAULT_ASSUMPTION, "Cash-flow horizon.", kind="integer", minimum=1, maximum=40),
        "discount_rate_pct": P(10.0, "%", DEFAULT_ASSUMPTION, "Real/nominal discount rate applied to cash flows as entered (no separate real/nominal conversion)."),
        "inflation_pct": P(5.0, "%", DEFAULT_ASSUMPTION, "OPEX inflation."),
        "electricity_escalation_pct": P(4.0, "%", DEFAULT_ASSUMPTION, "Grid energy-cost escalation."),
        "re_cost_escalation_pct": P(2.0, "%", DEFAULT_ASSUMPTION, "RE tariff/OPEX escalation where billed as energy."),
        "residual_value_pct": P(10.0, "%", DEFAULT_ASSUMPTION, "Residual value of depreciable CAPEX at horizon, credited in the final year."),
        "tax_pct": P(0.0, "%", DEFAULT_ASSUMPTION, "Optional tax on taxable income. Default 0 (pre-tax)."),
        "financing_enabled": P(False, "", DEFAULT_ASSUMPTION, "If false, the model is 100% equity / cash CAPEX at t=0.", kind="boolean"),
        "debt_pct": P(70.0, "%", DEFAULT_ASSUMPTION, "Debt share of CAPEX if financing is enabled."),
        "interest_rate_pct": P(9.0, "%", DEFAULT_ASSUMPTION, "Interest on outstanding debt."),
        "debt_tenor_yr": P(15, "yr", DEFAULT_ASSUMPTION, "Sculpted as equal principal + interest on outstanding.", kind="integer"),
        "additional_costs": P(
            [],
            "₹/yr",
            DEFAULT_ASSUMPTION,
            "User-defined additional annual cost line items (label + amount). Included in delivered ₹/kWh and cashflows.",
            kind="list",
        ),
    },
    "optimization": {
        "objective": P(
            "Minimum Cost",
            "",
            CONCEPT_NOTE,
            "Primary objective. Concept note states lowest electricity cost, subject to RE/CFE/compliance constraints.",
            kind="select",
            options=["Minimum Cost", "Maximum RE", "Maximum CFE", "Minimum Grid Dependency", "Compliance First", "Balanced"],
        ),
        "dispatch_mode": P(
            "Rule-Based",
            "",
            DEFAULT_ASSUMPTION,
            "Hourly BESS/grid dispatch method.",
            kind="select",
            options=["Rule-Based", "LP Dispatch"],
        ),
        "search_mode": P(
            "Standard",
            "",
            DEFAULT_ASSUMPTION,
            "Capacity search effort. Thorough evaluates more candidates.",
            kind="select",
            options=["Quick", "Standard", "Thorough"],
        ),
        "solar_min_mw": P(0.0, "MW", DEFAULT_ASSUMPTION, "Lower bound for solar capacity search."),
        "solar_max_mw": P(750.0, "MW", DEFAULT_ASSUMPTION, "Upper bound for solar capacity search."),
        "solar_step_mw": P(25.0, "MW", DEFAULT_ASSUMPTION, "Solar search step."),
        "wind_min_mw": P(0.0, "MW", DEFAULT_ASSUMPTION, "Lower bound for wind capacity search."),
        "wind_max_mw": P(750.0, "MW", DEFAULT_ASSUMPTION, "Upper bound for wind capacity search."),
        "wind_step_mw": P(25.0, "MW", DEFAULT_ASSUMPTION, "Wind search step."),
        "bess_power_min_mw": P(0.0, "MW", DEFAULT_ASSUMPTION, "Lower bound for BESS power."),
        "bess_power_max_mw": P(400.0, "MW", DEFAULT_ASSUMPTION, "Upper bound for BESS power."),
        "bess_energy_min_mwh": P(0.0, "MWh", DEFAULT_ASSUMPTION, "Lower bound for BESS energy."),
        "bess_energy_max_mwh": P(2000.0, "MWh", DEFAULT_ASSUMPTION, "Upper bound for BESS energy."),
        "grid_min_mw": P(0.0, "MW", DEFAULT_ASSUMPTION, "Lower bound for grid import capacity."),
        "grid_max_mw": P(400.0, "MW", DEFAULT_ASSUMPTION, "Upper bound for grid import capacity."),
        "enforce_re_target": P(True, "", DEFAULT_ASSUMPTION, "Treat annual RE target as a feasibility constraint.", kind="boolean"),
        "enforce_cfe_target": P(False, "", DEFAULT_ASSUMPTION, "Treat hourly CFE pass rule as a feasibility constraint. Default off because strict 24×7 CFE is demanding; enable after sizing BESS.", kind="boolean"),
        "enforce_no_unserved": P(True, "", DEFAULT_ASSUMPTION, "Require unserved energy ≈ 0.", kind="boolean"),
        "weight_cost": P(0.40, "w", DEFAULT_ASSUMPTION, "Balanced-objective weight on cost (lower is better)."),
        "weight_re": P(0.25, "w", DEFAULT_ASSUMPTION, "Balanced-objective weight on annual RE."),
        "weight_cfe": P(0.25, "w", DEFAULT_ASSUMPTION, "Balanced-objective weight on hourly CFE."),
        "weight_grid": P(0.10, "w", DEFAULT_ASSUMPTION, "Balanced-objective weight on reducing grid energy."),
        "priority_1": P("RE to load", "", DEFAULT_ASSUMPTION, "Dispatch priority 1.", kind="select", options=["RE to load"]),
        "priority_2": P("Excess RE charges BESS", "", DEFAULT_ASSUMPTION, "Dispatch priority 2.", kind="select", options=["Excess RE charges BESS"]),
        "priority_3": P("Curtail remaining RE", "", DEFAULT_ASSUMPTION, "Dispatch priority 3.", kind="select", options=["Curtail remaining RE"]),
        "priority_4": P("BESS discharges on deficit", "", DEFAULT_ASSUMPTION, "Dispatch priority 4.", kind="select", options=["BESS discharges on deficit"]),
        "priority_5": P("Grid serves residual", "", DEFAULT_ASSUMPTION, "Dispatch priority 5.", kind="select", options=["Grid serves residual"]),
    },
}

PRESET_RE_TARGETS = [90.0, 95.0, 99.0]
PRESET_CFE_TARGETS = [90.0, 95.0, 99.0, 100.0]

DEFAULT_SCENARIOS = []  # Architecture is chosen in Project Setup — do not seed structure presets here


def get_default_config():
    return deepcopy(DEFAULT_CONFIG)


def iter_params(config: dict, prefix: str = ""):
    for key, val in config.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(val, dict) and "value" in val and "source" in val:
            yield path, val
        elif isinstance(val, dict):
            yield from iter_params(val, path)


def set_param(config: dict, dotted: str, value, as_user: bool = True):
    parts = dotted.split(".")
    node = config
    for p in parts[:-1]:
        node = node[p]
    param = node[parts[-1]]
    param["value"] = value
    if as_user and param.get("editable", True) and param.get("source") != CALCULATED:
        param["source"] = USER_INPUT
    return config


def v(config: dict, dotted: str):
    node = config
    for p in dotted.split("."):
        node = node[p]
    return node["value"]


def recompute_calculated(config: dict) -> dict:
    peak = v(config, "load.peak_load_mw")
    lf = v(config, "load.load_factor_pct") / 100.0
    config["load"]["base_load_mw"]["value"] = round(peak * lf, 6)
    config["grid"]["connection_voltage_kv"]["value"] = v(config, "data_center.grid_connection_kv")
    return config


_OBSOLETE_BESS_KEYS = (
    "charge_efficiency_pct",
    "discharge_efficiency_pct",
    "round_trip_efficiency_pct",
    "max_charge_mw",
    "max_discharge_mw",
)


def _normalize_architecture_flags(config: dict) -> None:
    """Keep include_* flags consistent with commercial structure (UI + old projects)."""
    commercial = config.get("commercial")
    if not isinstance(commercial, dict):
        return
    structure_p = commercial.get("structure")
    structure = str(structure_p.get("value", "HYBRID")) if isinstance(structure_p, dict) else "HYBRID"

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
        # Captive: Solar / Wind / BESS only — DISCOM is not an option
        set_flag("include_discom", False)


def merge_missing_defaults(config: dict) -> dict:
    """Add any new default parameters missing from older saved projects."""
    _migrate_solar_wind_to_seasons(config)
    defaults = get_default_config()
    newly_added: list[tuple[str, str]] = []
    for section, params in defaults.items():
        if not isinstance(params, dict):
            continue
        if section not in config or not isinstance(config[section], dict):
            config[section] = deepcopy(params)
            continue
        for key, param in params.items():
            if key not in config[section]:
                config[section][key] = deepcopy(param)
                newly_added.append((section, key))
    # Drop retired BESS fields so they no longer appear in Setup / Assumptions
    bess = config.get("bess")
    if isinstance(bess, dict):
        for key in _OBSOLETE_BESS_KEYS:
            bess.pop(key, None)
    _seed_re_network_from_grid(config, newly_added)
    _seed_solar_wind_network_from_re(config, newly_added)
    _normalize_architecture_flags(config)
    return config


def _seed_re_network_from_grid(config: dict, newly_added: list[tuple[str, str]]) -> None:
    """When RE network rates are first introduced, copy prior Grid rates so behaviour is unchanged."""
    mapping = {
        "re_transmission_inr_per_kwh": "transmission_inr_per_kwh",
        "re_wheeling_inr_per_kwh": "wheeling_inr_per_kwh",
        "re_other_charges_inr_per_kwh": "other_charges_inr_per_kwh",
        "re_banking_inr_per_kwh": "banking_inr_per_kwh",
        "re_banking_enabled": "banking_enabled",
    }
    commercial = config.get("commercial")
    grid = config.get("grid")
    if not isinstance(commercial, dict) or not isinstance(grid, dict):
        return
    added = {k for sec, k in newly_added if sec == "commercial"}
    for re_key, grid_key in mapping.items():
        if re_key not in added:
            continue
        gp = grid.get(grid_key)
        rp = commercial.get(re_key)
        if isinstance(gp, dict) and "value" in gp and isinstance(rp, dict):
            rp["value"] = deepcopy(gp["value"])
            if gp.get("source"):
                rp["source"] = gp["source"]


def _seed_solar_wind_network_from_re(config: dict, newly_added: list[tuple[str, str]]) -> None:
    """Seed separate Solar/Wind network params from legacy combined RE network params."""
    commercial = config.get("commercial")
    if not isinstance(commercial, dict):
        return
    added = {k for sec, k in newly_added if sec == "commercial"}
    legacy_flag = commercial.get("apply_network_charges_to_re")
    legacy_map = {
        "transmission_inr_per_kwh": "re_transmission_inr_per_kwh",
        "wheeling_inr_per_kwh": "re_wheeling_inr_per_kwh",
        "other_charges_inr_per_kwh": "re_other_charges_inr_per_kwh",
        "banking_enabled": "re_banking_enabled",
        "banking_inr_per_kwh": "re_banking_inr_per_kwh",
    }
    for asset in ("solar", "wind", "bess"):
        flag_key = f"apply_network_charges_to_{asset}"
        if flag_key in added and isinstance(legacy_flag, dict) and "value" in legacy_flag:
            p = commercial.get(flag_key)
            if isinstance(p, dict):
                p["value"] = deepcopy(legacy_flag["value"])
                if legacy_flag.get("source"):
                    p["source"] = legacy_flag["source"]
        for suffix, legacy_key in legacy_map.items():
            new_key = f"{asset}_{suffix}"
            if new_key not in added:
                continue
            src = commercial.get(legacy_key)
            dst = commercial.get(new_key)
            if isinstance(src, dict) and "value" in src and isinstance(dst, dict):
                dst["value"] = deepcopy(src["value"])
                if src.get("source"):
                    dst["source"] = src["source"]


def _avg_month_values(section: dict, prefix: str, months_1based: list[int], fallback: float) -> float:
    vals = []
    for m in months_1based:
        key = f"{prefix}{m}"
        p = section.get(key)
        if isinstance(p, dict) and "value" in p:
            try:
                vals.append(float(p["value"]))
            except Exception:
                pass
    return round(sum(vals) / len(vals), 4) if vals else fallback


def _migrate_solar_wind_to_seasons(config: dict) -> None:
    """Replace legacy 12 monthly factors with 4 Indian seasonal factors on solar/wind."""
    season_defs = (
        ("seasonal_winter", [12, 1, 2]),
        ("seasonal_summer", [3, 4, 5]),
        ("seasonal_monsoon", [6, 7, 8, 9]),
        ("seasonal_post_monsoon", [10, 11]),
    )
    defaults = get_default_config()
    for section, legacy_prefix in (("solar", "seasonal_"), ("wind", "month_")):
        sec = config.get(section)
        if not isinstance(sec, dict):
            continue

        has_legacy = any(f"{legacy_prefix}{i}" in sec for i in range(1, 13))
        has_new = all(k in sec for k, _ in season_defs)

        if has_legacy:
            for key, months in season_defs:
                fallback = float(defaults[section][key]["value"])
                p = deepcopy(defaults[section][key])
                p["value"] = _avg_month_values(sec, legacy_prefix, months, fallback)
                if any(
                    isinstance(sec.get(f"{legacy_prefix}{m}"), dict)
                    and sec[f"{legacy_prefix}{m}"].get("source") == USER_INPUT
                    for m in months
                ):
                    p["source"] = USER_INPUT
                sec[key] = p
        elif not has_new:
            for key, _months in season_defs:
                sec[key] = deepcopy(defaults[section][key])

        for i in range(1, 13):
            sec.pop(f"{legacy_prefix}{i}", None)
            sec.pop(f"month_{i}", None)
            sec.pop(f"seasonal_{i}", None)


def has_default_assumptions(config: dict) -> bool:
    for _, param in iter_params(config):
        if param.get("source") == DEFAULT_ASSUMPTION and param.get("editable", True):
            return True
    return False


def count_default_assumptions(config: dict) -> int:
    n = 0
    for _, param in iter_params(config):
        if param.get("source") == DEFAULT_ASSUMPTION and param.get("editable", True):
            n += 1
    return n


CRITICAL_DEFAULT_PATHS = (
    "load.peak_load_mw",
    "load.load_factor_pct",
    "solar.capacity_factor_pct",
    "wind.capacity_factor_pct",
    "grid.energy_tariff_inr_per_kwh",
    "solar.capex_inr_per_mw",
    "wind.capex_inr_per_mw",
    "bess.capex_inr_per_mwh",
    "solar.opex_inr_per_mw_year",
    "compliance.rpo_applicability",
    "compliance.rco_applicability",
    "compliance.eso_applicability",
)


def critical_default_assumptions(config: dict) -> list[str]:
    out = []
    for path in CRITICAL_DEFAULT_PATHS:
        try:
            section, key = path.split(".", 1)
            p = config.get(section, {}).get(key)
            if isinstance(p, dict) and p.get("source") == DEFAULT_ASSUMPTION and p.get("editable", True):
                out.append(path)
        except Exception:
            continue
    return out


def flatten_assumptions(config: dict) -> list[dict]:
    rows = []
    for path, param in iter_params(config):
        rows.append(
            {
                "parameter": path,
                "value": param["value"],
                "unit": param.get("unit", ""),
                "source": param.get("source", ""),
                "type": param.get("source", ""),
                "description": param.get("description", ""),
                "editable": bool(param.get("editable", True)),
                "kind": param.get("kind", "number"),
                "options": param.get("options", []),
                "minimum": param.get("minimum"),
                "maximum": param.get("maximum"),
                "step": param.get("step"),
            }
        )
    return rows
