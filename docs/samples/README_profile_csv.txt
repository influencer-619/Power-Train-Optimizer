PowerTrain Optimizer — Profile CSV templates (Model 2.0)
========================================================

Use these files on the Profiles page (Load / Solar / Wind).

Format (required)
-----------------
- Header row: timestamp,mw
- Exactly 8,760 data rows for a non-leap year (or 8,784 for leap year)
- timestamp: unique hourly stamps (ISO recommended), e.g. 2025-01-01T00:00:00
- mw: non-negative number (megawatts). No blanks, no text, no NaN.

How to fill
-----------
1. Download the matching template (load / solar / wind).
2. Keep the timestamp column as-is (or replace with your own unique hourly stamps).
3. Replace the mw column with your project data (same row count).
4. Save as CSV (UTF-8).
5. On Profiles: Choose file → Upload CSV.

Notes
-----
- Sample mw values are EXAMPLE shapes for a ~250 MW data centre / 450 MW solar / 300 MW wind.
  Replace them with your measured or forecast series before investment decisions.
- Invalid files are rejected — the app will not silently fall back to synthetic data
  when profile_source is PROJECT DATA.
- Solar night hours should typically be 0 MW.
- Load must stay > 0 in hours the facility operates (model hours = 8760).

Files
-----
- load_profile_template_8760.csv
- solar_profile_template_8760.csv
- wind_profile_template_8760.csv
