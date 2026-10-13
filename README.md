# City Weather Forecasting

A reproducible historical benchmark for temperature, wind, pressure, and precipitation occurrence across five Iranian city grid cells. The project keeps its original temperature workflow and exploratory dashboard, with their evidence clearly separated from the new sourced data.

## Current Project Status

The four-target benchmark now has a documented 2022–2025 [ERA5 reanalysis snapshot](docs/ERA5_DATA_CARD.md), a retrieval manifest, fixed city coordinates, and a 2025 held-out test year. It compares simple baselines with ridge or logistic regression and reports each city's scores. This is a **retrospective grid-cell experiment**: ERA5 is published after the weather occurred, so these scores are not evidence of a real-time forecast service.

The original `data/new_weather_data.csv` remains for historical reproducibility. Its external source and daily definitions are [unknown](docs/DATA_CARD.md), so its results remain internal diagnostics. The dashboard and console use this older file and calendar-only estimates; neither displays the four-target benchmark.

## Install

Python 3.11 or newer is recommended. From the repository root:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-forecast.txt
```

For the dashboard, console charts, and PDF reporting tests, also install `requirements.txt`.

## Sourced ERA5 benchmark

The committed CSV has 7,305 daily rows: 2022-01-01 through 2025-12-31 for Sanandaj, Yazd, Bandar Abbas, Rasht, and Mashhad. Open-Meteo serves ECMWF ERA5 **gridded reanalysis**. The [data card](docs/ERA5_DATA_CARD.md) explains the four variables, UTC aggregation, grid locations, attribution, and publication delay. The [manifest](data/era5_daily_2022_2025.manifest.json) records each request and the CSV checksum.

```bash
# Recreate a dated source snapshot (requires network access).
python -m forecasting.cli fetch-era5 --start 2022-01-01 --end 2025-12-31 --out data/era5_daily_2022_2025.csv --manifest-out data/era5_daily_2022_2025.manifest.json

# Evaluate against fixed chronological periods, with manifest checksum verified.
python -m forecasting.cli weather-benchmark --data data/era5_daily_2022_2025.csv --manifest data/era5_daily_2022_2025.manifest.json --config configs/era5.json --report-out reports/era5-weather-benchmark.json
```

Training targets end in 2023, validation is 2024, and the held-out test year is 2025. Predictions use day D ERA5 values to estimate day D+1; day D values may not have been published at that time. The candidate models are **comparison tools**, not a selected or deployed forecast. Regenerating the snapshot can produce revised values and a different checksum.

| 2025 test target | Simple baseline | Candidate model |
| --- | ---: | ---: |
| Temperature MAE (°C) | 1.1459 | 1.0215 |
| Wind speed MAE (km/h) | 1.4874 | 1.2753 |
| Sea-level pressure MAE (hPa) | 2.1321 | 1.9725 |
| Precipitation occurrence Brier score | 0.1535 | 0.1245 |

Lower is better. See the [method](docs/WEATHER_FORECASTING.md) and the committed [JSON report with per-city scores](reports/era5-weather-benchmark.json). Weather data by [Open-Meteo](https://open-meteo.com/), based on ECMWF ERA5; daily aggregates were calculated for this project.

## Temperature forecasting commands

Run from the repository root. The default input and split dates are in `configs/forecast.json`; all commands accept explicit paths.

```bash
# Evaluate the five candidates on the same chronological periods.
python -m forecasting.cli benchmark --data data/new_weather_data.csv --config configs/forecast.json

# Benchmark, select on validation, refit on all labelled observations, and save outputs.
python -m forecasting.cli train --data data/new_weather_data.csv --config configs/forecast.json

# Forecast 2025-01-01 from the supplied data, one row per city.
python -m forecasting.cli predict --data data/new_weather_data.csv --model artifacts/temperature_model.joblib
```

`train` writes `artifacts/benchmark.json` and `artifacts/temperature_model.joblib`. The report includes the source file SHA-256, splits, metrics, and selection rule. Artifacts are ignored by Git. Load joblib files only from trusted sources.

Input CSV columns: `Date_Time`, `City`, `Temperature_C` (daily mean in Celsius). Each city must have unique, contiguous midnight daily dates, finite targets, and at least 30 days of history. An invalid or incomplete series is rejected rather than silently filled. Prediction requires at least the history used to train the saved artifact and rejects unseen cities.

### Actual benchmark on the supplied data

Forecasts are issued after today's observation for tomorrow's recorded daily temperature. Examples are partitioned by **target date**: train 2023-01-31 to 2023-12-31 (1,675 rows), validation 2024-01-01 to 2024-06-30 (910), test 2024-07-01 to 2024-12-31 (920). During validation and test, yesterday's actual temperature is available before forecasting the next day. No randomly shuffled time-series split is used.

| Model | Validation MAE (°C) | Test MAE (°C) | Test RMSE (°C) | Note |
|---|---:|---:|---:|---|
| Persistence | 1.5051 | 1.1568 | 1.6839 | Selected forecast policy |
| Seasonal naive, 7 days | 3.4230 | 2.6522 | 3.6169 | Same weekday last week |
| Original calendar linear | 2.9239 | 2.9943 | 3.7948 | Existing implementation, same split |
| Ridge with lags | **1.4937** | **1.1490** | **1.6114** | Best numeric MAE, marginal gain |
| Extra Trees with lags | 1.5521 | 1.1950 | 1.7095 | No gain over persistence |

The selected policy is persistence: ridge improves validation MAE by only 0.8%, below the preconfigured 2% practical improvement threshold. Ridge's test MAE advantage is also under 1%. The test period was not used to choose the policy. sMAPE and R² are included in the machine-readable benchmark; MAPE is avoided because temperatures can be near zero. Two years of data and one held-out period are insufficient to establish a durable performance advantage.

## Legacy CSV weather benchmark

The same four-target benchmark can run against the original CSV for comparison with earlier work. Its source is unknown, so these scores are only internal diagnostics.

```bash
python -m forecasting.cli weather-benchmark --data data/new_weather_data.csv --config configs/forecast.json --report-out artifacts/weather-benchmark.json
python -m forecasting.cli weather-baseline --data data/new_weather_data.csv --config configs/forecast.json --allow-historical
```

The second command is an explicitly dated replay: the bundled file ends on 2024-12-31, so its next day is **2025-01-01**, not tomorrow in 2026. Without `--allow-historical`, the baseline command rejects stale input. These results are internal diagnostics until the [data source and daily measurement definitions](docs/DATA_CARD.md) are verified. See the [forecasting method and measured results](docs/WEATHER_FORECASTING.md).

## Explore and test

```bash
python -m unittest discover -s tests -q
streamlit run scripts/app.py
python scripts/main.py
```

The dashboard reads the bundled daily CSV via a repository-relative path. Its date-picker estimate and the console's regression estimate are **exploratory calendar-only predictions**. The console saves generated output under ignored `artifacts/`. The validated next-day workflow is the CLI above. `Report.md` and `plots/RESULTS.md` are historical project artifacts, not reports from the current benchmark.

## Architecture

- `forecasting/config.py`: validated experiment settings.
- `forecasting/data.py`: CSV ingestion and daily-series validation.
- `forecasting/features.py`: lag, rolling, and calendar features known at issue time.
- `forecasting/experiment.py`: chronological splits, comparable baselines/models, metrics, model selection, save/load, inference.
- `forecasting/cli.py`: temperature and weather benchmark commands.
- `forecasting/weather.py`: four-target validation, issue-time features, baselines, and model comparison.
- `forecasting/open_meteo.py`: fixed-location ERA5 ingestion, UTC aggregation, validation, and provenance manifest.
- `scripts/`: existing dashboard, console, visualizations, reporting, outlier analysis, and calendar model.
- `tests/`: data, leakage, training, persistence, weather benchmark, CLI, dashboard, and legacy-model checks.
- `docs/WORKLOG.md`: decisions, tests, results, and team handoff.

## Next team work

1. Establish provenance for the original CSV if it will remain a supported input. Keep its results separate from the ERA5 experiment.
2. Add a genuine operational experiment using archived forecast runs and independent observations, with issuance times, publication delays, rolling origins, and per-city diagnostics. Never use a later reanalysis value as though it had existed at forecast time.
3. Compare archived forecasts at fixed lead times against station observations or an explicitly named reanalysis reference. Check issue-time availability, rolling test periods, and city-level performance before making a live forecast claim.
4. Decide with the team how to manage the historical 103 MB `data/weather_data.csv` and old virtual-environment blobs still present in Git history. The current tree no longer tracks `.venv`; rewriting shared history would need coordination.

## Collaboration

The previous README credited [Shakiba](https://github.com/shakibasaee) and [Kasra](https://github.com/kasra-2004) as core collaborators. Git history records all contributors and retains their original authorship. New work is described in `docs/WORKLOG.md` and separate commits.
