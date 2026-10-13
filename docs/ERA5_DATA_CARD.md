# Data card: Open-Meteo ERA5 daily snapshot

This is a separate, documented replacement for the original `new_weather_data.csv`. It is **ECMWF ERA5 gridded reanalysis served by Open-Meteo**, not measurements from five city weather stations. City names identify fixed requested coordinates; the actual ERA5 grid-cell centres returned by the API are recorded in the adjacent manifest.

The committed snapshot has **7,305 rows**, one for each of five cities on every UTC day from 2022-01-01 through 2025-12-31. All four target columns are complete. Its CSV SHA-256 is `68bb83a25acce304315edfdbbdd0cadac7575874bd75b94655d941f989fc0362`.

| City label | Requested centre (lat, lon) | Returned ERA5 grid centre (lat, lon) |
| --- | --- | --- |
| Sanandaj | 35.31495, 46.99883 | 35.25, 47.00 |
| Yazd | 31.89722, 54.36750 | 32.00, 54.25 |
| Bandar Abbas | 27.18650, 56.28080 | 27.25, 56.25 |
| Rasht | 37.27611, 49.58862 | 37.25, 49.50 |
| Mashhad | 36.29807, 59.60567 | 36.25, 59.50 |

| Field | Definition |
| --- | --- |
| Source | [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), model `era5` |
| Originating model | [ECMWF ERA5](https://www.ecmwf.int/en/forecasts/datasets/era5-hourly-data-single-levels-1940-present), approximately 0.25° grid |
| Retrieval | `python -m forecasting.cli fetch-era5`; request URLs, retrieval time, grid coordinates and CSV SHA-256 are stored in the manifest |
| Time convention | One row per city per **UTC** day. Instantaneous variables use 00:00 through 23:00 hourly values; precipitation uses the API's daily UTC total. Incomplete days are rejected. |
| Temperature | Arithmetic mean of hourly 2 m air temperature, °C |
| Precipitation | API `precipitation_sum`, including rain and snow, mm; `> 0` defines an occurrence target, not rain specifically |
| Wind speed | Arithmetic mean of hourly 10 m wind speed, km/h |
| Pressure | Arithmetic mean of hourly **sea-level** pressure, hPa |
| Availability | Open-Meteo documents ERA5 with an approximately five-day publication delay; requests end at least seven days before the run date |
| License and use | Attribute [Open-Meteo and its data sources](https://open-meteo.com/en/licence). The [free API terms](https://open-meteo.com/en/terms) limit use to non-commercial purposes. |

The generated CSV is a **fixed snapshot**, not automatically refreshed. The request manifest makes it reproducible and identifies the grid cells, but reanalysis values may be revised when fetched later. The SHA-256 verifies the committed snapshot, not future API responses.

This source is suitable for a reproducible **retrospective grid-cell benchmark**. ERA5's delay means day D reanalysis is generally unavailable immediately after day D, so the next-day experiment is **not an operational forecast simulation**. A real forecast evaluation needs archived model runs with their issuance times and independent observations or a clearly named reanalysis reference. [Open-Meteo Previous Runs](https://open-meteo.com/en/docs/previous-runs-api) is one candidate for fixed lead-time archived forecasts; [NOAA SSOD](https://www.ncei.noaa.gov/products/global-historical-climatology-network-hourly/synoptic-summary-of-the-day) is a candidate station source, but station coverage, reporting delay, missingness and precipitation quality need checking per city.

To regenerate the exact date range, use the command in the README. Compare row counts, units, grid coordinates, and checksum before replacing the committed snapshot. Do not join this reanalysis file to the undocumented CSV by city/date and call them the same measurement.
