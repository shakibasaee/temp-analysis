# One-city next-day forecast evaluation

This isolated experiment prepares the input for a later signed-error drift
check. It does **not** run Page–Hinkley or claim that drift was detected.

## Data and validation

- Input: `data/new_weather_data.csv`; fields `Date_Time`, `City`, and
  `Temperature_C` are mapped to date, city, and actual temperature. The file's
  original provider, timezone, and exact definition of `Temperature_C` remain
  unverified. Its column name indicates Celsius; no unit conversion is made.
- City: `Mashhad`, selected from the five current cities. It has 731 daily
  records from 2023-01-01 through 2024-12-31.
- The script sorts dates and checks for invalid/non-midnight dates, duplicate
  dates, missing calendar days, and missing/non-finite temperatures. This
  snapshot has zero in every category. The command fails rather than
  comparing misaligned days if any such defect appears.
- The exact input SHA-256 is recorded in `forecast_eval.metadata.json`.

## Forecast contract

The first 584 chronological dates (2023-01-01 to 2024-08-06) fit the existing
`scripts.models.linear_regression.LinearRegressionModel`. The final 147 dates
(2024-08-07 to 2024-12-31) are the untouched evaluation period. The model is
fixed after training. Its prediction for each target date uses only that
date's known calendar fields and the fixed city; it does not read the target
temperature or later observations. One may issue that prediction on the
previous day. The comparator for target date `d` is the **actual temperature
on `d-1`**, available before issuing the next-day forecast. Both methods are
scored on exactly the same 147 target dates.

The output [`forecast_eval.csv`](../forecast_eval.csv) contains exactly
`date,actual,predicted`, sorted ascending with one row per test date. The
first row is 2024-08-07. For the later drift experiment, signed error is
`actual - predicted`: positive means underprediction (forecast too cold),
negative means overprediction (forecast too warm).

| Method | MAE, °C | Mean signed error, °C |
|---|---:|---:|
| Existing calendar linear regression | 3.2800 | -1.2483 |
| Persistence: tomorrow equals today | 1.8551 | -0.1735 |

The simple comparator performs better on this holdout. The regression's
negative average signed error indicates overprediction *on average across
the whole test period*; it does not show when a change began or establish
drift. No alert date is asserted.

## Reproduce

From the repository root after installing `requirements.txt`:

```bash
python -m scripts.one_city_forecast_eval --data data/new_weather_data.csv --city Mashhad --out forecast_eval.csv
python -m unittest tests.test_one_city_forecast_eval -v
```

The script writes `forecast_eval.csv` and
[`forecast_eval.metadata.json`](../forecast_eval.metadata.json), which records
the source and output hashes, split dates/counts, model, units caveat, and
both methods' metrics. This input file is ready for the proposed
Page–Hinkley check on the **ordered signed errors**. A separate check of
seasonal temperature anomalies would address a different question and
requires a justified multiyear observational reference.
