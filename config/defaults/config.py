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
            "Label year for timestamps. Not a leap year.",
            kind="integer",
            minimum=2020,
            maximum=2100,
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
        "seasonal_1": P(0.78, "x", DEFAULT_ASSUMPTION, "January solar seasonal factor.", minimum=0, step=0.01),
        "seasonal_2": P(0.88, "x", DEFAULT_ASSUMPTION, "February solar seasonal factor.", minimum=0, step=0.01),
        "seasonal_3": P(1.02, "x", DEFAULT_ASSUMPTION, "March solar seasonal factor.", minimum=0, step=0.01),
        "seasonal_4": P(1.12, "x", DEFAULT_ASSUMPTION, "April solar seasonal factor.", minimum=0, step=0.01),
        "seasonal_5": P(1.18, "x", DEFAULT_ASSUMPTION, "May solar seasonal factor.", minimum=0, step=0.01),
        "seasonal_6": P(1.05, "x", DEFAULT_ASSUMPTION, "June solar seasonal factor.", minimum=0, step=0.01),
        "seasonal_7": P(0.92, "x", DEFAULT_ASSUMPTION, "July solar seasonal factor.", minimum=0, step=0.01),
        "seasonal_8": P(0.90, "x", DEFAULT_ASSUMPTION, "August solar seasonal factor.", minimum=0, step=0.01),
        "seasonal_9": P(0.98, "x", DEFAULT_ASSUMPTION, "September solar seasonal factor.", minimum=0, step=0.01),
        "seasonal_10": P(1.05, "x", DEFAULT_ASSUMPTION, "October solar seasonal factor.", minimum=0, step=0.01),
        "seasonal_11": P(0.90, "x", DEFAULT_ASSUMPTION, "November solar seasonal factor.", minimum=0, step=0.01),
        "seasonal_12": P(0.75, "x", DEFAULT_ASSUMPTION, "December solar seasonal factor.", minimum=0, step=0.01),
    },
    "wind": {
        "profile_source": P(
            "SYNTHETIC",
            "",
            DEFAULT_ASSUMPTION,
            "SYNTHETIC = CF/monthly generator. PROJECT DATA = imported 8,760 hourly MW series (optional).",
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
        "month_1": P(0.70, "x", DEFAULT_ASSUMPTION, "January wind monthly factor.", minimum=0, step=0.01),
        "month_2": P(0.75, "x", DEFAULT_ASSUMPTION, "February wind monthly factor.", minimum=0, step=0.01),
        "month_3": P(0.82, "x", DEFAULT_ASSUMPTION, "March wind monthly factor.", minimum=0, step=0.01),
        "month_4": P(0.92, "x", DEFAULT_ASSUMPTION, "April wind monthly factor.", minimum=0, step=0.01),
        "month_5": P(1.10, "x", DEFAULT_ASSUMPTION, "May wind monthly factor.", minimum=0, step=0.01),
        "month_6": P(1.35, "x", DEFAULT_ASSUMPTION, "June wind monthly factor.", minimum=0, step=0.01),
        "month_7": P(1.45, "x", DEFAULT_ASSUMPTION, "July wind monthly factor.", minimum=0, step=0.01),
        "month_8": P(1.25, "x", DEFAULT_ASSUMPTION, "August wind monthly factor.", minimum=0, step=0.01),
        "month_9": P(1.05, "x", DEFAULT_ASSUMPTION, "September wind monthly factor.", minimum=0, step=0.01),
        "month_10": P(0.88, "x", DEFAULT_ASSUMPTION, "October wind monthly factor.", minimum=0, step=0.01),
        "month_11": P(0.78, "x", DEFAULT_ASSUMPTION, "November wind monthly factor.", minimum=0, step=0.01),
        "month_12": P(0.72, "x", DEFAULT_ASSUMPTION, "December wind monthly factor.", minimum=0, step=0.01),
    },
    "bess": {
        "power_mw": P(150.0, "MW", DEFAULT_ASSUMPTION, "BESS power rating (charge and discharge unless overridden).", minimum=0, step=1),
        "energy_mwh": P(600.0, "MWh", DEFAULT_ASSUMPTION, "Usable energy capacity at 100% SOC window before min/max SOC.", minimum=0, step=1),
        "initial_soc_pct": P(50.0, "%", DEFAULT_ASSUMPTION, "Starting state of charge.", minimum=0, maximum=100, step=1),
        "min_soc_pct": P(10.0, "%", DEFAULT_ASSUMPTION, "Lower SOC bound.", minimum=0, maximum=100, step=1),
        "max_soc_pct": P(95.0, "%", DEFAULT_ASSUMPTION, "Upper SOC bound.", minimum=0, maximum=100, step=1),
        "charge_efficiency_pct": P(95.0, "%", DEFAULT_ASSUMPTION, "One-way charging efficiency.", minimum=1, maximum=100, step=0.1),
        "discharge_efficiency_pct": P(95.0, "%", DEFAULT_ASSUMPTION, "One-way discharging efficiency.", minimum=1, maximum=100, step=0.1),
        "round_trip_efficiency_pct": P(90.25, "%", CALCULATED, "charge_efficiency × discharge_efficiency.", editable=False),
        "max_charge_mw": P(150.0, "MW", DEFAULT_ASSUMPTION, "Maximum charge power. Defaults to power rating."),
        "max_discharge_mw": P(150.0, "MW", DEFAULT_ASSUMPTION, "Maximum discharge power. Defaults to power rating."),
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
        "transmission_inr_per_kwh": P(0.40, "₹/kWh", DEFAULT_ASSUMPTION, "Transmission charge applied to wheeled/imported energy as configured by structure."),
        "wheeling_inr_per_kwh": P(0.30, "₹/kWh", DEFAULT_ASSUMPTION, "Wheeling charge."),
        "banking_inr_per_kwh": P(0.10, "₹/kWh", DEFAULT_ASSUMPTION, "Banking-related charge. Applied only when banking_enabled."),
        "other_charges_inr_per_kwh": P(0.15, "₹/kWh", DEFAULT_ASSUMPTION, "Other configurable volumetric charges."),
        "loss_pct": P(3.0, "%", DEFAULT_ASSUMPTION, "Grid/network loss applied to wheeled RE in captive/OA structures."),
        "availability_pct": P(99.5, "%", DEFAULT_ASSUMPTION, "Deterministic availability: first (1-a)×8760 hours of each year are scaled; implemented as a constant derate of max import."),
        "tariff_escalation_pct": P(4.0, "%/yr", DEFAULT_ASSUMPTION, "Grid tariff escalation in the financial model."),
        "banking_enabled": P(False, "", DEFAULT_ASSUMPTION, "If false, banking charges are zero regardless of the unit rate.", kind="boolean"),
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
        "apply_network_charges_to_re": P(True, "", DEFAULT_ASSUMPTION, "Apply transmission/wheeling/other charges to renewable energy served.", kind="boolean"),
        "apply_network_charges_to_grid": P(False, "", DEFAULT_ASSUMPTION, "Apply transmission/wheeling to grid import in addition to the DISCOM energy tariff.", kind="boolean"),
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

DEFAULT_SCENARIOS = [
    {"name": "DISCOM – 90% RE", "structure": "DISCOM", "annual_re_target_pct": 90.0, "hourly_cfe_target_pct": 90.0},
    {"name": "CAPTIVE – 95% RE", "structure": "CAPTIVE", "annual_re_target_pct": 95.0, "hourly_cfe_target_pct": 90.0},
    {"name": "HYBRID – 95% RE / 99% CFE", "structure": "HYBRID", "annual_re_target_pct": 95.0, "hourly_cfe_target_pct": 99.0},
    {"name": "OPEN ACCESS – 99% RE / 100% CFE", "structure": "OPEN_ACCESS", "annual_re_target_pct": 99.0, "hourly_cfe_target_pct": 100.0},
]


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
    ce = v(config, "bess.charge_efficiency_pct") / 100.0
    de = v(config, "bess.discharge_efficiency_pct") / 100.0
    config["bess"]["round_trip_efficiency_pct"]["value"] = round(ce * de * 100.0, 4)
    config["grid"]["connection_voltage_kv"]["value"] = v(config, "data_center.grid_connection_kv")
    return config


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
