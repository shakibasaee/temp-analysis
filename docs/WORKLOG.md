# Project work log

## 2026-10-11 — Reproducibility review

**Plan.** Audit the shipped dashboard, CLI, legacy console, data, dependencies, tests, and CI; describe feature boundaries accurately; provide a source-independent demo dataset; then run the forecast, dashboard, and tests. Keep existing unrelated files and Git history intact.

**Changes.** Documented the actual status of CSV input, anomaly analysis, PDF export, configuration, live weather, and forecasting. Added a deterministic two-city synthetic CSV generator and a dashboard data-path override. Removed the remaining workstation path from the standalone outlier script. Benchmark JSON now records validation and test row counts per model. Scoped CI lint and format checks to the supported forecast/dashboard path, and added tests for the sample schema and identical benchmark row counts. No virtual environment is tracked in this tree; `.venv/` remains ignored.

**Verification.** On the bundled 3,655-row, five-city dataset, all candidates used 910 validation and 920 held-out test targets. Calendar linear test MAE was 2.9943 C, seasonal naive was 2.6522 C, and selected persistence was 1.1568 C. The data provider, measurement definition, and redistribution rights remain unknown. The synthetic 1,462-row demo generated, trained, predicted, and rendered in Streamlit without exceptions; its scores demonstrate the pipeline only. The 24-test suite and scoped Ruff lint/format checks passed. The standalone outlier module wrote to ignored `artifacts/plots/`.

**Remaining blockers for promotion.** Confirm the bundled data's provider/license and a project code license; collect genuinely later observations; resolve the large legacy CSV's storage policy. The app has no upload widget, live weather, anomaly view, or PDF export.

## 2026-10-07 — Rolling evaluation and dashboard forecast

**Plan.** First add expanding monthly validation folds and per-city held-out metrics. Then make the dashboard consume the selected next-day policy. Finally document the bundled data's provenance gap and validate the complete path.

**Changes and decisions.** Validation now uses six monthly folds from January through June 2024. Each fold trains on labels strictly before that month; earlier validation months become training history only after they have elapsed. Candidate selection uses pooled out-of-fold MAE with the existing 2% gain requirement. The July–December 2024 test remains held out until selection. The report includes fold dates/rows, fold metrics, and per-city test metrics. The dashboard calls the same benchmark, final fit, and prediction functions as the CLI; Streamlit caches the fitted result until the data or config file changes. It displays the selected model, per-city forecast and historical held-out error, and warns when bundled observations are stale. The older console model remains available.

**Experiments.** On the bundled five-city data, pooled rolling-validation MAE (°C) was persistence 1.5051, seasonal naive 3.4230, calendar linear 2.9260, ridge with lags 1.4916, and Extra Trees with lags 1.5744. Held-out test MAE remains 1.1568, 2.6522, 2.9943, 1.1490, and 1.1950 respectively. Ridge's roughly 0.9% validation gain remains below the 2% selection threshold, so persistence is still selected. Its per-city test MAE is 0.5658 Bandar_Abbas, 1.6630 Mashhad, 0.9859 Rasht, 1.2799 Sanandaj, and 1.2897 Yazd.

**Validation.** The expanded suite passed 23 tests locally, including fold-boundary checks and a Streamlit smoke test with default and multi-city selections. Ruff lint/format checks and the CLI benchmark also passed. The bundled data ends on 2024-12-31; the app's next-day output is for 2025-01-01 and is explicitly marked historical.

**Known issues and next steps.** Data source, measurement definition, timezone, and update process are still unknown; see `data/README.md`. Acquire later trusted observations before drawing stronger model conclusions. After that, assess calibrated forecast intervals and add point-in-time available weather covariates only if they improve rolling validation. Large historical Git data still needs a team storage decision.

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
