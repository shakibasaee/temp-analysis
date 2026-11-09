"""Fetch and validate a versioned five-city daily ERA5 research dataset."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path

from scripts.audit_open_meteo import (
    CITY_POINTS,
    ENDPOINT,
    VARIABLES,
    fetch_archive,
    summarize_archive,
)


def build(start: date, end: date, output: Path) -> dict:
    payload = fetch_archive(start, end)
    summary = summarize_archive(payload, start, end)
    if any(
        any(city["missing"].values()) or city["inconsistent_min_mean_max"]
        for city in summary["cities"]
    ):
        raise ValueError("Source contains missing or inconsistent temperatures")

    rows = []
    for (city, _, _, _), item in zip(CITY_POINTS, payload, strict=True):
        daily = item["daily"]
        rows.extend(
            (day, city, mean, minimum, maximum)
            for day, mean, minimum, maximum in zip(
                daily["time"], *(daily[name] for name in VARIABLES), strict=True
            )
        )
    rows.sort(key=lambda row: (row[0], row[1]))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("Date", "City", "Mean_C", "Min_C", "Max_C"))
        writer.writerows(rows)
    metadata = {
        "source": "Open-Meteo Historical Weather API / ECMWF ERA5",
        "source_url": "https://open-meteo.com/en/docs/historical-weather-api",
        "api_endpoint": ENDPOINT,
        "model": "era5",
        "variables": list(VARIABLES),
        "timezone": "Asia/Tehran",
        "unit": "Celsius",
        "license": "CC BY 4.0; attribution required",
        "license_url": "https://open-meteo.com/en/terms",
        "retrieved_utc": datetime.now(UTC).isoformat(),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "rows": len(rows),
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "city_coverage": summary["cities"],
        "limitations": "ERA5 reanalysis estimates; not independent station observations",
    }
    output.with_suffix(".metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2020, 1, 1))
    parser.add_argument("--end", type=date.fromisoformat, default=date(2025, 12, 31))
    parser.add_argument("--out", type=Path, default=Path("data/era5_five_cities.csv"))
    args = parser.parse_args()
    print(json.dumps(build(args.start, args.end, args.out), indent=2))


if __name__ == "__main__":
    main()
