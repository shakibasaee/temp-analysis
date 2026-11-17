"""Compare local-day ERA5 forecasts with quality-screened NOAA GHCNh readings."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from datetime import UTC, date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.audit_ghcn_stations import distance_km
from scripts.audit_open_meteo import CITY_POINTS
from scripts.audit_ssod import STATIONS
from scripts.evaluate_ssod import evaluate

SOURCE_ROOT = (
    "https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/access/by-year"
)
DOCUMENTATION = "https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/doc/ghcnh_DOCUMENTATION.pdf"
MIN_HOURS = 18
MIN_HOURS_PER_BLOCK = 3


def parse_local_station(raw: bytes, station_id: str, year: int) -> tuple[pd.DataFrame, dict]:
    """Use one median temperature per local hour, then summarize complete-enough days."""
    columns = ["STATION", "DATE", "temperature", "temperature_Quality_Code"]
    frame = pd.read_csv(io.BytesIO(raw), sep="|", usecols=columns, low_memory=False)
    if frame.empty or frame["STATION"].isna().any() or not frame["STATION"].eq(station_id).all():
        raise ValueError("Unexpected or missing GHCNh station ID")
    stamps = pd.to_datetime(frame["DATE"], utc=True, errors="coerce")
    if stamps.isna().any() or not stamps.dt.year.eq(year).all():
        raise ValueError("Invalid or out-of-year GHCNh UTC timestamp")
    temperature = pd.to_numeric(frame["temperature"], errors="coerce")
    quality = pd.to_numeric(frame["temperature_Quality_Code"], errors="coerce")
    accepted = quality.eq(1) & temperature.gt(-100) & temperature.lt(70) & np.isfinite(temperature)
    valid = pd.DataFrame(
        {
            "local_time": stamps[accepted].dt.tz_convert("Asia/Tehran"),
            "temperature": temperature[accepted].astype(float),
        }
    )
    valid["local_hour"] = valid["local_time"].dt.floor("h")
    hourly = valid.groupby("local_hour", as_index=False)["temperature"].median()
    hourly["target_date"] = hourly["local_hour"].dt.tz_localize(None).dt.normalize()
    hourly["block"] = hourly["local_hour"].dt.hour // 6
    # Jan 1 is incomplete: the annual UTC file excludes Dec 31 of the prior year.
    lower = pd.Timestamp(date(year, 1, 2))
    upper = pd.Timestamp(date(year, 12, 31))
    hourly = hourly[hourly["target_date"].between(lower, upper)]
    blocks = hourly.groupby(["target_date", "block"]).size().unstack(fill_value=0)
    blocks = blocks.reindex(columns=range(4), fill_value=0)
    hours = hourly.groupby("target_date").size()
    eligible = hours.index[(hours >= MIN_HOURS) & blocks.ge(MIN_HOURS_PER_BLOCK).all(axis=1)]
    daily = (
        hourly[hourly["target_date"].isin(eligible)]
        .groupby("target_date")["temperature"]
        .agg(Mean_C="mean", Min_C="min", Max_C="max")
        .reset_index()
    )
    if (
        daily.empty
        or not (daily["Min_C"] <= daily["Mean_C"]).all()
        or not (daily["Mean_C"] <= daily["Max_C"]).all()
    ):
        raise ValueError("No valid, physically ordered local station days")
    return daily, {
        "raw_reports": len(frame),
        "quality_accepted_reports": int(accepted.sum()),
        "distinct_local_hour_bins": len(hourly),
        "local_days_with_any_accepted_hour": len(hours),
        "eligible_local_days": len(daily),
        "first_eligible_date": daily["target_date"].min().date().isoformat(),
        "last_eligible_date": daily["target_date"].max().date().isoformat(),
        "eligible_hour_bins_median": float(hours.loc[eligible].median()),
    }


def load_stations(year: int, station_dir: Path) -> tuple[pd.DataFrame, list[dict]]:
    city_coords = {city: (lat, lon) for city, _, lat, lon in CITY_POINTS}
    frames = []
    metadata = []
    for city, (station_id, name, lat, lon) in STATIONS.items():
        path = station_dir / f"GHCNh_{station_id}_{year}.psv"
        raw = path.read_bytes()
        frame, coverage = parse_local_station(raw, station_id, year)
        frame.insert(0, "City", city)
        frames.append(frame)
        city_lat, city_lon = city_coords[city]
        metadata.append(
            {
                "city": city,
                "station_id": station_id,
                "station_name": name,
                "station_latitude": lat,
                "station_longitude": lon,
                "distance_km": round(distance_km(city_lat, city_lon, lat, lon), 1),
                "source_url": f"{SOURCE_ROOT}/{year}/psv/GHCNh_{station_id}_{year}.psv",
                "response_sha256": hashlib.sha256(raw).hexdigest(),
                **coverage,
            }
        )
    return pd.concat(frames, ignore_index=True), metadata


def audit(year: int, station_dir: Path) -> dict:
    _observations, stations = load_stations(year, station_dir)
    return {
        "source": "NOAA NCEI GHCNh hourly observations",
        "documentation": DOCUMENTATION,
        "retrieved_utc": datetime.now(UTC).isoformat(),
        "year": year,
        "day_definition": "Asia/Tehran local calendar day, 00:00 to 23:59",
        "first_eligible_date": f"{year}-01-02",
        "last_eligible_date": f"{year}-12-31",
        "denominator_local_days": (date(year + 1, 1, 1) - date(year, 1, 2)).days,
        "temperature_rule": (
            "temperature_Quality_Code == 1; -100 < C < 70; median per local hour; "
            f"at least {MIN_HOURS} distinct local hours and "
            f"{MIN_HOURS_PER_BLOCK} in each 6-hour block"
        ),
        "stations": stations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--station-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--data", type=Path, default=Path("data/era5_five_cities.csv"))
    parser.add_argument(
        "--audit-out", type=Path, default=Path("docs/GHCNH_LOCAL_STATION_AUDIT.json")
    )
    parser.add_argument("--out", type=Path, default=Path("docs/GHCNH_LOCAL_EVALUATION.json"))
    args = parser.parse_args()
    report = audit(2025, args.station_dir)
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    result = evaluate(
        args.data,
        args.audit_out,
        observation_loader=lambda year: load_stations(year, args.station_dir),
        timezone="Asia/Tehran",
        source="NOAA GHCNh quality-screened hourly station summaries",
        day_definition="Asia/Tehran local calendar day, 00:00 to 23:59",
        station_limitations=(
            "Daily targets summarize quality-screened hourly readings. Mean is the mean of hourly "
            "medians; min/max are extrema of hourly medians, not true daily extrema. "
            "Require at least "
            "18 distinct hours and 3 in every 6-hour block. ERA5 grid and station locations differ."
        ),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "station_days": {s["city"]: s["eligible_local_days"] for s in report["stations"]},
                "paired_forecasts": result["paired_forecasts"],
                "paired_unique_city_target_days": result["paired_unique_city_target_days"],
                "station_overall": result["station_overall"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
