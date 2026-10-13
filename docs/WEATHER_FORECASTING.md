# Experimental next-day weather benchmark

This workflow extends the original temperature-only CLI. It is an **internal experiment on a dataset with undocumented provenance**, not a live weather service. The supplied data end on 2024-12-31; a forecast for 2025-01-01 is a historical replay today.

## Forecast contract

For each city, the issue time is **after all measurements for day D are available**. The targets describe day D+1. Every predictor is measured on or before D, except calendar values derived from the known target date. This contract requires the data provider to state its daily cutoff and time zone before operational use.

| Target for D+1 | Baseline | Candidate | Primary score |
| --- | --- | --- | --- |
| Temperature (°C) | Day D temperature | Ridge regression | MAE (°C) |
| Wind speed (km/h) | Day D wind speed | Ridge regression | MAE (km/h) |
| Pressure (hPa) | Day D pressure | Ridge regression | MAE (hPa) |
| Rain occurrence, precipitation > 0 mm | Wet-day frequency in the previous 30 days | Logistic regression | Brier score |

The rain output is a probability, not a precipitation amount. Missing precipitation and pressure values are retained as missing. Rows without a target or baseline are excluded **for that target only** and counted in the report. Candidate models impute missing predictors using training-period medians. City identity, recent measurements, rolling summaries, and target-day calendar cycles are the model features.

Training targets end on 2023-12-31; validation covers 2024-01-01 through 2024-06-30; test covers 2024-07-01 through 2024-12-31. The candidate is fit on training data for validation, then refit on training plus validation for test. During evaluation, each day's actual measurements may be used for the next day's predictors. No test labels enter fitting. The JSON report includes scores for every city, so aggregate gains do not hide local regressions. This is still one held-out period, not a rolling-origin or external validation.

## Run

```bash
python -m pip install -r requirements-forecast.txt
python -m forecasting.cli weather-benchmark --data data/new_weather_data.csv --config configs/forecast.json --report-out artifacts/weather-benchmark.json
python -m forecasting.cli weather-baseline --data data/new_weather_data.csv --config configs/forecast.json --allow-historical
```

`weather-baseline` deliberately refuses stale input unless `--allow-historical` is supplied. It emits transparent baseline values, not the fitted candidates. The trained models in `weather-benchmark` are comparison tools; there is no validated multi-variable model artifact or live forecast endpoint yet.

## Results on the bundled CSV

| Target | Test baseline | Test candidate | Interpretation |
| --- | ---: | ---: | --- |
| Temperature MAE (°C) | 1.1568 | 1.1229 | Candidate loses in 3 of 5 cities |
| Wind-speed MAE (km/h) | 2.3888 | 1.9787 | Candidate improves in all 5 cities |
| Pressure MAE (hPa) | 1.9670 | 1.8732 | Candidate loses in 2 of 5 cities |
| Rain Brier score | 0.1022 | 0.0986 | Small aggregate improvement |

Lower is better for all four scores. These numbers describe only this file and split. The data source, station or grid coordinates, time zone, daily aggregation, and update process are unknown; see the [data card](DATA_CARD.md). They cannot support a real-world forecast accuracy claim.

## Next evidence required

1. Replace or verify the CSV with a documented source. [NOAA GHCN-Daily](https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily) provides station-based daily summaries; [ERA5](https://www.ecmwf.int/en/forecasts/datasets/era5-hourly-data-single-levels-1940-present) is reanalysis and must be labeled as such. These are candidate sources, not the origin of the current file.
2. Define each variable's measurement, unit, location, time zone, daily cutoff, and publication delay. A feature is usable only if it exists by the stated issue time.
3. Collect genuinely later dates and run rolling-origin tests. Compare by city, season, rainy-day prevalence, and missing-data regime before selecting a deployable policy.
4. Decide whether the goal is a station forecast or a grid-cell forecast. The two targets and their evaluation data are different.
