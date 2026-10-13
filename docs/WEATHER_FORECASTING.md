# Retrospective four-target weather benchmark

This workflow compares simple baselines with candidate models on two **separate** inputs. The primary input is a documented 2022–2025 [ERA5 grid-cell snapshot](ERA5_DATA_CARD.md). The original 2023–2024 [CSV](DATA_CARD.md) has unknown provenance and is retained for historical comparison. Neither experiment is a live weather service.

## Forecast contract

For each city, predictors describe day D or earlier; targets describe day D+1. Calendar values are derived from the known target date. In the ERA5 experiment, day D values are treated as if available immediately after day D. ERA5 has a publication delay, so this is a **retrospective target prediction**, not an operational issue-time simulation.

| Target for D+1 | Baseline | Candidate | Primary score |
| --- | --- | --- | --- |
| Temperature (°C) | Day D temperature | Ridge regression | MAE (°C) |
| Wind speed (km/h) | Day D wind speed | Ridge regression | MAE (km/h) |
| Pressure (hPa) | Day D pressure | Ridge regression | MAE (hPa) |
| Precipitation occurrence, precipitation > 0 mm | Wet-day frequency in the previous 30 days | Logistic regression | Brier score |

The precipitation-occurrence output is a probability, not a precipitation amount. Missing precipitation and pressure values are retained as missing. Rows without a target or baseline are excluded **for that target only** and counted in the report. Candidate models impute missing predictors using training-period medians. City identity, recent measurements, rolling summaries, and target-day calendar cycles are the model features.

The sourced experiment trains through 2023-12-31, validates on 2024, and tests on 2025. The legacy experiment trains through 2023-12-31, validates through 2024-06-30, and tests on the second half of 2024. For each, the candidate is fit on training data for validation, then refit on training plus validation for test. During evaluation, each day's target values may be used as the next day's predictors. No test labels enter the corresponding model fit. The JSON report includes every city's scores. There is only one held-out test period per experiment, not rolling-origin or external validation.

## Run

```bash
python -m pip install -r requirements-forecast.txt
python -m forecasting.cli weather-benchmark --data data/era5_daily_2022_2025.csv --manifest data/era5_daily_2022_2025.manifest.json --config configs/era5.json --report-out reports/era5-weather-benchmark.json
python -m forecasting.cli weather-benchmark --data data/new_weather_data.csv --config configs/forecast.json --report-out artifacts/weather-benchmark.json
python -m forecasting.cli weather-baseline --data data/new_weather_data.csv --config configs/forecast.json --allow-historical
```

`weather-baseline` deliberately refuses stale input unless `--allow-historical` is supplied. It emits transparent baseline values, not the fitted candidates. The trained models in `weather-benchmark` are comparison tools; there is no validated multi-variable model artifact or live forecast endpoint yet.

## ERA5 2025 test results

| Target | Test baseline | Test candidate | City comparison |
| --- | ---: | ---: | --- |
| Temperature MAE (°C) | 1.1459 | 1.0215 | Candidate lower in 5 of 5 cities |
| Wind-speed MAE (km/h) | 1.4874 | 1.2753 | Candidate lower in 5 of 5 cities |
| Sea-level pressure MAE (hPa) | 2.1321 | 1.9725 | Candidate lower in 5 of 5 cities |
| Precipitation occurrence Brier score | 0.1535 | 0.1245 | Candidate lower in 5 of 5 cities |

Lower is better. Weather data by [Open-Meteo](https://open-meteo.com/), based on ECMWF ERA5 and aggregated for this project. These are scores **against ERA5 reanalysis itself**, not station-observation accuracy or skill against an operational weather forecast. The source has a publication delay and the candidate models use values that would not yet have been published at the assumed issue time. The report's city scores and checksum support reproduction of this historical result, not a live accuracy claim.

## Results on the original bundled CSV

| Target | Test baseline | Test candidate | Interpretation |
| --- | ---: | ---: | --- |
| Temperature MAE (°C) | 1.1568 | 1.1229 | Candidate loses in 3 of 5 cities |
| Wind-speed MAE (km/h) | 2.3888 | 1.9787 | Candidate improves in all 5 cities |
| Pressure MAE (hPa) | 1.9670 | 1.8732 | Candidate loses in 2 of 5 cities |
| Precipitation Brier score | 0.1022 | 0.0986 | Small aggregate improvement |

Lower is better for all four scores. These numbers describe only this file and split. The data source, station or grid coordinates, time zone, daily aggregation, and update process are unknown; see the [data card](DATA_CARD.md). They cannot support a real-world forecast accuracy claim.

## Next evidence required

1. Use [archived fixed-lead forecasts](https://open-meteo.com/en/docs/previous-runs-api) or preserved individual model runs as predictors, with explicit issuance times. Compare to independent station observations where coverage is adequate, or name ERA5 as the reference.
2. Check reporting delay and availability of each feature at issuance. ERA5 values cannot serve as immediately available day D features in a live forecast.
3. Use several rolling test origins, stratify by city and season, and examine event reliability and calibration before selecting a candidate policy.
4. Investigate [NOAA SSOD](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly/synoptic-summary-of-the-day) stations for the five cities. Its UTC day is consistent, but NOAA notes that synoptic precipitation can be underreported; check station mapping, coverage and missingness before using it as truth.
