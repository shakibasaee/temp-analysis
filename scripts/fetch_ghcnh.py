"""Download NOAA GHCNh annual station PSV files into an ignored local directory."""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from urllib.request import urlopen

from scripts.audit_ssod import STATIONS
from scripts.evaluate_ghcnh_local import SOURCE_ROOT


def fetch(year: int, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for city, (station_id, _name, _lat, _lon) in STATIONS.items():
        name = f"GHCNh_{station_id}_{year}.psv"
        path = directory / name
        if path.exists() and path.stat().st_size > 0:
            print(f"{city}: existing {path}")
            continue
        url = f"{SOURCE_ROOT}/{year}/psv/{name}"
        temporary = path.with_suffix(".psv.part")
        for attempt in range(5):
            try:
                with urlopen(url, timeout=90) as response, temporary.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                with temporary.open("rb") as downloaded:
                    if not downloaded.readline().startswith(b"STATION|Station_name|DATE|"):
                        raise ValueError(f"Unexpected GHCNh file header for {city}")
                temporary.replace(path)
                print(f"{city}: downloaded {path}")
                break
            except OSError:
                if attempt == 4:
                    raise
                time.sleep(attempt + 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--dir", type=Path, default=Path("artifacts"))
    args = parser.parse_args()
    fetch(args.year, args.dir)


if __name__ == "__main__":
    main()
