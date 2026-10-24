"""Fetch the pinned weekly archived forecast sample."""

from datetime import date
from pathlib import Path

from forecasting.archived_runs import fetch_snapshot, save_snapshot

ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    data, metadata = fetch_snapshot(date(2024, 4, 1), date(2025, 12, 29))
    save_snapshot(
        data,
        metadata,
        ROOT / "data" / "archived_ifs_weekly.csv",
        ROOT / "data" / "archived_ifs_weekly.manifest.json",
    )
    print(f"Saved {len(data)} rows; SHA-256 {metadata['csv_sha256']}")
