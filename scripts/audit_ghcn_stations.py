"""Audit NOAA GHCN-Daily temperature coverage at proposed Iranian stations."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
from http.client import IncompleteRead
from pathlib import Path
from urllib.request import urlopen

from scripts.audit_open_meteo import CITY_POINTS

BASE_URL = "https://www.ncei.noaa.gov/pub/data/ghcn/daily/all"
ELEMENTS = ("TAVG", "TMIN", "TMAX")
# Candidate station coordinates/IDs from NOAA ghcnd-stations.txt, 2026-11-17.
STATIONS = {
    "Bandar_Abbas": ("IRM00040875", "BANDAR ABBASS INTL", 27.218, 56.378),
    "Mashhad": ("IR000040745", "MASHHAD", 36.267, 59.633),
    "Rasht": ("IRM00040718", "ANZALI", 37.467, 49.467),
    "Sanandaj": ("IRM00040747", "SANANDAJ", 35.247, 47.009),
    "Yazd": ("IRM00040821", "YAZD SHAHID SADOOGHI", 31.905, 54.277),
}


def distance_km(a: float, b: float, c: float, d: float) -> float:
    latitude = math.radians(c - a)
    longitude = math.radians(d - b)
    value = (
        math.sin(latitude / 2) ** 2
        + math.cos(math.radians(a)) * math.cos(math.radians(c)) * math.sin(longitude / 2) ** 2
    )
    return 12742 * math.asin(math.sqrt(value))


def parse_dly(raw: bytes, first_year: int, last_year: int) -> dict:
    """Count nonmissing observations without failed NOAA quality flags."""
    if last_year < first_year:
        raise ValueError("last year must follow first year")
    observations: dict[date, dict[str, float]] = defaultdict(dict)
    source_flags: dict[str, Counter] = defaultdict(Counter)
    quality_rejected: Counter = Counter()
    malformed = 0
    for line in raw.decode("ascii").splitlines():
        if len(line) < 269:
            malformed += 1
            continue
        try:
            year = int(line[11:15])
            month = int(line[15:17])
        except ValueError:
            malformed += 1
            continue
        element = line[17:21]
        if not first_year <= year <= last_year or element not in ELEMENTS:
            continue
        for day in range(1, 32):
            try:
                stamp = date(year, month, day)
            except ValueError:
                continue
            position = 21 + (day - 1) * 8
            try:
                value = int(line[position : position + 5])
            except ValueError:
                malformed += 1
                continue
            if value == -9999:
                continue
            quality = line[position + 6]
            if quality != " ":
                quality_rejected[element] += 1
                continue
            observations[stamp][element] = value / 10
            source_flags[element][line[position + 7]] += 1
    counts = {element: sum(element in row for row in observations.values()) for element in ELEMENTS}
    latest = {
        element: max(
            (stamp.isoformat() for stamp, row in observations.items() if element in row),
            default=None,
        )
        for element in ELEMENTS
    }
    triples = sum(all(element in row for element in ELEMENTS) for row in observations.values())
    ordering_violations = sum(
        not (row["TMIN"] <= row["TAVG"] <= row["TMAX"])
        for row in observations.values()
        if len(row) == 3
    )
    by_year = {
        str(year): {
            **{
                element: sum(
                    element in row for stamp, row in observations.items() if stamp.year == year
                )
                for element in ELEMENTS
            },
            "all_three": sum(
                len(row) == 3 for stamp, row in observations.items() if stamp.year == year
            ),
        }
        for year in range(first_year, last_year + 1)
    }
    return {
        "element_days": counts,
        "latest_date": latest,
        "all_three_days": triples,
        "ordering_violations": ordering_violations,
        "by_year": by_year,
        "source_flags": {key: dict(value) for key, value in source_flags.items()},
        "quality_rejected": dict(quality_rejected),
        "malformed_fields_or_lines": malformed,
    }


def fetch_station(station_id: str) -> bytes:
    url = f"{BASE_URL}/{station_id}.dly"
    for attempt in range(3):
        try:
            with urlopen(url, timeout=30) as response:
                return response.read()
        except (OSError, IncompleteRead):
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    raise AssertionError("unreachable")


def audit(first_year: int, last_year: int) -> dict:
    city_coords = {city: (lat, lon) for city, _, lat, lon in CITY_POINTS}

    def inspect(item: tuple[str, tuple[str, str, float, float]]) -> dict:
        city, (station_id, name, lat, lon) = item
        raw = fetch_station(station_id)
        if not raw.startswith(station_id.encode("ascii")):
            raise ValueError(f"Unexpected station file for {station_id}")
        coverage = parse_dly(raw, first_year, last_year)
        city_lat, city_lon = city_coords[city]
        return {
            "city": city,
            "station_id": station_id,
            "station_name": name,
            "station_latitude": lat,
            "station_longitude": lon,
            "city_latitude": city_lat,
            "city_longitude": city_lon,
            "distance_km": round(distance_km(city_lat, city_lon, lat, lon), 1),
            "url": f"{BASE_URL}/{station_id}.dly",
            "file_sha256": hashlib.sha256(raw).hexdigest(),
            **coverage,
        }

    with ThreadPoolExecutor(max_workers=5) as pool:
        stations = list(pool.map(inspect, STATIONS.items()))
    return {
        "source": "NOAA NCEI GHCN-Daily",
        "station_index": "https://www.ncei.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt",
        "documentation": "https://www.ncei.noaa.gov/pub/data/ghcn/daily/readme.txt",
        "retrieved_utc": datetime.now(UTC).isoformat(),
        "years": [first_year, last_year],
        "daily_denominator": (date(last_year + 1, 1, 1) - date(first_year, 1, 1)).days,
        "quality_rule": "exclude -9999 and nonblank QFLAG; counts only, not archived values",
        "stations": stations,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first-year", type=int, default=2020)
    parser.add_argument("--last-year", type=int, default=2025)
    parser.add_argument("--out", type=Path, default=Path("docs/GHCN_STATION_AUDIT.json"))
    args = parser.parse_args()
    result = audit(args.first_year, args.last_year)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for station in result["stations"]:
        print(
            station["city"],
            station["station_id"],
            station["distance_km"],
            station["element_days"],
            station["all_three_days"],
        )


if __name__ == "__main__":
    main()
