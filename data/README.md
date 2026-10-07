# Dataset inventory and provenance

`new_weather_data.csv` is the input for the supported next-day benchmark. It contains 3,655 records: one daily record for each of five cities from 2023-01-01 through 2024-12-31. The required fields are `Date_Time`, `City`, and `Temperature_C`. There are no missing required values or city/date gaps. Optional precipitation and pressure fields contain 19 and 10 missing values respectively; the current forecast does not use them.

**Provenance is unverified.** The repository does not establish the original provider, station identifiers, collection method, timezone, whether `Temperature_C` is a mean or point reading, licensing, or how new rows should be obtained. The benchmark is useful for testing the pipeline but does not establish live forecasting skill. The bundled series ends in 2024, so its next-day prediction is a historical estimate.

Before adding observations, record the source URL or provider, location/station identifiers, temperature definition and units, timezone and daily aggregation, license, retrieval date, and any cleaning steps. Keep raw source files and retrieval metadata separate from validated model inputs. Re-run data validation and rolling backtests after each update.

Other files (`fullweather.csv`, `kh_weather_data.csv`, `train_processed.csv`, `test_processed.csv`, and `weather_data.csv`) have different schemas or purposes. In particular, `weather_data.csv` is approximately 103 MB and has one million rows; its relationship to the five-city benchmark is undocumented. Do not combine these files until their origin, target alignment, and temporal split have been verified.
