"""Ingest and validate daily observations without discarding dates at random."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REQUIRED = ("Date_Time", "City", "Temperature_C")


def validate_daily_data(frame: pd.DataFrame) -> pd.DataFrame:
    missing = set(REQUIRED) - set(frame)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("The input dataset is empty")
    data = frame.loc[:, list(REQUIRED)].copy()
    data["Date_Time"] = pd.to_datetime(data["Date_Time"], errors="coerce")
    data["Temperature_C"] = pd.to_numeric(data["Temperature_C"], errors="coerce")
    if (
        data["Date_Time"].isna().any()
        or (data["Date_Time"].dt.normalize() != data["Date_Time"]).any()
    ):
        raise ValueError("Date_Time must contain valid midnight daily dates")
    if data["City"].isna().any() or data["City"].astype(str).str.strip().eq("").any():
        raise ValueError("City must be nonempty")
    if not np.isfinite(data["Temperature_C"].to_numpy(dtype=float)).all():
        raise ValueError("Temperature_C must contain finite numeric values")
    if not data["Temperature_C"].between(-90, 60).all():
        raise ValueError("Temperature_C falls outside plausible Celsius bounds")
    if data.duplicated(["City", "Date_Time"]).any():
        raise ValueError("Duplicate City/Date_Time observations")
    data = data.sort_values(["City", "Date_Time"]).reset_index(drop=True)
    gaps = data.groupby("City", sort=False)["Date_Time"].diff().dropna()
    if not gaps.eq(pd.Timedelta(days=1)).all():
        raise ValueError("Each city must have contiguous daily observations")
    return data


def load_daily_data(path: str | Path) -> pd.DataFrame:
    return validate_daily_data(pd.read_csv(path))
