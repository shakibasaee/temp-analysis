"""Generate a deterministic synthetic daily dataset for a provenance-free demo."""

from __future__ import annotations

import argparse
import csv
import math
from datetime import date, timedelta
from pathlib import Path


def generate(path: Path) -> int:
    """Write the forecasting CSV schema and return its observation count."""
    path.parent.mkdir(parents=True, exist_ok=True)
    start = date(2023, 1, 1)
    end = date(2024, 12, 31)
    cities = (("Sample_North", 8.0), ("Sample_South", 22.0))
    count = 0
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(("Date_Time", "City", "Temperature_C"))
        for city, offset in cities:
            day = start
            while day <= end:
                elapsed = (day - start).days
                annual = 9.0 * math.sin(2 * math.pi * elapsed / 365.25)
                weekly = 1.5 * math.sin(2 * math.pi * elapsed / 7)
                writer.writerow((day.isoformat(), city, round(offset + annual + weekly, 3)))
                count += 1
                day += timedelta(days=1)
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("artifacts/sample_weather.csv"))
    args = parser.parse_args()
    print(f"Wrote {generate(args.out)} synthetic observations to {args.out}")


if __name__ == "__main__":
    main()
