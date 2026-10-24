# Archived-run evaluation method

## Forecast question and clock

For five fixed Iranian locations, can a correction learned from earlier archived runs improve the raw ECMWF IFS forecast for **Wednesday's UTC daily mean temperature, wind speed, sea-level pressure, and precipitation occurrence**? The simulation fixes one Monday 00 UTC run per week, declares Tuesday 12 UTC as the decision time, and scores the full Wednesday UTC day. This is a fixed 48–71 hour lead from model initialization. The four variables all use the same cases and the same issue protocol.

The [forecast data card](ARCHIVED_FORECAST_DATA_CARD.md) defines the archive, coordinates, units, request manifest and publication caveat. The [ERA5 data card](ERA5_DATA_CARD.md) defines the delayed gridded reference. The evaluated 2025 sample has 53 target Wednesdays × five cities = 265 cases; the 2024 runs provide prior training examples. The committed [JSON report](../reports/archived-ifs-2025.json) contains folds, per-city metrics and calibration bins; its checksum-linked [case-level predictions](../reports/archived-ifs-2025-predictions.csv) allow an audit of individual forecasts.

## Leakage controls

At any issue time, predictors are the archived IFS forecast amounts, city and target calendar only. They do **not** include target-day ERA5, target-day station measurements, later model runs, or the original unsourced CSV. The ingestion checks that issue time is exactly 36 hours after run initialization and that target-day start is exactly 48 hours after it. It rejects missing reference joins, nonfinite values and duplicate city-day keys.

ERA5 is assumed usable for **training** only seven days after its target date. Each quarter's models are fitted once on cases with `target_date + 7 days <= first issue time in that quarter`. The four expanding training windows contain 190, 255, 320 and 385 city-day examples; the respective test windows contain 65, 65, 65 and 70. Test labels never choose the correction. The seven-day delay is more conservative than Open-Meteo's approximate five-day ERA5 publication delay, but exact historical release times are unavailable.

## Models and metrics

- **Continuous raw baseline:** the archived IFS daily value itself. **Candidate:** raw IFS plus the city-specific mean `(ERA5 − IFS)` residual from the allowed training window. This is a simple learned bias correction, refitted at each quarter. Temperature, wind and pressure use mean absolute error in their original units.
- **Precipitation raw baseline:** a deterministic 0/1 event from the archived daily IFS precipitation amount. A second baseline is the prior training window's observed city event rate. **Candidate:** regularized logistic regression on log(1 + forecast mm), city and target-day seasonal sine/cosine, trained only on allowed historical pairs. Brier score evaluates probabilities against ERA5 occurrence.
- Two event definitions are reported: **>0 mm** and **≥1 mm**. The report gives their base rates and five probability calibration bins. Sparse high-probability bins should be interpreted cautiously; no probability forecast is certified as calibrated by this sample alone.

The report and dashboard show pooled, city and quarterly metrics. A pooled gain does not select a model for live use. Temperature correction improves all tested cities and quarters against ERA5; wind worsens slightly in Bandar Abbas; pressure worsens in Rasht, Sanandaj and 2025 Q1; the >0 mm precipitation candidate worsens in Bandar Abbas, Mashhad, Yazd, Q1 and Q4. The ≥1 mm candidate worsens in Bandar Abbas, Sanandaj and Q1. See the report for exact scores.

## Reproduction and interpretation

`python -m scripts.evaluate_archived_runs` recomputes the report from the committed forecast and ERA5 CSVs. `python -m scripts.fetch_archived_runs` retrieves the same requested run dates from the API but may receive revised source data. Unit tests verify source hashes, weekly coverage, fixed lead, unavailable-label exclusion, rejected malformed pairs and score reproduction; CI runs the full test suite and Ruff.

The reference is **ERA5 gridded reanalysis**, not independent station truth. ERA5 and IFS have related model lineage and different spatial grids. Weekly sampling misses intervening days and can overrepresent seasonal patterns; five locations and one evaluation year do not establish broad robustness. Exact archived delivery timestamps, independent station coverage/quality, and prospective live ingestion/monitoring are missing. The project therefore makes a historical skill claim only against this specified ERA5 snapshot and does not promote a real-time forecasting model.
