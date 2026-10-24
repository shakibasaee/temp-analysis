# Data card: archived IFS weekly forecasts

This dataset is an archived **forecast**, distinct from both the [ERA5 reference](ERA5_DATA_CARD.md) and the [original unsourced CSV](DATA_CARD.md). It contains 460 rows: one 48–71 hour daily forecast for each of five locations from each of 92 Monday 00 UTC ECMWF IFS HRES runs, 2024-04-01 through 2025-12-29. The target is the Wednesday UTC day. The committed CSV SHA-256 is `e9dad84af1ad905143217412eb047c07110badd6f07beb6fa35dc03aa2f02765`.

| Field | Definition |
| --- | --- |
| Source | [Open-Meteo Single Runs API](https://open-meteo.com/en/docs/single-runs-api), `models=ecmwf_ifs` (ECMWF IFS HRES 9 km archived run) |
| Retrieval | 2026-10-24 UTC; [manifest](../data/archived_ifs_weekly.manifest.json) lists every exact URL, UTC run time, response SHA-256, returned grid coordinate, and final CSV SHA-256 |
| Model initialization | Monday 00:00 UTC (`run_utc`); preserved by the archive |
| Declared decision time | Tuesday 12:00 UTC (`issue_utc`), **36 hours after initialization** |
| Target | Wednesday 00:00–23:59 UTC (`target_date_utc`), a fixed 48–71 hour forecast lead from initialization; daily aggregates use `timezone=UTC` |
| Variables | Mean 2 m temperature (°C), mean 10 m wind speed (km/h), mean sea-level pressure (hPa), daily precipitation total (mm, rain plus snow) |
| Completeness | All five cities and four target fields required for each run; missing, nonfinite, negative precipitation/wind, wrong units/timezone, wrong target dates, and duplicate keys are rejected |
| Use and license | Attribute [Open-Meteo and its data sources](https://open-meteo.com/en/licence); the [free API terms](https://open-meteo.com/en/terms) are non-commercial |

| City | Requested centre (lat, lon) | Returned forecast grid centre for first run (lat, lon) |
| --- | --- | --- |
| Sanandaj | 35.31495, 46.99883 | 35.32513, 46.95652 |
| Yazd | 31.89722, 54.36750 | 31.880491, 54.368233 |
| Bandar Abbas | 27.18650, 56.28080 | 27.240772, 56.28763 |
| Rasht | 37.27611, 49.58862 | 37.223198, 49.58940 |
| Mashhad | 36.29807, 59.60567 | 36.309315, 59.648438 |

The manifest records each returned coordinate, since grids or upstream versions may change. The ERA5 grid centres differ from these forecast grid centres. City labels identify sampling locations, not station observations.

The API's `run` timestamp is **initialization**, not publication. [Open-Meteo states](https://open-meteo.com/en/docs/single-runs-api) global runs are typically available about four to six hours later. A 36-hour allowance is conservative, but the archive does not prove the exact historical delivery time of every run. This is a historical decision-time simulation, not evidence that a particular client received each run at 12 UTC.

The [reference CSV](../data/era5_daily_2022_2025.csv) is a fixed ERA5 snapshot obtained through a different Open-Meteo API. ERA5 is published with an approximately five-day delay, so it is used only as a delayed label and cannot enter predictors at issue time. Its grid values may be revised later. Forecast and reference share the ECMWF model ecosystem; agreement with ERA5 is weaker evidence than independent station observations.

**Station assessment:** [NOAA ISD station metadata](https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv) lists nearby candidates for all five cities, including Sanandaj, Yazd, Bandar Abbas, Rasht and Mashhad. Metadata alone does not establish complete daily coverage, reporting latency, consistent precipitation accumulation, or quality for the four target definitions in 2025. No station values were mixed into the reference or scored. A station benchmark requires those checks and a documented station-to-grid comparison first.

Regenerate with `python -m scripts.fetch_archived_runs` and compare the generated manifest and checksum before replacing this snapshot. Response SHA-256 values verify bytes retrieved during this run, while the CSV hash verifies the committed processed artifact; neither guarantees later API responses are identical.
