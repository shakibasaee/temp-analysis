# Forecast product contract — draft, 6 November 2026

## Agreed intent

- The first educational, noncommercial version supports the five current cities: `Bandar_Abbas`, `Mashhad`, `Rasht`, `Sanandaj`, and `Yazd`.
- A user selects one of these cities and a future calendar date **1–30 days after the forecast issue date**.
- The intended output is daily **mean, minimum, and maximum temperature** in °C for that city and date.
- Evaluate each target and horizon using **MAE in °C** and the **percentage of forecasts with absolute error at most 2 °C**. Always show the number of evaluated predictions. Aggregate and per-city results are both required.
- Past dates are outside the first forecast request flow and must be rejected by that input. Historical observations can remain available in a separately labeled exploration view.

## What the repository currently supports

The shipped path forecasts only **one day ahead** for a single field named `Temperature_C`, after the latest observation. The bundled file ends on 2024-12-31 and has unverified provenance. Its field may be a daily mean or a point reading; neither has been established. The current output cannot be relabeled as daily mean, minimum, or maximum. No 2–30-day accuracy or three-target capability has been measured or implemented.

## Decisions required before implementation

| Decision | Required evidence or answer | Current status |
|---|---|---|
| Exact target definitions | Provider definitions for daily mean/min/max, observation method, units, and whether the day is local civil time. | Unknown |
| Forecast issue time | When a day's observations become available, the issue timestamp and timezone, and the latest data a prediction may use. | Unknown |
| City identity | Station or grid-cell mapping and what happens when a city has multiple measurement locations. | Unknown |
| Source rights and continuity | Provider, license, permitted storage/display, historical coverage, update latency, and 2025+ observations. | Unknown |
| Intended use | Educational and noncommercial initially; recheck source terms before public display or any commercial change. | Agreed |
| Missing or stale data behavior | Whether to reject a request, show an older labeled estimate, or offer an alternative source; never silently invent observations. | Open |
| Product success threshold | Minimum acceptable MAE and within-±2 °C rate for each horizon/target; set before examining future test results. | Open |

## Evaluation contract to implement after data approval

For an issue date `t` and requested date `t+h` (`1 <= h <= 30`), a prediction may use only inputs available by `t`. Actual observations for `t+1` through `t+h` are unavailable at issue time, even if a historical backtest file contains them. Use rolling issue dates, fit every preprocessing step on each training window, and reserve a later time range for a final untouched assessment. Compare each horizon and target with a baseline built from information available at the same issue date. Report MAE, within-±2 °C rate, and counts by horizon and city; do not select a model using the final test period.

The UI must show the issue date, target date, horizon, data freshness, units, and the relevant historical evaluation scope. It must reject or clearly mark unsupported dates. This contract is a draft, not a claim that the current app meets it.
