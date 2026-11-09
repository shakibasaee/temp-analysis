"""Check historical ERA5 coverage for the five proposed city grid points.

This read-only probe does not replace the repository's existing dataset or
measure forecast accuracy. Coordinates are provisional city-centre matches.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from datetime import date, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen

CITY_POINTS = (
    ("Bandar_Abbas", 141681, 27.1865, 56.2808),
    ("Mashhad", 124665, 36.29807, 59.60567),
    ("Rasht", 118743, 37.27611, 49.58862),
    ("Sanandaj", 117574, 35.31495, 46.99883),
    ("Yazd", 111822, 31.89722, 54.3675),
)
VARIABLES = (
    "temperature_2m_mean",
    "temperature_2m_min",
    "temperature_2m_max",
)
ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"


def fetch_archive(start: date, end: date) -> list[dict]:
    if end < start:
        raise ValueError("end date must be on or after start date")
    params = {
        "latitude": ",".join(str(point[2]) for point in CITY_POINTS),
        "longitude": ",".join(str(point[3]) for point in CITY_POINTS),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": ",".join(VARIABLES),
        "timezone": "Asia/Tehran",
        "models": "era5",
        "temperature_unit": "celsius",
    }
    for attempt in range(3):
        try:
            with urlopen(f"{ENDPOINT}?{urlencode(params)}", timeout=60) as response:
                payload = json.load(response)
            break
        except OSError:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    return payload


def summarize_archive(payload: list[dict], start: date, end: date) -> dict:
    if not isinstance(payload, list) or len(payload) != len(CITY_POINTS):
        raise ValueError("expected one response per requested city")

    expected_dates = [
        (start + timedelta(days=offset)).isoformat() for offset in range((end - start).days + 1)
    ]
    results = []
    for (city, geocoding_id, lat, lon), item in zip(CITY_POINTS, payload, strict=True):
        daily = item["daily"]
        if item.get("timezone") != "Asia/Tehran" or daily.get("time") != expected_dates:
            raise ValueError(f"{city}: unexpected timezone or date coverage")
        missing = {}
        for variable in VARIABLES:
            if item["daily_units"].get(variable) != "°C":
                raise ValueError(f"{city}: unexpected unit for {variable}")
            values = daily[variable]
            if len(values) != len(expected_dates):
                raise ValueError(f"{city}: unexpected length for {variable}")
            if any(
                value is not None
                and (not isinstance(value, int | float) or not math.isfinite(value))
                for value in values
            ):
                raise ValueError(f"{city}: invalid value for {variable}")
            missing[variable] = sum(value is None for value in values)
        inconsistent = sum(
            not (minimum <= mean <= maximum)
            for mean, minimum, maximum in zip(*(daily[name] for name in VARIABLES), strict=True)
            if mean is not None and minimum is not None and maximum is not None
        )
        results.append(
            {
                "city": city,
                "geocoding_id": geocoding_id,
                "requested_latitude": lat,
                "requested_longitude": lon,
                "grid_latitude": item.get("latitude"),
                "grid_longitude": item.get("longitude"),
                "days": len(expected_dates),
                "missing": missing,
                "inconsistent_min_mean_max": inconsistent,
            }
        )
    return {
        "source": "Open-Meteo Historical Weather API / ERA5",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timezone": "Asia/Tehran",
        "cities": results,
    }


def audit(start: date, end: date) -> dict:
    return summarize_archive(fetch_archive(start, end), start, end)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2023, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2024, 12, 31))
    args = parser.parse_args()
    print(json.dumps(audit(args.start, args.end), indent=2))


if __name__ == "__main__":
    main()
