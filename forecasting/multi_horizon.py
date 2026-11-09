"""Leakage-aware, fixed-origin evaluation of daily ERA5 temperature estimates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TARGETS = ("Mean_C", "Min_C", "Max_C")
NUMERIC = (
    "horizon",
    "day_sin",
    "day_cos",
    "last_mean",
    "last_min",
    "last_max",
    "week_mean",
    "week_min",
    "week_max",
    "month_mean",
    "month_min",
    "month_max",
)
FEATURES = (*NUMERIC, "City")
LAG_DAYS = 7  # Conservative fixed ERA5 publication delay for this experiment.
MAX_HORIZON = 30


def load_dataset(path: Path) -> pd.DataFrame:
    data = pd.read_csv(path, parse_dates=["Date"])
    if list(data.columns) != ["Date", "City", *TARGETS]:
        raise ValueError("Unexpected daily temperature schema")
    if data.isna().any().any() or not np.isfinite(data[list(TARGETS)].to_numpy()).all():
        raise ValueError("Missing or non-finite temperatures")
    if (data["Min_C"] > data["Mean_C"]).any() or (data["Mean_C"] > data["Max_C"]).any():
        raise ValueError("Daily minimum, mean and maximum are inconsistent")
    if data.duplicated(["City", "Date"]).any():
        raise ValueError("Duplicate city/date")
    for _, city in data.groupby("City"):
        dates = city["Date"].sort_values()
        if not dates.diff().dropna().eq(pd.Timedelta(days=1)).all():
            raise ValueError("City history has a date gap")
    return data.sort_values(["City", "Date"]).reset_index(drop=True)


def make_examples(data: pd.DataFrame, lag_days: int = LAG_DAYS) -> pd.DataFrame:
    if lag_days < 1:
        raise ValueError("Publication lag must be positive")
    parts = []
    for city, frame in data.groupby("City", sort=True):
        frame = frame.reset_index(drop=True)
        values = frame[list(TARGETS)].to_numpy()
        dates = frame["Date"].to_numpy()
        week_rolling = frame[list(TARGETS)].rolling(7).mean().to_numpy()
        month_rolling = frame[list(TARGETS)].rolling(30).mean().to_numpy()
        for horizon in range(1, MAX_HORIZON + 1):
            issue_idx = np.arange(lag_days + 29, len(frame) - horizon)
            if not len(issue_idx):
                continue
            available = issue_idx - lag_days
            target_idx = issue_idx + horizon
            target_dates = pd.DatetimeIndex(dates[target_idx])
            day_angle = 2 * np.pi * target_dates.dayofyear.to_numpy() / 365.25
            last = values[available]
            week = week_rolling[available]
            month = month_rolling[available]
            # Last available observation with the requested target weekday.
            weekday_offset = (-(lag_days + horizon)) % 7
            seasonal = values[available - weekday_offset]
            part = pd.DataFrame(
                {
                    "City": city,
                    "issue_date": dates[issue_idx],
                    "available_through": dates[available],
                    "target_date": dates[target_idx],
                    "horizon": horizon,
                    "day_sin": np.sin(day_angle),
                    "day_cos": np.cos(day_angle),
                }
            )
            for j, label in enumerate(("mean", "min", "max")):
                part[f"last_{label}"] = last[:, j]
                part[f"week_{label}"] = week[:, j]
                part[f"month_{label}"] = month[:, j]
                part[TARGETS[j]] = values[target_idx, j]
                part[f"seasonal_{label}"] = seasonal[:, j]
            parts.append(part)
    if not parts:
        raise ValueError("Insufficient daily history")
    return pd.concat(parts, ignore_index=True)


def split_examples(examples: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    target = examples["target_date"]
    issue = examples["issue_date"]
    train = examples[target < "2024-01-01"]
    validation = examples[
        (target >= "2024-01-01") & (target < "2025-01-01") & (issue >= "2024-01-08")
    ]
    test = examples[(target >= "2025-01-01") & (target < "2026-01-01") & (issue >= "2025-01-08")]
    if min(len(train), len(validation), len(test)) == 0:
        raise ValueError("Train, validation or test is empty")
    if train["target_date"].max() > validation["available_through"].min():
        raise ValueError("Training labels unavailable at validation issue time")
    if validation["target_date"].max() > test["available_through"].min():
        raise ValueError("Validation labels unavailable at test issue time")
    return train, validation, test


def fit_ridge(train: pd.DataFrame) -> Pipeline:
    preprocessing = ColumnTransformer(
        [
            ("numeric", StandardScaler(), list(NUMERIC)),
            ("city", OneHotEncoder(handle_unknown="ignore"), ["City"]),
        ],
        sparse_threshold=0,
    )
    model = Pipeline([("preprocess", preprocessing), ("regression", Ridge(alpha=100.0))])
    model.fit(train[list(FEATURES)], train[list(TARGETS)])
    return model


def predict_all(frame: pd.DataFrame, model: Pipeline) -> dict[str, np.ndarray]:
    last = frame[["last_mean", "last_min", "last_max"]].to_numpy()
    seasonal = frame[["seasonal_mean", "seasonal_min", "seasonal_max"]].to_numpy()
    ridge = model.predict(frame[list(FEATURES)])
    return {"persistence": last, "seasonal_weekday": seasonal, "ridge": ridge}


def score(frame: pd.DataFrame, predictions: dict[str, np.ndarray]) -> tuple[list[dict], list[dict]]:
    actual = frame[list(TARGETS)].to_numpy()
    groups = frame.groupby(["City", "horizon"], sort=True).indices
    overall = []
    detail = []
    for name, values in predictions.items():
        for j, target in enumerate(TARGETS):
            error = np.abs(values[:, j] - actual[:, j])
            overall.append(
                {
                    "model": name,
                    "target": target,
                    "n": len(error),
                    "mae_c": round(float(error.mean()), 4),
                    "within_2c_pct": round(float(100 * (error <= 2).mean()), 2),
                }
            )
            for (city, horizon), idx in groups.items():
                item = error[idx]
                detail.append(
                    {
                        "model": name,
                        "target": target,
                        "city": city,
                        "horizon": int(horizon),
                        "n": len(item),
                        "mae_c": round(float(item.mean()), 4),
                        "within_2c_pct": round(float(100 * (item <= 2).mean()), 2),
                    }
                )
    return overall, detail


def evaluate(path: Path) -> dict:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    metadata_path = path.with_suffix(".metadata.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata["sha256"] != digest or metadata["model"] != "era5":
        raise ValueError("Dataset does not match its ERA5 provenance metadata")
    data = load_dataset(path)
    if metadata["rows"] != len(data) or sorted(data["City"].unique()) != sorted(
        city["city"] for city in metadata["city_coverage"]
    ):
        raise ValueError("Dataset coverage does not match its metadata")
    examples = make_examples(data)
    train, validation, test = split_examples(examples)
    initial_model = fit_ridge(train)
    validation_overall, _ = score(validation, predict_all(validation, initial_model))
    final_model = fit_ridge(pd.concat([train, validation], ignore_index=True))
    test_predictions = predict_all(test, final_model)
    test_overall, test_detail = score(test, test_predictions)
    ridge = test_predictions["ridge"]
    return {
        "data_sha256": digest,
        "retrieved_utc": metadata["retrieved_utc"],
        "source": "Open-Meteo ERA5 reanalysis; agreement with reanalysis, not station skill",
        "data_dates": [str(data["Date"].min().date()), str(data["Date"].max().date())],
        "cities": sorted(data["City"].unique().tolist()),
        "data_rows": len(data),
        "publication_lag_days": LAG_DAYS,
        "horizons": [1, MAX_HORIZON],
        "train": {
            "n": len(train),
            "target_dates": [
                str(train["target_date"].min().date()),
                str(train["target_date"].max().date()),
            ],
        },
        "validation": {
            "n": len(validation),
            "issue_dates": [
                str(validation["issue_date"].min().date()),
                str(validation["issue_date"].max().date()),
            ],
            "target_dates": [
                str(validation["target_date"].min().date()),
                str(validation["target_date"].max().date()),
            ],
            "overall": validation_overall,
        },
        "test": {
            "n": len(test),
            "issue_dates": [
                str(test["issue_date"].min().date()),
                str(test["issue_date"].max().date()),
            ],
            "target_dates": [
                str(test["target_date"].min().date()),
                str(test["target_date"].max().date()),
            ],
            "ridge_ordering_violations": int(
                ((ridge[:, 1] > ridge[:, 0]) | (ridge[:, 0] > ridge[:, 2])).sum()
            ),
            "overall": test_overall,
            "by_city_horizon": test_detail,
        },
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/era5_five_cities.csv"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/era5_horizon_evaluation.json"))
    args = parser.parse_args()
    result = evaluate(args.data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "data_rows": result["data_rows"],
                "train": result["train"]["n"],
                "validation": result["validation"]["n"],
                "test": result["test"]["n"],
                "validation_overall": result["validation"]["overall"],
                "test_overall": result["test"]["overall"],
                "report": str(args.out),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
