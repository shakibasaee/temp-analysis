"""Evaluate the existing calendar regression on one city's next-day dates."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.models.linear_regression import LinearRegressionModel


def prepare_city(path: Path, city: str) -> tuple[pd.DataFrame, dict]:
    source = pd.read_csv(path)
    required = ("Date_Time", "City", "Temperature_C")
    if not set(required).issubset(source.columns):
        raise ValueError(f"Missing columns: {sorted(set(required) - set(source.columns))}")
    selected = source.loc[source["City"] == city, list(required)].copy()
    if selected.empty:
        raise ValueError(f"City is absent: {city}")
    selected["Date_Time"] = pd.to_datetime(selected["Date_Time"], errors="coerce")
    selected["Temperature_C"] = pd.to_numeric(selected["Temperature_C"], errors="coerce")
    invalid_dates = int(selected["Date_Time"].isna().sum())
    invalid_temps = int((~np.isfinite(selected["Temperature_C"])).sum())
    non_midnight = int(
        (
            selected["Date_Time"].notna()
            & selected["Date_Time"].ne(selected["Date_Time"].dt.normalize())
        ).sum()
    )
    selected = selected.sort_values("Date_Time").reset_index(drop=True)
    duplicate_dates = int(selected["Date_Time"].duplicated().sum())
    valid_dates = selected["Date_Time"].dropna()
    expected = (
        pd.date_range(valid_dates.min(), valid_dates.max())
        if len(valid_dates)
        else pd.DatetimeIndex([])
    )
    missing_dates = expected.difference(valid_dates)
    audit = {
        "city": city,
        "rows": len(selected),
        "first_date": str(valid_dates.min().date()) if len(valid_dates) else None,
        "last_date": str(valid_dates.max().date()) if len(valid_dates) else None,
        "invalid_dates": invalid_dates,
        "non_midnight_dates": non_midnight,
        "invalid_temperatures": invalid_temps,
        "duplicate_dates": duplicate_dates,
        "missing_dates": [str(day.date()) for day in missing_dates],
        "unit": "Celsius, as named by Temperature_C; daily meaning unverified",
    }
    if invalid_dates or non_midnight or invalid_temps or duplicate_dates or len(missing_dates):
        raise ValueError(f"City series is not usable: {json.dumps(audit)}")
    if len(selected) < 30:
        raise ValueError("At least 30 consecutive days are required")
    return selected, audit


def evaluate(path: Path, city: str) -> tuple[pd.DataFrame, dict]:
    daily, audit = prepare_city(path, city)
    train_count = math.floor(len(daily) * 0.8)
    train = daily.iloc[:train_count].copy()
    test = daily.iloc[train_count:].copy()
    model = LinearRegressionModel().fit(train)
    predicted = model.predict(test[["Date_Time", "City"]])
    baseline = daily["Temperature_C"].shift(1).iloc[train_count:].to_numpy()
    actual = test["Temperature_C"].to_numpy()
    if not np.isfinite(predicted).all() or not np.isfinite(baseline).all():
        raise ValueError("Forecast or baseline contains non-finite values")
    output = pd.DataFrame(
        {
            "date": test["Date_Time"].dt.strftime("%Y-%m-%d").to_numpy(),
            "actual": actual,
            "predicted": predicted,
        }
    )
    summary = {
        "dataset_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_csv": path.as_posix(),
        "data_audit": audit,
        "train_rows": len(train),
        "train_dates": [str(train["Date_Time"].min().date()), str(train["Date_Time"].max().date())],
        "test_rows": len(test),
        "test_dates": [str(test["Date_Time"].min().date()), str(test["Date_Time"].max().date())],
        "split": "first floor(80% of dates) for fitting, final 20% for evaluation",
        "model": (
            "scripts.models.linear_regression.LinearRegressionModel; "
            "calendar and city features only; fixed after training"
        ),
        "forecast_issue": "day before each test target; target calendar date is known",
        "signed_error": "actual - predicted; positive means underprediction",
        "regression_mae_c": float(np.mean(np.abs(actual - predicted))),
        "regression_mean_signed_error_c": float(np.mean(actual - predicted)),
        "persistence_mae_c": float(np.mean(np.abs(actual - baseline))),
        "persistence_mean_signed_error_c": float(np.mean(actual - baseline)),
        "persistence_rule": "previous day's actual Temperature_C",
    }
    return output, summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/new_weather_data.csv"))
    parser.add_argument("--city", default="Mashhad")
    parser.add_argument("--out", type=Path, default=Path("forecast_eval.csv"))
    args = parser.parse_args()
    output, summary = evaluate(args.data, args.city)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.out, index=False, float_format="%.12g", lineterminator="\n")
    summary["forecast_eval_sha256"] = hashlib.sha256(args.out.read_bytes()).hexdigest()
    args.out.with_suffix(".metadata.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
