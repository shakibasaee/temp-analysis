# Day 1 baseline lock — 6 November 2026

This record freezes the current **one-day, single-target historical benchmark** before work on the requested 1–30-day, three-target product. It is an integrity and reproducibility reference, not proof of real-world forecast quality.

## Inputs and environment

| Item | Recorded value |
|---|---|
| Source file | `data/new_weather_data.csv`, 150,898 bytes in the LF Git checkout |
| Source SHA-256 | `da870b3b780aed7edd1a64b75d54bd29fef768bc78538047214c2679539f3517` (Git blob and LF checkout) |
| Configuration | `configs/forecast.json` |
| Config SHA-256 | `34b8362e23da99b59db0e80c852ddb8a95765708a78618db408b575e30a8d5f7` |
| Configuration values | Train through 2023-12-31; validation through 2024-06-30; seed 42; at least 30 history days; 2% minimum relative MAE gain for model selection. |
| Dataset scope | 3,655 rows; five cities; 2023-01-01 through 2024-12-31. Source provider, station IDs, temperature definition, timezone, and reuse rights remain unknown. |
| Local runtime | Python 3.13.3; NumPy 2.2.5; pandas 2.3.1; scikit-learn 1.7.2; Streamlit 1.48.1; Matplotlib 3.10.1; joblib 1.5.2. These are observed local versions, not a lockfile. |
| CI runtime | GitHub Actions uses Python 3.11 and installs `requirements.txt` plus Ruff 0.7.1. Exact resolved versions may differ from the local runtime. |

## Reproduction commands

Run from the repository root with dependencies from `requirements.txt`:

```bash
python -m unittest discover -s tests -q
python -m forecasting.cli train --data data/new_weather_data.csv --config configs/forecast.json --model-out artifacts/day1_model.joblib --report-out artifacts/day1_benchmark.json
```

The second command writes ignored local artifacts. The report includes input SHA-256, split dates and counts, model metrics, and the selected policy. The new `test_bundled_one_day_baseline_snapshot` test fails if the source hash, split counts, selected policy, or two baseline test MAEs change without a reviewed update.

The first CI run of this snapshot found a Windows/Linux line-ending mismatch: the old Windows checkout of the CSV had CRLF bytes and SHA-256 `361491c9f30c3a60ee0d86e5d54bcbfab9492e9204f7959ad80505fae2ed1c71`, while the Git blob and Linux checkout were LF with the hash above. The records were identical. `.gitattributes` now requires LF for the benchmark CSV and configuration so a fresh checkout yields the same byte-level source hash on both systems.

## Observed result

| Period | Target dates | Rows |
|---|---|---:|
| Initial train | 2023-01-31 to 2023-12-31 | 1,675 |
| Rolling validation | 2024-01-01 to 2024-06-30 | 910 |
| Held-out test | 2024-07-01 to 2024-12-31 | 920 |

| Candidate | Validation MAE (°C) | Held-out MAE (°C) |
|---|---:|---:|
| Persistence | 1.5051 | 1.1568 |
| Seven-day seasonal naive | 3.4230 | 2.6522 |
| Existing calendar regression | 2.9260 | 2.9943 |
| Ridge with lags | 1.4916 | 1.1490 |
| Extra Trees with lags | 1.5744 | 1.1950 |

Persistence remains selected because Ridge's validation gain is below the configured 2% threshold. The 2024 holdout did not choose the policy. The local suite passed **26 tests** on 6 November 2026 and the scoped Ruff lint/format checks passed. The same tests and checks passed on Python 3.11 in [GitHub CI run 42263349964](https://github.com/shakibasaee/temp-analysis/actions/runs/42263349964), including the bundled baseline snapshot test.

## Change control

If the dataset, configuration, or evaluation code changes, keep the previous benchmark traceable, record a new hash and rationale, and re-run the full chronological evaluation. Do not adjust the 2024 holdout or delete difficult rows to improve the reported result. The benchmark does not validate 2–30-day forecasts or daily mean/minimum/maximum targets.
