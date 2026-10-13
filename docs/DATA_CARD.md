# Data card: `data/new_weather_data.csv`

This card records what can be verified from the repository, and what is still unknown. It does not infer provenance from who committed the file.

| Field | Current evidence |
| --- | --- |
| SHA-256 | `361491c9f30c3a60ee0d86e5d54bcbfab9492e9204f7959ad80505fae2ed1c71` |
| Coverage | Five city labels, 2023-01-01 through 2024-12-31, 731 contiguous dates each |
| Columns | `Date_Time`, `City`, `Temperature_C`, `Precipitation_mm`, `Wind_Speed_kmh`, `Pressure_hPa` |
| Missing values | 19 precipitation, 10 pressure; none in temperature or wind |
| Source and license | Unknown |
| Station or grid coordinates | Unknown |
| Daily aggregation and time zone | Unknown; timestamps parse as midnight but do not define the observation period |
| Measurement method and quality flags | Unknown |
| Update schedule | Unknown; latest row is 2024-12-31 |

Until the unknown fields are resolved, benchmark scores are **internal diagnostics only**. The file must not be described as a verified observational dataset or used to claim operational forecast accuracy.

To promote this dataset, record the original URL or collection process, version and license, city-to-location mapping, variable definitions and units, time zone and daily cutoff, publication delay, quality flags, and how missing or revised values are handled. Then check a sample of rows against the source and evaluate on later data.
