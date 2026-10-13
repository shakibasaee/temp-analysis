# Project work log

## 2026-09-28 — Forecasting and repository recovery

**Assessment.** The existing repository had useful modular analysis, a reusable calendar linear model, metrics with bootstrap intervals, a dashboard, and tests. Forecasting was not compared with persistence, forecast horizon and inference inputs were unclear, the console called an obsolete outlier API, and several paths depended on a particular workstation. A random split was still permitted by configuration.

**Data audit.** `data/new_weather_data.csv` has 3,655 rows: 731 consecutive daily dates for each of five cities, 2023-01-01 through 2024-12-31. No duplicate city/date rows or missing temperatures were found. Temperature spans -15.4 to 39.7 °C. Precipitation has 19 missing values; pressure has 10. They are not needed for the present forecast. Per-city lag-1 autocorrelation is 0.962–0.986; lag-365 is 0.800–0.921, consistent with strong persistence and seasonality. Sanandaj's yearly mean rises from 15.08 to 19.03 °C, a shift that deserves source verification. Other data files use different schemas; `data/weather_data.csv` is 103 MB and has one million rows with no documented relationship to this benchmark. Dataset collection method and provenance remain unknown.

**Architecture and decisions.** Added `forecasting/` for ingestion and validation, features, chronological benchmark, selection, persistence, and CLI. The target is the next day's recorded temperature for the same city. Forecasts are issued after the current day's observation. Predictors use current/past temperatures, 3/7/30-day rolling values, target-day calendar cycles, and city; no measured future weather enters features. Dates must be daily and contiguous. Split by **target date**, with training through 2023-12-31, validation through 2024-06-30, and test through 2024-12-31. A model is selected only when its validation MAE improves at least 2% over persistence; this threshold is configured before test evaluation. The final selected policy is saved after fitting on all labelled history. Generated artifacts go to ignored `artifacts/`.

**Experiments.** Compared persistence, 7-day seasonal naive, the existing calendar linear model, ridge with lag/rolling features, and Extra Trees. All use the same 1,675 training, 910 validation, and 920 held-out test target rows. Test results, °C:

| Model | Validation MAE | Test MAE | Test RMSE |
|---|---:|---:|---:|
| Persistence | 1.5051 | 1.1568 | 1.6839 |
| Seasonal naive | 3.4230 | 2.6522 | 3.6169 |
| Calendar linear | 2.9239 | 2.9943 | 3.7948 |
| Ridge with lags | **1.4937** | **1.1490** | **1.6114** |
| Extra Trees with lags | 1.5521 | 1.1950 | 1.7095 |

Ridge's validation improvement over persistence is about 0.8%, so persistence is selected. Its test MAE is about 0.7% lower, not a convincing advantage on one held-out period. sMAPE and R² are also emitted in the JSON report; MAPE is excluded because near-zero Celsius targets make it unstable. More complex models and future weather variables were deferred until data provenance and availability at prediction time are clear.

**Legacy workflows and repository.** Fixed dashboard and default loader paths; rendered figures are closed after use. The dashboard now limits prediction dates to after its supplied history and labels its estimate as calendar-only. Repaired the interactive console's outlier calls, date filters, model invocation, and generated-output directory. The original notebooks, plots, reports, data, and commit authors remain in Git history. Removed 7,053 generated `.venv` files from the current tree in a dedicated commit and ignored future environment/model artifacts. Existing historical blobs were not rewritten.

**Validation performed.** The original 15 unittest tests passed locally with one ReportLab-dependent skip before changes. After installing the declared ReportLab dependency, `python -m unittest discover -s tests -q` passed all 22 tests, including PDF reporting; a Streamlit AppTest rendered the dashboard without exceptions; the interactive console completed on `data/new_weather_data.csv` with a future date; `benchmark`, `train`, and `predict` CLI commands completed on the bundled dataset; `ruff check` passed for new and touched Python files; `ruff format --check` passed for new forecasting files; `python -m compileall` and `git diff --check` passed.

**Known issues.** The dataset is only two years long and externally unverified. The dashboard/console use the older calendar model, while the CLI holds the validated next-day workflow. Large historic files, including the 103 MB CSV and prior `.venv` commits, remain in Git history; reducing history size requires a team decision. The old console's cleaning rules discard rows with missing optional weather variables, unlike the new forecasting loader.

**Next steps.** Confirm data provenance and collect later observations for rolling-origin evaluation. Add only weather inputs that are actually available when forecasts are issued. Decide on storage/LFS or archival for large historical data with the team.

## 2026-10-13 — Experimental multi-variable weather benchmark

**Scope.** Added a separate next-day benchmark for temperature, wind speed, pressure, and rain occurrence probability. The original temperature policy and exploratory dashboard remain separate. The weather CLI compares persistence (or a 30-day wet-frequency baseline) with ridge regression (or logistic regression for rain) on chronological validation and test periods. Candidate models are not deployed as a live forecast.

**Data contract.** Features use measurements no later than the issue day. Missing precipitation and pressure values are retained, excluded only when they are the target or required baseline, and imputed within the model's training pipeline when used as predictors. A new data card records the bundled CSV checksum, coverage, missingness, and unknown provenance, time zone, aggregation, and coordinates.

**Internal results.** On the bundled file's 2024-07-01 to 2024-12-31 test period, aggregate baseline/candidate scores were: temperature MAE 1.1568/1.1229 °C; wind MAE 2.3888/1.9787 km/h; pressure MAE 1.9670/1.8732 hPa; rain Brier 0.1022/0.0986. Temperature candidate performance was worse in three cities; pressure was worse in two. These scores are internal diagnostics, not evidence of field accuracy.

**Operational guard.** The bundled file ends in 2024. `weather-baseline` refuses to call its 2025-01-01 output a current forecast unless the user explicitly chooses `--allow-historical`. The output contains only baseline forecasts. A source-backed later dataset and rolling-origin evaluation remain necessary before model selection or a public accuracy claim.
