"""Fetch a reproducible UTC daily ERA5 reanalysis snapshot from Open-Meteo."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

from .weather import validate_weather_data

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY = ("temperature_2m", "wind_speed_10m", "pressure_msl")
UNITS = {
    "temperature_2m": "°C",
    "wind_speed_10m": "km/h",
    "pressure_msl": "hPa",
}
# Fixed city centres from Open-Meteo's geocoding API, resolved on 2026-10-13.
CITY_CENTRES = {
    "Sanandaj": (35.31495, 46.99883),
    "Yazd": (31.89722, 54.3675),
    "Bandar_Abbas": (27.1865, 56.2808),
    "Rasht": (37.27611, 49.58862),
    "Mashhad": (36.29807, 59.60567),
}


def archive_url(city: str, start: date, end: date) -> str:
    """Build one explicitly versioned model, unit, timezone, and location request."""
    if city not in CITY_CENTRES:
        raise ValueError(f"Unknown city: {city}")
    if start > end or start.year != end.year:
        raise ValueError("Fetch one chronological calendar-year chunk at a time")
    latitude, longitude = CITY_CENTRES[city]
    query = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "hourly": ",".join(HOURLY),
            "daily": "precipitation_sum",
            "timezone": "UTC",
            "models": "era5",
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
        }
    )
    return f"{ARCHIVE_URL}?{query}"


def daily_from_response(
    payload: dict, city: str, start: date, end: date
) -> pd.DataFrame:
    """Aggregate complete UTC days, rejecting silent gaps or variable changes."""
    if payload.get("error"):
        raise ValueError(f"Open-Meteo error: {payload.get('reason')}")
    if (
        payload.get("timezone") not in ("GMT", "UTC")
        or payload.get("utc_offset_seconds") != 0
    ):
        raise ValueError("Open-Meteo response is not UTC")
    actual_units = payload.get("hourly_units", {})
    if any(actual_units.get(key) != unit for key, unit in UNITS.items()):
        raise ValueError(f"Unexpected Open-Meteo units: {actual_units}")
    if payload.get("daily_units", {}).get("precipitation_sum") != "mm":
        raise ValueError("Unexpected Open-Meteo precipitation unit")
    hourly = payload.get("hourly", {})
    timestamps = pd.to_datetime(hourly.get("time", []), errors="coerce")
    expected = pd.date_range(
        start, end + pd.Timedelta(days=1), freq="h", inclusive="left"
    )
    if len(timestamps) != len(expected) or not timestamps.equals(expected):
        raise ValueError(f"Missing, duplicated, or unexpected ERA5 hours for {city}")
    frame = pd.DataFrame({"time": timestamps})
    for variable in HOURLY:
        values = pd.to_numeric(pd.Series(hourly.get(variable, [])), errors="coerce")
        if len(values) != len(expected) or values.isna().any():
            raise ValueError(f"Incomplete {variable} in ERA5 response for {city}")
        frame[variable] = values.to_numpy()
    daily = frame.groupby(frame["time"].dt.normalize()).agg(
        Temperature_C=("temperature_2m", "mean"),
        Wind_Speed_kmh=("wind_speed_10m", "mean"),
        Pressure_hPa=("pressure_msl", "mean"),
    )
    daily = daily.reset_index(names="Date_Time")
    daily_response = payload.get("daily", {})
    daily_dates = pd.to_datetime(daily_response.get("time", []), errors="coerce")
    expected_days = pd.date_range(start, end, freq="D")
    precipitation = pd.to_numeric(
        pd.Series(daily_response.get("precipitation_sum", [])), errors="coerce"
    )
    if (
        len(daily_dates) != len(expected_days)
        or not daily_dates.equals(expected_days)
        or len(precipitation) != len(expected_days)
        or precipitation.isna().any()
        or (precipitation < 0).any()
    ):
        raise ValueError(f"Incomplete daily precipitation for {city}")
    daily["Precipitation_mm"] = precipitation.to_numpy()
    daily = daily[
        [
            "Date_Time",
            "Temperature_C",
            "Precipitation_mm",
            "Wind_Speed_kmh",
            "Pressure_hPa",
        ]
    ]
    daily.insert(1, "City", city)
    return daily


def fetch_era5(start: date, end: date) -> tuple[pd.DataFrame, dict]:
    """Fetch all five cities in yearly chunks with a recorded request manifest."""
    if start > end:
        raise ValueError("start must be on or before end")
    # ERA5 is normally published with a multi-day delay; no recent-day promise.
    if end > date.today() - pd.Timedelta(days=7):
        raise ValueError("End at least seven days before today for ERA5 availability")
    chunks = []
    requests = []
    for city in CITY_CENTRES:
        cursor = start
        while cursor <= end:
            chunk_end = min(end, date(cursor.year, 12, 31))
            url = archive_url(city, cursor, chunk_end)
            for attempt in range(3):
                try:
                    with urlopen(url, timeout=60) as response:
                        payload = json.load(response)
                    break
                except OSError:
                    if attempt == 2:
                        raise
                    time.sleep(2**attempt)
            chunks.append(daily_from_response(payload, city, cursor, chunk_end))
            requests.append(
                {
                    "city": city,
                    "url": url,
                    "requested_coordinates": list(CITY_CENTRES[city]),
                    "response_grid_coordinates": [
                        payload.get("latitude"),
                        payload.get("longitude"),
                    ],
                    "first_date": cursor.isoformat(),
                    "last_date": chunk_end.isoformat(),
                }
            )
            cursor = chunk_end + pd.Timedelta(days=1)
    data = validate_weather_data(pd.concat(chunks, ignore_index=True))
    manifest = {
        "source": "Open-Meteo Historical Weather API, ECMWF ERA5 reanalysis",
        "source_url": "https://open-meteo.com/en/docs/historical-weather-api",
        "model": "era5",
        "nature": "Gridded reanalysis, not station observations or archived forecasts",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "date_definition": "UTC daily total for precipitation; 00:00–23:00 UTC hourly instants for other variables",
        "aggregation": {
            "Temperature_C": "mean hourly 2 m air temperature",
            "Precipitation_mm": "API daily precipitation_sum, including rain and snow",
            "Wind_Speed_kmh": "mean hourly 10 m wind speed",
            "Pressure_hPa": "mean hourly sea-level pressure",
        },
        "license": "Open-Meteo attribution required; free API is non-commercial",
        "requests": requests,
        "rows": len(data),
    }
    return data, manifest


def save_snapshot(
    data: pd.DataFrame, manifest: dict, output: Path, metadata: Path
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(
        output,
        index=False,
        date_format="%Y-%m-%d",
        float_format="%.4f",
        lineterminator="\n",
    )
    manifest["csv_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    metadata.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
