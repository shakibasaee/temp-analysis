"""Audit NOAA SSODv2 observation coverage without saving daily station rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from http.client import IncompleteRead
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from scripts.audit_ghcn_stations import distance_km
from scripts.audit_open_meteo import CITY_POINTS

API = "https://www.ncei.noaa.gov/access/services/data/v1"
TARGETS = ("mean_temperature", "min_temperature", "max_temperature")
STATIONS = {
    "Bandar_Abbas": ("IRI0000OIKB", "BANDAR ABBASS INTL", 27.2182, 56.3779),
    "Mashhad": ("IRU040745-1", "MASHHAD", 36.2700, 59.6300),
    "Rasht": ("IRI0000OIGG", "RASHT", 37.3254, 49.6057),
    "Sanandaj": ("IRI0000OICS", "SANANDAJ", 35.2469, 47.0090),
    "Yazd": ("IRI0000OIYY", "YAZD SHAHID SADOOGHI", 31.9049, 54.2765),
}


def fetch_station(station_id: str, year: int) -> tuple[bytes, str]:
    query = urlencode(
        {
            "dataset": "synoptic-summary-of-the-day-v2",
            "stations": station_id,
            "startDate": f"{year}-01-01",
            "endDate": f"{year}-12-31",
            "format": "json",
        }
    )
    url = f"{API}?{query}"
    for attempt in range(3):
        try:
            with urlopen(url, timeout=40) as response:
                return response.read(), url
        except (OSError, IncompleteRead):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    raise AssertionError("unreachable")


def valid_temperature(value: object) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return -100 < number < 70


def summarize(raw: bytes, station_id: str, year: int) -> dict:
    rows = json.loads(raw)
    if not isinstance(rows, list):
        raise ValueError("SSOD response must be a list")
    accepted: dict[date, set[str]] = {}
    duplicates = 0
    invalid_dates = 0
    ordering_violations = 0
    for row in rows:
        if row.get("STATION") != station_id:
            raise ValueError("Unexpected station ID in SSOD response")
        try:
            stamp = date.fromisoformat(row["DATE"])
        except (KeyError, TypeError, ValueError):
            invalid_dates += 1
            continue
        if stamp.year != year:
            raise ValueError("SSOD response date outside requested year")
        if stamp in accepted:
            duplicates += 1
            continue
        present = {target for target in TARGETS if valid_temperature(row.get(target))}
        accepted[stamp] = present
        if len(present) == 3 and not (
            float(row["min_temperature"])
            <= float(row["mean_temperature"])
            <= float(row["max_temperature"])
        ):
            ordering_violations += 1
    counts = {target: sum(target in present for present in accepted.values()) for target in TARGETS}
    return {
        "rows": len(rows),
        "distinct_dates": len(accepted),
        "invalid_dates": invalid_dates,
        "duplicate_dates": duplicates,
        "element_days": counts,
        "all_three_days": sum(len(present) == 3 for present in accepted.values()),
        "ordering_violations": ordering_violations,
        "latest_date": {
            target: max(
                (stamp.isoformat() for stamp, present in accepted.items() if target in present),
                default=None,
            )
            for target in TARGETS
        },
    }


def audit(year: int) -> dict:
    city_coords = {city: (lat, lon) for city, _, lat, lon in CITY_POINTS}

    def inspect(item: tuple[str, tuple[str, str, float, float]]) -> dict:
        city, (station_id, name, lat, lon) = item
        raw, url = fetch_station(station_id, year)
        centre_lat, centre_lon = city_coords[city]
        return {
            "city": city,
            "station_id": station_id,
            "station_name": name,
            "station_latitude": lat,
            "station_longitude": lon,
            "city_latitude": centre_lat,
            "city_longitude": centre_lon,
            "distance_km": round(distance_km(centre_lat, centre_lon, lat, lon), 1),
            "url": url,
            "response_sha256": hashlib.sha256(raw).hexdigest(),
            **summarize(raw, station_id, year),
        }

    with ThreadPoolExecutor(max_workers=2) as pool:
        stations = list(pool.map(inspect, STATIONS.items()))
    return {
        "source": "NOAA NCEI SSODv2",
        "station_index": "https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/doc/ghcnh-station-list.txt",
        "documentation": "https://www.ncei.noaa.gov/oa/synoptic-summary-of-the-day/v2/doc/ssodv2_DOCUMENTATION.pdf",
        "retrieved_utc": datetime.now(UTC).isoformat(),
        "year": year,
        "day_definition": "00:00–23:59 UTC, not Asia/Tehran local day",
        "denominator_days": (date(year + 1, 1, 1) - date(year, 1, 1)).days,
        "temperature_rule": (
            "finite values strictly between -100 and 70 C; " "exclude missing sentinel -9999.9"
        ),
        "stations": stations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--out", type=Path, default=Path("docs/SSOD_STATION_AUDIT.json"))
    args = parser.parse_args()
    report = audit(args.year)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for station in report["stations"]:
        print(
            station["city"],
            station["station_id"],
            station["distance_km"],
            station["all_three_days"],
        )


if __name__ == "__main__":
    main()
