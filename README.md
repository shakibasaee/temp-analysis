# Temperature Analysis Platform

Daily city temperature analysis with a Streamlit dashboard and a reproducible **one-day-ahead** forecasting benchmark. The historical notebooks, plots, reports, and data remain in the repository.

## Current Project Status

Active development resumed on 2026-09-28; the latest update is 2026-10-07. The forecasting workflow validates daily city data, compares five models across expanding monthly validation folds and a held-out test, saves a selected forecast policy, and predicts the day after the latest observation. The dashboard shows that selected next-day forecast and per-city historical error alongside exploratory charts. The interactive console still uses the older calendar-only model.

The supplied `data/new_weather_data.csv` contains 3,655 daily observations across five cities from 2023-01-01 through 2024-12-31. Temperature targets and dates are complete; precipitation has 19 missing values and pressure has 10. The forecasting workflow uses only city, date, and previously observed temperature, so no future weather measurements are assumed. Dataset provenance and external validity are not documented. Treat the results as an internal benchmark, not a deployed weather service.

## Install

Python 3.11 or newer is recommended. From the repository root:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements-forecast.txt
```

For the dashboard, console charts, and PDF reporting tests, also install `requirements.txt`.

## Forecasting commands

Run from the repository root. The default input and split dates are in `configs/forecast.json`; all commands accept explicit paths.

```bash
# Evaluate the five candidates on the same chronological periods.
python -m forecasting.cli benchmark --data data/new_weather_data.csv --config configs/forecast.json

# Benchmark, select on validation, refit on all labelled observations, and save outputs.
python -m forecasting.cli train --data data/new_weather_data.csv --config configs/forecast.json

# Forecast 2025-01-01 from the supplied data, one row per city.
python -m forecasting.cli predict --data data/new_weather_data.csv --model artifacts/temperature_model.joblib
```

`train` writes `artifacts/benchmark.json` and `artifacts/temperature_model.joblib`. The report includes the source file SHA-256, monthly validation folds, per-city test metrics, and selection rule. Artifacts are ignored by Git. Load joblib files only from trusted sources.

Input CSV columns: `Date_Time`, `City`, `Temperature_C` (recorded daily temperature in Celsius). Each city must have unique, contiguous midnight daily dates, finite targets, and at least 30 days of history. An invalid or incomplete series is rejected rather than silently filled. Prediction requires at least the history used to train the saved artifact and rejects unseen cities. See `data/README.md` for the dataset provenance gap.

### Actual benchmark on the supplied data

Forecasts are issued after today's observation for tomorrow's recorded daily temperature. Examples are partitioned by **target date**: initial train 2023-01-31 to 2023-12-31 (1,675 rows), rolling validation 2024-01-01 to 2024-06-30 (six monthly folds, 910 rows), and held-out test 2024-07-01 to 2024-12-31 (920). Each validation fold trains on all earlier targets. During validation and test, yesterday's actual temperature is available before forecasting the next day. No randomly shuffled time-series split is used.

| Model | Validation MAE (°C) | Test MAE (°C) | Test RMSE (°C) | Note |
|---|---:|---:|---:|---|
| Persistence | 1.5051 | 1.1568 | 1.6839 | Selected forecast policy |
| Seasonal naive, 7 days | 3.4230 | 2.6522 | 3.6169 | Same weekday last week |
| Original calendar linear | 2.9260 | 2.9943 | 3.7948 | Existing implementation, same folds |
| Ridge with lags | **1.4916** | **1.1490** | **1.6114** | Best numeric MAE, marginal gain |
| Extra Trees with lags | 1.5744 | 1.1950 | 1.7095 | No gain over persistence |

The selected policy is persistence: ridge improves pooled rolling-validation MAE by about 0.9%, below the preconfigured 2% practical improvement threshold. Ridge's test MAE advantage is also under 1%. The test period was not used to choose the policy. The selected model's held-out MAE varies by city: Bandar_Abbas 0.5658, Mashhad 1.6630, Rasht 0.9859, Sanandaj 1.2799, and Yazd 1.2897 °C. sMAPE and R² are included in the machine-readable benchmark; MAPE is avoided because temperatures can be near zero. Two years of data remain insufficient to establish a durable performance advantage.

## Explore and test

```bash
python -m unittest discover -s tests -q
streamlit run scripts/app.py
python scripts/main.py
```

The dashboard reads the bundled daily CSV via a repository-relative path, applies the same selection rule as the CLI, and displays a next-day forecast after the latest observation. Because the bundled data ends on 2024-12-31, the app warns that its 2025-01-01 estimate is historical rather than current weather. The console's regression estimate remains exploratory and calendar-only; its generated output goes under ignored `artifacts/`. `Report.md` and `plots/RESULTS.md` are historical project artifacts, not reports from the current benchmark.

## Architecture

- `forecasting/config.py`: validated experiment settings.
- `forecasting/data.py`: CSV ingestion and daily-series validation.
- `forecasting/features.py`: lag, rolling, and calendar features known at issue time.
- `forecasting/experiment.py`: chronological splits, comparable baselines/models, metrics, model selection, save/load, inference.
- `forecasting/cli.py`: benchmark, train, predict commands.
- `scripts/`: existing dashboard, console, visualizations, reporting, outlier analysis, and calendar model.
- `tests/`: data, leakage, training, persistence, CLI, dashboard, and legacy-model checks.
- `docs/WORKLOG.md`: decisions, tests, results, and team handoff.

## Next team work

1. Establish provenance, collection method, units, and update process for the five-city dataset. Validate on genuinely later observations and several rolling origins.
2. Add reliable observations or forecasts of humidity, pressure, wind, cloud, precipitation, and solar radiation before testing them as predictors. Same-day *future* observations must never enter a forecast.
3. Decide with the team how to manage the historical 103 MB `data/weather_data.csv` and old virtual-environment blobs still present in Git history. The current tree no longer tracks `.venv`; rewriting shared history would need coordination.

## Collaboration

The previous README credited [Shakiba](https://github.com/shakibasaee) and [Kasra](https://github.com/kasra-2004) as core collaborators. Git history records all contributors and retains their original authorship. New work is described in `docs/WORKLOG.md` and separate commits.
