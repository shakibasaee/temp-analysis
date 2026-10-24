"""Archived ECMWF run snapshots with an explicit decision time and lead."""

from __future__ import annotations

import hashlib
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

from .open_meteo import CITY_CENTRES

URL = "https://single-runs-api.open-meteo.com/v1/forecast"
FIELDS = {
    "temperature_2m_mean": ("forecast_temperature_c", "°C"),
    "wind_speed_10m_mean": ("forecast_wind_kmh", "km/h"),
    "pressure_msl_mean": ("forecast_pressure_hpa", "hPa"),
    "precipitation_sum": ("forecast_precipitation_mm", "mm"),
}


def request_url(run_day: date) -> str:
    """A 00 UTC run is treated as available at 12 UTC the next day."""
    query = urlencode(
        {
            "latitude": ",".join(str(v[0]) for v in CITY_CENTRES.values()),
            "longitude": ",".join(str(v[1]) for v in CITY_CENTRES.values()),
            "run": run_day.isoformat() + "T00:00",
            "daily": ",".join(FIELDS),
            "timezone": "UTC",
            "models": "ecmwf_ifs",
            "forecast_days": 3,
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "precipitation_unit": "mm",
        }
    )
    return f"{URL}?{query}"


def parse_run(payload: object, run_day: date) -> tuple[list[dict], list[dict]]:
    if not isinstance(payload, list) or len(payload) != len(CITY_CENTRES):
        raise ValueError(f"Expected five city responses for {run_day}")
    target = run_day + timedelta(days=2)
    issue = datetime.combine(
        run_day + timedelta(days=1), datetime.min.time()
    ) + timedelta(hours=12)
    rows, grids = [], []
    for city, item in zip(CITY_CENTRES, payload, strict=True):
        if item.get("utc_offset_seconds") != 0 or item.get("timezone") not in (
            "GMT",
            "UTC",
        ):
            raise ValueError(f"Non-UTC response for {city} on {run_day}")
        daily = item.get("daily", {})
        if daily.get("time") != [
            (run_day + timedelta(days=n)).isoformat() for n in range(3)
        ]:
            raise ValueError(f"Unexpected forecast dates for {city} on {run_day}")
        row = {
            "run_utc": run_day.isoformat() + "T00:00Z",
            "issue_utc": issue.isoformat() + "Z",
            "target_date_utc": target.isoformat(),
            "City": city,
        }
        for source, (column, unit) in FIELDS.items():
            if item.get("daily_units", {}).get(source) != unit:
                raise ValueError(
                    f"Unexpected {source} unit for {city}: {item.get('daily_units')}"
                )
            values = daily.get(source, [])
            if (
                len(values) != 3
                or values[2] is None
                or not math.isfinite(float(values[2]))
            ):
                raise ValueError(f"Missing {source} target for {city} on {run_day}")
            row[column] = float(values[2])
        if row["forecast_precipitation_mm"] < 0 or row["forecast_wind_kmh"] < 0:
            raise ValueError(f"Negative precipitation or wind for {city} on {run_day}")
        rows.append(row)
        grids.append(
            {
                "city": city,
                "latitude": item.get("latitude"),
                "longitude": item.get("longitude"),
            }
        )
    return rows, grids


def fetch_one(run_day: date) -> tuple[list[dict], dict]:
    url = request_url(run_day)
    for attempt in range(4):
        try:
            with urlopen(url, timeout=50) as response:
                raw = response.read()
            rows, grids = parse_run(json.loads(raw), run_day)
            return rows, {
                "run_utc": run_day.isoformat() + "T00:00Z",
                "url": url,
                "response_sha256": hashlib.sha256(raw).hexdigest(),
                "grid_coordinates": grids,
            }
        except (OSError, ValueError):
            if attempt == 3:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def fetch_snapshot(start: date, end: date) -> tuple[pd.DataFrame, dict]:
    if start < date(2024, 3, 14) or end > date.today() - timedelta(days=5):
        raise ValueError("Run dates outside the archived and safely available range")
    days = pd.date_range(start, end, freq="W-MON").date.tolist()
    if not days:
        raise ValueError("No Monday runs in date range")
    with ThreadPoolExecutor(max_workers=4) as pool:
        fetched = list(pool.map(fetch_one, days))
    rows = [row for pair in fetched for row in pair[0]]
    frame = (
        pd.DataFrame(rows)
        .sort_values(["target_date_utc", "City"])
        .reset_index(drop=True)
    )
    if (
        len(frame) != len(days) * len(CITY_CENTRES)
        or frame.duplicated(["target_date_utc", "City"]).any()
    ):
        raise ValueError("Missing or duplicated run-city pairs")
    grids = fetched[0][1]["grid_coordinates"]
    if any(pair[1]["grid_coordinates"] != grids for pair in fetched):
        raise ValueError("Forecast grid coordinates changed between runs")
    manifest = {
        "source": "Open-Meteo Single Runs API; ECMWF IFS HRES archived runs",
        "source_url": "https://open-meteo.com/en/docs/single-runs-api",
        "model": "ecmwf_ifs",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": "Monday 00 UTC initialization; conservative decision time Tuesday 12 UTC; target Wednesday UTC day (initialization lead 48-71 hours)",
        "publication_delay": "Open-Meteo states global runs typically become available 4-6 hours after initialization; exact historical API delivery times are not archived. The 36-hour allowance is conservative but cannot prove each run was accessible then.",
        "time_convention": "All dates and issue times UTC; daily API fields are full UTC days.",
        "requested_coordinates": {
            city: list(coords) for city, coords in CITY_CENTRES.items()
        },
        "response_grid_coordinates": grids,
        "license": "Open-Meteo attribution required (CC BY 4.0); free API is non-commercial.",
        "requests": [
            {key: value for key, value in pair[1].items() if key != "grid_coordinates"}
            for pair in fetched
        ],
        "rows": len(frame),
    }
    return frame, manifest


def save_snapshot(
    frame: pd.DataFrame, manifest: dict, csv_path: Path, manifest_path: Path
) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(csv_path, index=False, lineterminator="\n", float_format="%.4f")
    manifest["csv_sha256"] = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
