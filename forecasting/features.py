"""Features known at the close of the observation day for a next-day forecast."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .data import validate_daily_data

NUMERIC_FEATURES = (
    "temp_today",
    "temp_lag_1",
    "temp_lag_6",
    "temp_lag_7",
    "mean_3",
    "mean_7",
    "mean_30",
    "std_7",
    "day_of_year_sin",
    "day_of_year_cos",
    "day_of_week_sin",
    "day_of_week_cos",
)
FEATURES = (*NUMERIC_FEATURES, "City")


def make_examples(data: pd.DataFrame, min_history_days: int = 30) -> pd.DataFrame:
    """Build one-day-ahead examples; all predictors are observed by issue_date.

    The final row per city has an unknown target and is retained for inference.
    No future weather measurements enter the predictors.
    """
    if min_history_days < 30:
        raise ValueError("At least 30 days are needed for the rolling features")
    daily = validate_daily_data(data)
    group = daily.groupby("City", sort=False)["Temperature_C"]
    result = daily[["City", "Date_Time"]].rename(columns={"Date_Time": "issue_date"}).copy()
    result["target_date"] = result["issue_date"] + pd.Timedelta(days=1)
    result["temp_today"] = daily["Temperature_C"]
    for lag in (1, 6, 7):
        result[f"temp_lag_{lag}"] = group.shift(lag)
    for window in (3, 7, 30):
        result[f"mean_{window}"] = group.transform(
            lambda s, window=window: s.rolling(window).mean()
        )
    result["std_7"] = group.transform(lambda s: s.rolling(7).std())
    day_of_year = result["target_date"].dt.dayofyear
    result["day_of_year_sin"] = np.sin(2 * np.pi * day_of_year / 365.25)
    result["day_of_year_cos"] = np.cos(2 * np.pi * day_of_year / 365.25)
    day_of_week = result["target_date"].dt.dayofweek
    result["day_of_week_sin"] = np.sin(2 * np.pi * day_of_week / 7)
    result["day_of_week_cos"] = np.cos(2 * np.pi * day_of_week / 7)
    result["target"] = group.shift(-1)
    age = daily.groupby("City", sort=False).cumcount() + 1
    result = result.loc[age >= min_history_days].copy()
    if result.empty:
        raise ValueError("No city has enough daily history")
    return result.reset_index(drop=True)
