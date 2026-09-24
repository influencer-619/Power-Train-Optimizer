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
            CALCULATED,
            "Same as General → Project name. Used on reports.",
            kind="text",
            editable=False,
        ),
        "it_capacity_mw": P(
            250.0,
            "MW",
            DEFAULT_ASSUMPTION,
            "IT / critical load (MW). Same value drives Load → IT load and facility peak = IT × PUE.",
            minimum=0.01,
            step=0.1,
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
            "Seasonal TOD",
            "",
            DEFAULT_ASSUMPTION,
            "How the hourly load shape is generated. Seasonal TOD is the default commercial path.",
            kind="select",
            options=["Seasonal TOD", "Flat", "Daily Pattern", "Weekday/Weekend", "Seasonal", "Custom Parameterized"],
        ),
        "seasonal_tod_summer_months": P(
            "3,4,5",
            "",
            DEFAULT_ASSUMPTION,
            "Summer months (1–12, comma-separated) for Seasonal TOD shaping.",
            kind="text",
        ),
        "seasonal_tod_rainy_months": P(
            "6,7,8,9",
            "",
            DEFAULT_ASSUMPTION,
            "Rainy / monsoon months for Seasonal TOD shaping.",
            kind="text",
        ),
        "seasonal_tod_winter_months": P(
            "10,11,12,1,2",
            "",
            DEFAULT_ASSUMPTION,
            "Winter months for Seasonal TOD shaping.",
            kind="text",
        ),
        "seasonal_tod_day_start_hour": P(
            8,
            "h",
            DEFAULT_ASSUMPTION,
            "Day TOD start (hour 0–23). Default 8 = 8AM. Day band is start ≤ hour < end; night is the rest.",
            kind="integer",
            minimum=0,
            maximum=23,
        ),
        "seasonal_tod_day_end_hour": P(
            20,
            "h",
            DEFAULT_ASSUMPTION,
            "Day TOD end exclusive (hour 0–23). Default 20 = 8PM. With start 8 → day 8AM–8PM, night 8PM–8AM.",
            kind="integer",
            minimum=0,
            maximum=23,
        ),
        "seasonal_tod_summer_day": P(1.05, "x", DEFAULT_ASSUMPTION, "Summer day-band shape multiplier.", minimum=0, step=0.01),
        "seasonal_tod_summer_night": P(0.95, "x", DEFAULT_ASSUMPTION, "Summer night-band shape multiplier.", minimum=0, step=0.01),
        "seasonal_tod_rainy_day": P(1.02, "x", DEFAULT_ASSUMPTION, "Rainy day-band shape multiplier.", minimum=0, step=0.01),
        "seasonal_tod_rainy_night": P(0.98, "x", DEFAULT_ASSUMPTION, "Rainy night-band shape multiplier.", minimum=0, step=0.01),
        "seasonal_tod_winter_day": P(1.03, "x", DEFAULT_ASSUMPTION, "Winter day-band shape multiplier.", minimum=0, step=0.01),
        "seasonal_tod_winter_night": P(0.97, "x", DEFAULT_ASSUMPTION, "Winter night-band shape multiplier.", minimum=0, step=0.01),
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
        "capacity_factor_pct": P(22.0, "%", DEFAULT_ASSUMPTION, "Target annual capacity factor used to scale the synthetic profile.", minimum=0, maximum=80, step=0.1),
        "sunrise_hour": P(6.0, "h", DEFAULT_ASSUMPTION, "Hour of day (0–24) at which generation becomes non-zero.", minimum=0, maximum=12, step=0.5),
        "sunset_hour": P(18.0, "h", DEFAULT_ASSUMPTION, "Hour of day at which generation returns to zero.", minimum=12, maximum=24, step=0.5),
        "peak_generation_hour": P(12.0, "h", DEFAULT_ASSUMPTION, "Hour of day of the diurnal peak.", minimum=0, maximum=24, step=0.5),
        "hourly_variability": P(0.12, "frac", DEFAULT_ASSUMPTION, "Deterministic relative noise amplitude applied in daylight hours.", minimum=0, maximum=1, step=0.01),
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
        "capacity_factor_pct": P(32.0, "%", DEFAULT_ASSUMPTION, "Target annual capacity factor used to scale the synthetic profile.", minimum=0, maximum=80, step=0.1),
        "hourly_variability": P(0.28, "frac", DEFAULT_ASSUMPTION, "Deterministic relative noise amplitude for hourly wind.", minimum=0, maximum=1, step=0.01),
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
    "grid": {
        "connection_voltage_kv": P(220.0, "kV", CONCEPT_NOTE, "Grid interconnection voltage from the concept note."),
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

        "cost_blend_basis": P(
            "TARGET_POWER_PCT",
            "",
            DEFAULT_ASSUMPTION,
            "CAPTIVE/HYBRID energy blend: TARGET_POWER_PCT = Architecture Percentage of power; "
            "SIMULATED_ENERGY_SHARE = same contracted Architecture mix % (DC buyer — suppliers deliver "
            "at fixed rates; no plant MW/MWh). Bill = mix % × DISCOM/Solar/Wind stacks + Storage tariff.",
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
        "excel_bess_ppa_inr_per_kwh": P(
            0.0,
            "₹/kWh",
            DEFAULT_ASSUMPTION,
            "Storage tariff (₹/kWh) — consumer fixed rate for BESS % of power. "
            "No BESS CAPEX/OPEX; enter the contracted ₹/kWh.",
            step=0.01,
        ),
        "excel_bess_energy_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Energy Charges (BESS). Captive/Hybrid: unused (0).", step=0.01),
        "excel_bess_wheeling_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Wheeling (BESS). Not used for on-site Captive/Hybrid storage.", step=0.01),
        "excel_bess_transmission_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Transmission (BESS). Not used for on-site Captive/Hybrid storage.", step=0.01),
        "excel_bess_transmission_loss_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Transmission losses (BESS). Not used for Captive/Hybrid.", step=0.01),
        "excel_bess_css_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "CSS (BESS). Not used for on-site Captive/Hybrid storage.", step=0.01),
        "excel_bess_as_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Additional surcharge (BESS). Not used for Captive/Hybrid.", step=0.01),
        "excel_bess_sldc_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "SLDC (BESS). Not used for Captive/Hybrid.", step=0.01),
        "excel_bess_banking_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Banking (BESS). Not used for Captive/Hybrid.", step=0.01),
        "excel_bess_ed_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "Electricity duty (BESS). Not used for Captive/Hybrid.", step=0.01),
        "excel_bess_tose_inr_per_kwh": P(0.0, "₹/kWh", DEFAULT_ASSUMPTION, "TOSE (BESS). Not used for Captive/Hybrid.", step=0.01),
        "excel_bess_total_inr_per_kwh": P(
            0.0,
            "₹/kWh",
            CALCULATED,
            "Captive/Hybrid: equals Storage tariff. Open Access: sum of BESS charge stack.",
            editable=False,
            step=0.01,
        ),
        "mix_discom_pct": P(
            25.0,
            "%",
            DEFAULT_ASSUMPTION,
            "DISCOM/grid share of Architecture Percentage of power (HYBRID). "
            "Selected assets’ mix % must sum to 100. Pricing share only.",
            minimum=0,
            maximum=100,
            step=1,
        ),
        "mix_solar_pct": P(
            35.0,
            "%",
            DEFAULT_ASSUMPTION,
            "Solar share of Architecture Percentage of power (CAPTIVE / HYBRID). "
            "Selected assets’ mix % must sum to 100. Pricing / energy-contract share.",
            minimum=0,
            maximum=100,
            step=1,
        ),
        "mix_wind_pct": P(
            25.0,
            "%",
            DEFAULT_ASSUMPTION,
            "Wind share of Architecture Percentage of power (CAPTIVE / HYBRID). "
            "Selected assets’ mix % must sum to 100. Pricing / energy-contract share.",
            minimum=0,
            maximum=100,
            step=1,
        ),
        "mix_bess_pct": P(
            15.0,
            "%",
            DEFAULT_ASSUMPTION,
            "BESS share of contracted Architecture energy (CAPTIVE / HYBRID). "
            "Priced at Storage tariff ₹/kWh — not a plant MW/MWh size. "
            "Selected assets’ mix % must sum to 100.",
            minimum=0,
            maximum=100,
            step=1,
        ),
        "grid_power_pct": P(
            25.0,
            "%",
            CALCULATED,
            "Alias of DISCOM / grid mix % (synced from mix_discom_pct when DISCOM is included).",
            editable=False,
            minimum=0,
            maximum=100,
            step=0.1,
        ),
        "captive_re_pct": P(
            75.0,
            "%",
            CALCULATED,
            "Alias of RE mix % = Solar + Wind + BESS selected shares (synced on recompute).",
            editable=False,
            minimum=0,
            maximum=100,
            step=0.1,
        ),
        "discom_name": P("MSEDCL", "", CONCEPT_NOTE, "DISCOM counterparty name referenced in the concept note DISCOM structure.", kind="text"),
        "captive_ownership_pct": P(26.0, "%", DEFAULT_ASSUMPTION, "Captive ownership share. Not a legal qualification test."),
        "captive_allocation_pct": P(100.0, "%", DEFAULT_ASSUMPTION, "Share of RE project output allocated to this data centre."),
        "captive_energy_price": P(3.80, "₹/kWh", DEFAULT_ASSUMPTION, "Captive delivered energy price before network charges."),
        "oa_energy_price": P(4.20, "₹/kWh", DEFAULT_ASSUMPTION, "Open-access RE energy price before OA charges."),
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
            False,
            "",
            DEFAULT_ASSUMPTION,
            "BESS network charges on discharge. Forced off for Captive/Hybrid (use Storage tariff ₹/kWh).",
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
            "Min(Load, Load×(Architecture Solar%+Wind%+BESS%)/100) / Load × 100 "
            "(firm contracted mix) meets this target; otherwise Fail.",
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
    "financial": {
        "project_life_yr": P(25, "yr", DEFAULT_ASSUMPTION, "Cash-flow horizon.", kind="integer", minimum=1, maximum=40),
        "discount_rate_pct": P(10.0, "%", DEFAULT_ASSUMPTION, "Real/nominal discount rate applied to cash flows as entered (no separate real/nominal conversion)."),
        "electricity_escalation_pct": P(4.0, "%", DEFAULT_ASSUMPTION, "Grid energy-cost escalation."),
        "re_cost_escalation_pct": P(2.0, "%", DEFAULT_ASSUMPTION, "RE tariff/OPEX escalation where billed as energy."),
        "tax_pct": P(0.0, "%", DEFAULT_ASSUMPTION, "Optional tax on taxable income. Default 0 (pre-tax)."),
        "additional_costs": P(
            [],
            "₹/yr",
            DEFAULT_ASSUMPTION,
            "User-defined additional annual cost line items (label + amount). Included in delivered ₹/kWh and cashflows.",
            kind="list",
        ),
    },
}

PRESET_RE_TARGETS = [90.0, 95.0, 99.0]
PRESET_CFE_TARGETS = [90.0, 95.0, 99.0, 100.0]

DEFAULT_SCENARIOS = []  # Architecture is chosen in Project Setup — do not seed structure presets here


def get_default_config():
    cfg = deepcopy(DEFAULT_CONFIG)
    return strip_plant_leftovers(cfg)


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


def v_opt(config: dict, dotted: str, default=None):
    """Read a config value or return default when the path was retired / missing."""
    try:
        return v(config, dotted)
    except Exception:
        return default


def recompute_calculated(config: dict) -> dict:
    """Refresh calculated fields (peak, LF, stack totals, study hours, migrations)."""
    strip_plant_leftovers(config)
    # Project name → facility name (same label)
    try:
        general = config.get("general") or {}
        dc = config.get("data_center") or {}
        if "project_name" in general and "facility_name" in dc:
            name = str(v(config, "general.project_name") or "")
            dc["facility_name"]["value"] = name
            dc["facility_name"]["source"] = CALCULATED
            dc["facility_name"]["editable"] = False
    except Exception:
        pass

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

    # Seasonal TOD day band: product requirement is 8AM–8PM / 8PM–8AM
    try:
        load = config.get("load") or {}
        if "seasonal_tod_day_start_hour" in load and "seasonal_tod_day_end_hour" in load:
            # Migrate mistaken recovery defaults (6–22) back to required 8–20
            try:
                ds = int(load["seasonal_tod_day_start_hour"].get("value"))
                de = int(load["seasonal_tod_day_end_hour"].get("value"))
            except Exception:
                ds, de = 8, 20
            if (ds, de) == (6, 22):
                load["seasonal_tod_day_start_hour"]["value"] = 8
                load["seasonal_tod_day_end_hour"]["value"] = 20
                load["seasonal_tod_day_start_hour"]["source"] = CALCULATED
                load["seasonal_tod_day_end_hour"]["source"] = CALCULATED
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

    # Captive/Hybrid: BESS OA lines unused; single Storage tariff stays editable (PPA key).
    try:
        structure = str(v(config, "commercial.structure") or "")
        commercial = config.get("commercial") or {}
        commercial.pop("include_generation_capex", None)  # obsolete: tariff stacks only
        if structure in ("CAPTIVE", "HYBRID"):
            if "apply_network_charges_to_bess" in commercial:
                commercial["apply_network_charges_to_bess"]["value"] = False
                commercial["apply_network_charges_to_bess"]["source"] = CALCULATED
            # Keep excel_bess_ppa as the single Storage ₹/kWh input
            if "excel_bess_ppa_inr_per_kwh" in commercial:
                commercial["excel_bess_ppa_inr_per_kwh"]["editable"] = True
                commercial["excel_bess_ppa_inr_per_kwh"]["description"] = (
                    "Storage tariff (₹/kWh) — consumer fixed rate for BESS % of power. "
                    "No BESS CAPEX/OPEX; enter the contracted ₹/kWh."
                )
            for key in (
                "excel_bess_energy_inr_per_kwh",
                "excel_bess_wheeling_inr_per_kwh",
                "excel_bess_transmission_inr_per_kwh",
                "excel_bess_transmission_loss_inr_per_kwh",
                "excel_bess_css_inr_per_kwh",
                "excel_bess_as_inr_per_kwh",
                "excel_bess_sldc_inr_per_kwh",
                "excel_bess_banking_inr_per_kwh",
                "excel_bess_ed_inr_per_kwh",
                "excel_bess_tose_inr_per_kwh",
            ):
                if key not in commercial:
                    continue
                commercial[key]["value"] = 0.0
                commercial[key]["source"] = CALCULATED
                commercial[key]["editable"] = False
            if "excel_bess_total_inr_per_kwh" in commercial and "excel_bess_ppa_inr_per_kwh" in commercial:
                try:
                    commercial["excel_bess_total_inr_per_kwh"]["value"] = round(
                        float(commercial["excel_bess_ppa_inr_per_kwh"].get("value") or 0.0), 6
                    )
                except Exception:
                    commercial["excel_bess_total_inr_per_kwh"]["value"] = 0.0
                commercial["excel_bess_total_inr_per_kwh"]["source"] = CALCULATED
                commercial["excel_bess_total_inr_per_kwh"]["editable"] = False
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


# Plant / owner leftovers — removed from buyer config (strip on load for old .pto.zip).
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
    return config


_MIX_PCT_BY_INCLUDE = {
    "include_discom": "mix_discom_pct",
    "include_solar": "mix_solar_pct",
    "include_wind": "mix_wind_pct",
    "include_bess": "mix_bess_pct",
}


def active_architecture_mix_keys(config: dict) -> list[str]:
    """Mix % keys that must sum to 100 for the current structure + include flags."""
    commercial = config.get("commercial")
    if not isinstance(commercial, dict):
        return []
    structure_p = commercial.get("structure")
    structure = str(structure_p.get("value", "HYBRID")) if isinstance(structure_p, dict) else "HYBRID"
    if structure == "DISCOM":
        return []
    if structure == "CAPTIVE":
        flag_keys = ["include_solar", "include_wind", "include_bess"]
    elif structure in ("HYBRID", "OPEN_ACCESS"):
        flag_keys = ["include_discom", "include_solar", "include_wind", "include_bess"]
    else:
        return []

    keys: list[str] = []
    for flag in flag_keys:
        p = commercial.get(flag)
        on = True
        if isinstance(p, dict) and "value" in p:
            on = bool(p["value"])
        if on:
            keys.append(_MIX_PCT_BY_INCLUDE[flag])
    return keys


def ensure_architecture_mix_sums_to_100(config: dict) -> None:
    """If selected Asset usage % do not sum to ~100, redistribute equally (old projects / structure changes)."""
    commercial = config.get("commercial")
    if not isinstance(commercial, dict):
        return
    keys = active_architecture_mix_keys(config)
    if not keys:
        return
    total = 0.0
    for key in keys:
        p = commercial.get(key)
        if isinstance(p, dict) and "value" in p:
            try:
                total += float(p["value"])
            except (TypeError, ValueError):
                pass
    if abs(total - 100.0) <= 0.05:
        return
    n = len(keys)
    share = round(100.0 / n, 4)
    allocated = 0.0
    for i, key in enumerate(keys):
        p = commercial.get(key)
        if not isinstance(p, dict) or "value" not in p:
            continue
        if i < n - 1:
            p["value"] = share
            allocated += share
        else:
            p["value"] = round(100.0 - allocated, 4)


def _normalize_architecture_flags(config: dict) -> None:
    """Keep include_* flags consistent with commercial structure (UI + old projects)."""
    commercial = config.get("commercial")
    if not isinstance(commercial, dict):
        return
    structure_p = commercial.get("structure")
    structure = str(structure_p.get("value", "HYBRID")) if isinstance(structure_p, dict) else "HYBRID"
    # Legacy OPEN_ACCESS behaves like HYBRID (same asset flags + mix rules)
    if structure == "OPEN_ACCESS":
        structure = "HYBRID"
        if isinstance(structure_p, dict) and "value" in structure_p:
            structure_p["value"] = "HYBRID"

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
    strip_plant_leftovers(config)
    for section in ("compliance", "optimization"):
        sec = config.get(section)
        if isinstance(sec, dict):
            sec.pop("enforce_cfe_target", None)
    commercial = config.get("commercial")
    if isinstance(commercial, dict):
        commercial.pop("include_generation_capex", None)
    load = config.get("load")
    if isinstance(load, dict):
        load.pop("growth_rate_pct", None)
    _seed_re_network_from_grid(config, newly_added)
    _seed_solar_wind_network_from_re(config, newly_added)
    _normalize_architecture_flags(config)
    ensure_architecture_mix_sums_to_100(config)
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
    "compliance.rpo_rco_applicability",
    "compliance.eso_applicability",
)

# Safety net: never show retired plant keys if an old project still carries them.
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
)


def is_plant_leftover_path(path: str) -> bool:
    if path in PLANT_LEFTOVER_PATHS:
        return True
    return any(path.startswith(p) for p in PLANT_LEFTOVER_PREFIXES)


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
        if is_plant_leftover_path(path):
            continue
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
