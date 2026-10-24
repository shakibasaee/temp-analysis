# Weather Forecasting: Archived-Run Evaluation

Can a correction trained on earlier forecasts improve the next-day daily weather forecast for five Iranian city locations? This project evaluates archived ECMWF IFS runs for **temperature, wind speed, sea-level pressure, and precipitation occurrence** at a fixed lead time. It is a reproducible **historical evaluation against ERA5 grid-cell reanalysis**, not a live service or station-validated forecast.

**One measured result:** across 265 city-day cases in 2025, a city-specific temperature bias correction reduced mean absolute error from **1.2887 °C** for the raw IFS forecast to **0.7934 °C** against ERA5. The pressure correction was worse in Rasht and Sanandaj, and precipitation calibration was worse in some cities and quarters. See the complete [report](reports/archived-ifs-2025.json) before interpreting a pooled score.

[Dashboard source](scripts/app.py) · [Archived-forecast data card](docs/ARCHIVED_FORECAST_DATA_CARD.md) · [Evaluation method](docs/ISSUE_TIME_METHOD.md) · [Measured report](reports/archived-ifs-2025.json)

## What works

- A committed sample of 92 weekly archived IFS runs from April 2024 through December 2025, each for five fixed locations, with [request URLs, returned grid coordinates and checksums](data/archived_ifs_weekly.manifest.json).
- Four rolling 2025 test quarters. Each case uses a Monday 00:00 UTC run, a conservative Tuesday 12:00 UTC decision time, and Wednesday's full UTC day as target. Training uses only earlier run data and ERA5 labels assumed available seven days after their target day.
- Raw IFS forecasts are compared with a prior-data bias correction for the three continuous targets. For precipitation, a logistic probability calibration is compared with raw binary occurrence and historical city climatology at **>0 mm** and **≥1 mm** thresholds. Scores are broken down by city and quarter in the report and dashboard.

| 2025 ERA5 reference; 265 city-day cases | Raw IFS | Correction | Metric |
| --- | ---: | ---: | --- |
| Daily mean temperature | 1.2887 | 0.7934 | MAE, °C |
| Daily mean wind speed | 2.4343 | 1.6688 | MAE, km/h |
| Daily mean sea-level pressure | 0.7494 | 0.7183 | MAE, hPa |
| Precipitation occurrence, >0 mm | 0.1170 | 0.1079 | Brier score |
| Precipitation occurrence, ≥1 mm | 0.0830 | 0.0742 | Brier score |

Lower is better. The archived run is a forecast known by initialization time; the reference is [ERA5 reanalysis](docs/ERA5_DATA_CARD.md), published later and from the same broad ECMWF model family. Exact historical delivery timestamps were not archived, and station coverage and quality have not been established for all four daily targets. These limits prevent a real-time or independent-observation skill claim. No correction is promoted for deployment.

## Reproduce

Use Python 3.11 or newer from the repository root:

```bash
python -m pip install -r requirements-forecast.txt
python -m scripts.evaluate_archived_runs
python -m unittest discover -s tests -q
```

To regenerate the archived input from Open-Meteo, run `python -m scripts.fetch_archived_runs`; compare the new manifest and checksum before replacing the committed snapshot. Network responses and historical source revisions can change. To open the dashboard, install `requirements.txt` and run `streamlit run scripts/app.py`.

The dashboard also keeps the [original temperature workflow](docs/README_HISTORY.md) as a clearly labeled historical exploration. Its input has [unverified provenance](docs/DATA_CARD.md) and ends in 2024; its displayed next-day estimate refers to **2025-01-01**. The earlier [ERA5-only four-variable experiment](docs/WEATHER_FORECASTING.md) uses delayed reanalysis as a predictor and remains a retrospective diagnostic, separate from the archived-run evaluation.

Weather data by [Open-Meteo](https://open-meteo.com/), based on ECMWF IFS and ERA5. See the data cards for attribution, terms and definitions. Original collaborator commits remain in Git history.
