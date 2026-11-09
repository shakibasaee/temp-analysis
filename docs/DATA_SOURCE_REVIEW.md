# Historical temperature source review

Reviewed 2026-11-06 for an educational, noncommercial application covering
`Bandar_Abbas`, `Mashhad`, `Rasht`, `Sanandaj`, and `Yazd`. The proposed future
targets are local-calendar-day 2 m air temperature mean, minimum, and maximum,
in °C. The shipped next-day `Temperature_C` benchmark has **unknown provenance
and an unknown target definition**; this review does not assign it a provider.

| Source | Three daily targets and location coverage | Freshness / access | Rights and limitation | Assessment |
|---|---|---|---|---|
| [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api), pinned to ERA5 | `temperature_2m_mean`, `_min`, `_max` are 2 m air temperature aggregates. ERA5 is global, gridded, 0.25°; request `timezone=Asia/Tehran` for local daily boundaries. The probe below found all three values on all 731 requested days in each proposed city grid point. | Historical ERA5 is updated daily with approximately five days' delay. The free API needs no key for noncommercial use. | [Terms](https://open-meteo.com/en/terms) allow free noncommercial use subject to limits, and API data is CC BY 4.0 with attribution. These are **model reanalysis estimates**, not independent station observations. Grid points can differ from city centres, especially near coasts and mountains. | Best **candidate for a reproducible prototype dataset**. Do not describe it as observed ground truth or proof of live 30-day skill. |
| [Meteostat daily point API](https://dev.meteostat.net/api/point/daily) / station data | `tavg`, `tmin`, `tmax` exist. Point data combines nearby stations; missing values are substituted with model data by default (`model=true`). Individual Iranian station coverage and observation-only gaps are **not yet measured**. | Daily data typically arrives after 1–7 days, sometimes later. JSON API requires a RapidAPI key; [API docs](https://dev.meteostat.net/api) list 500 free monthly calls. | [Developer license](https://dev.meteostat.net/license) says CC BY 4.0 and requires provider attribution, but the [public support page](https://meteostat.net/support) says CC BY-NC 4.0. That contradiction needs clarification before redistributing a dataset. | Candidate for a separate observation-oriented check only after station inventory, `model=false` gap audit, provider attribution, and license clarification. |
| [Copernicus ERA5 daily statistics](https://cds.climate.copernicus.eu/datasets/derived-era5-single-levels-daily-statistics?tab=overview) | Global ERA5 daily mean/max/min can be derived from hourly 2 m air temperature with an explicit UTC shift and sampling interval. Coarser 0.25° grid. | Daily product has about six days' delay. Requires a CDS account and license acceptance for retrieval. | CDS lists a CC BY license. Reanalysis is model-derived, so it is not an independent observational check against Open-Meteo ERA5. | Useful direct upstream cross-check; more retrieval and aggregation work for this small educational app. |

## Reproducible coverage check

The city-centre candidates below came from the [Open-Meteo geocoding API](https://open-meteo.com/en/docs/geocoding-api) on 2026-11-06. IDs distinguish the intended cities from same-name places. They are **provisional grid-point mappings**, not weather stations. The archive response reports its actual grid coordinates, which the probe prints.

| City | Geocoding ID | Requested latitude, longitude |
|---|---:|---|
| Bandar Abbas | 141681 | 27.1865, 56.2808 |
| Mashhad | 124665 | 36.29807, 59.60567 |
| Rasht | 118743 | 37.27611, 49.58862 |
| Sanandaj | 117574 | 35.31495, 46.99883 |
| Yazd | 111822 | 31.89722, 54.3675 |

From the repository root, with internet access:

```bash
python -m scripts.audit_open_meteo --start 2023-01-01 --end 2024-12-31
```

The read-only script requests `models=era5`, `timezone=Asia/Tehran`, Celsius,
and the three daily variables in one multi-location API call. It checks dates,
units, missing values, and `min <= mean <= max`; it does not save source rows.
Observed 2026-11-06: **731 daily rows per city, zero missing values for each
target, zero ordering violations**. This is 3,655 city-days and 10,965
temperature values for 2023-01-01 through 2024-12-31. API responses may be
revised; record retrieval date and source parameters when building a dataset.

## Data card and decision gate

- **Purpose:** education and reproducible development, then a properly scoped
  1–30-day backtest. This coverage check is not that backtest.
- **Measurement:** Open-Meteo ERA5 daily aggregates are gridded estimates of
  2 m air temperature. They are not the existing CSV's known source, station
  observations, or independent truth for ERA5-based predictors.
- **Rights:** if source values are committed or displayed, preserve attribution
  to Open-Meteo and its underlying provider, the CC BY 4.0 link, retrieval
  metadata, and any transformations. Recheck service terms if use changes.
- **Unresolved:** city/station identity, independent observation quality,
  issue-time data availability, any later ERA5 revisions, and performance
  separately by horizon, target, and city. Choose an observation source before
  making real-world accuracy claims.
- **Decision:** Open-Meteo ERA5 is suitable for a labeled prototype input and
  pipeline validation. The existing benchmark is unchanged. No three-target
  or 30-day forecast is shipped or validated by this review.

The repository's [Issue #1](https://github.com/shakibasaee/temp-analysis/issues/1)
contains an unfilled bug-report template (no reproduction steps, expected or
actual behavior). It supplies no additional evidence about data provenance or
an app defect; a concrete reproduction would be needed to investigate it.

## Implemented research snapshot

On 2026-11-09, the proposed Open-Meteo ERA5 input was retrieved for
2020-01-01 through 2025-12-31 as `data/era5_five_cities.csv`, with a separate
provenance manifest. All five points had 2,192 dates and all three targets,
without missing values or minimum/mean/maximum ordering violations. The
[technical report](PROJECT_REVIEW_FA.md) describes the independent 1–30-day
research backtest. This does not resolve the missing station-observation check
or the old CSV's provenance.
