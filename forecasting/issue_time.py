"""Rolling evaluation of archived forecasts against a delayed ERA5 reference."""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, mean_absolute_error

CONTINUOUS = {
    "temperature_c": ("forecast_temperature_c", "Temperature_C", "°C"),
    "wind_speed_kmh": ("forecast_wind_kmh", "Wind_Speed_kmh", "km/h"),
    "pressure_hpa": ("forecast_pressure_hpa", "Pressure_hPa", "hPa"),
}


def load_pairs(forecast_csv: Path, reference_csv: Path) -> pd.DataFrame:
    forecasts = pd.read_csv(forecast_csv)
    reference = pd.read_csv(reference_csv).rename(
        columns={"Date_Time": "target_date_utc"}
    )
    required = {
        "run_utc",
        "issue_utc",
        "target_date_utc",
        "City",
        "forecast_precipitation_mm",
    }
    required.update(source for source, _, _ in CONTINUOUS.values())
    if required - set(forecasts):
        raise ValueError(
            f"Missing forecast columns: {sorted(required - set(forecasts))}"
        )
    if (
        forecasts.duplicated(["target_date_utc", "City"]).any()
        or reference.duplicated(["target_date_utc", "City"]).any()
    ):
        raise ValueError("Duplicate city-day keys")
    for key in ("run_utc", "issue_utc"):
        forecasts[key] = pd.to_datetime(forecasts[key], utc=True, errors="raise")
    forecasts["target_date_utc"] = pd.to_datetime(
        forecasts["target_date_utc"], utc=True, errors="raise"
    )
    reference["target_date_utc"] = pd.to_datetime(
        reference["target_date_utc"], utc=True, errors="raise"
    )
    if not (
        (forecasts["issue_utc"] - forecasts["run_utc"]) == timedelta(hours=36)
    ).all():
        raise ValueError("Run to decision-time delay must be 36 hours")
    if not (
        (forecasts["target_date_utc"] - forecasts["run_utc"]) == timedelta(hours=48)
    ).all():
        raise ValueError("Target-day start must be run plus 48 hours")
    joined = forecasts.merge(
        reference,
        on=["target_date_utc", "City"],
        how="left",
        validate="one_to_one",
        indicator=True,
    )
    if (joined["_merge"] != "both").any():
        raise ValueError("Missing ERA5 reference for archived run")
    joined = joined.drop(columns="_merge")
    numeric = ["forecast_precipitation_mm", "Precipitation_mm"]
    numeric += [name for name, _, _ in CONTINUOUS.values()]
    numeric += [name for _, name, _ in CONTINUOUS.values()]
    if not np.isfinite(joined[numeric].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite forecast or reference value")
    if (joined[["forecast_precipitation_mm", "Precipitation_mm"]] < 0).any().any():
        raise ValueError("Negative precipitation")
    return joined.sort_values(["target_date_utc", "City"]).reset_index(drop=True)


def training_before_issue(frame: pd.DataFrame, issue_utc: pd.Timestamp) -> pd.DataFrame:
    """ERA5 labels are assumed published seven days after the target UTC day."""
    available = frame["target_date_utc"] + pd.Timedelta(days=7)
    selected = frame.loc[available <= issue_utc].copy()
    if (
        not selected.empty
        and not (selected["target_date_utc"] + pd.Timedelta(days=7) <= issue_utc).all()
    ):
        raise AssertionError("Future reference label entered training")
    return selected


def probability_features(frame: pd.DataFrame) -> pd.DataFrame:
    day = frame["target_date_utc"].dt.dayofyear.to_numpy()
    city = pd.get_dummies(frame["City"], prefix="city", dtype=float)
    features = pd.DataFrame(
        {
            "log_forecast_mm": np.log1p(frame["forecast_precipitation_mm"].to_numpy()),
            "season_sin": np.sin(2 * np.pi * day / 365.25),
            "season_cos": np.cos(2 * np.pi * day / 365.25),
        },
        index=frame.index,
    )
    return pd.concat([features, city], axis=1)


def _scores(rows: pd.DataFrame, key: str, metric: str) -> dict:
    truth = rows["truth"].to_numpy()
    result = {"n": len(rows)}
    for name in ("raw_ifs", "candidate", "climatology"):
        if name == "climatology" and metric == "mae":
            continue
        values = rows[name].to_numpy()
        result[name] = float(
            mean_absolute_error(truth, values)
            if metric == "mae"
            else brier_score_loss(truth, values)
        )
    return result


def evaluate(frame: pd.DataFrame) -> dict:
    if frame.empty:
        raise ValueError("No paired forecasts")
    all_predictions = []
    fold_info = []
    for quarter in range(1, 5):
        start = pd.Timestamp(2025, 3 * (quarter - 1) + 1, 1, tz="UTC")
        end = start + pd.DateOffset(months=3)
        test = frame.loc[
            (frame["target_date_utc"] >= start) & (frame["target_date_utc"] < end)
        ].copy()
        if test.empty:
            raise ValueError(f"No cases in 2025 Q{quarter}")
        first_issue = test["issue_utc"].min()
        train = training_before_issue(frame, first_issue)
        if (
            len(train) < 100
            or train["target_date_utc"].max() >= test["target_date_utc"].min()
        ):
            raise ValueError(f"Insufficient prior training cases for Q{quarter}")
        fold_info.append(
            {
                "fold": f"2025-Q{quarter}",
                "train_n": len(train),
                "test_n": len(test),
                "train_last_target": train["target_date_utc"].max().date().isoformat(),
                "first_issue_utc": first_issue.isoformat(),
                "test_first_target": test["target_date_utc"].min().date().isoformat(),
                "test_last_target": test["target_date_utc"].max().date().isoformat(),
            }
        )
        for variable, (forecast_col, truth_col, _) in CONTINUOUS.items():
            residual = train[truth_col] - train[forecast_col]
            city_bias = residual.groupby(train["City"]).mean().to_dict()
            if not set(test["City"]).issubset(city_bias):
                raise ValueError("Unseen city in test fold")
            for row in test.itertuples():
                raw = float(getattr(row, forecast_col))
                all_predictions.append(
                    {
                        "fold": f"2025-Q{quarter}",
                        "target_date_utc": row.target_date_utc.date().isoformat(),
                        "City": row.City,
                        "variable": variable,
                        "truth": float(getattr(row, truth_col)),
                        "raw_ifs": raw,
                        "candidate": raw + city_bias[row.City],
                    }
                )
        train_features = probability_features(train)
        test_features = probability_features(test).reindex(
            columns=train_features.columns, fill_value=0
        )
        for threshold, label in (
            (0.0, "precipitation_gt_0mm"),
            (1.0, "precipitation_ge_1mm"),
        ):
            wet_train = (
                (train["Precipitation_mm"] > threshold).astype(int)
                if threshold == 0
                else (train["Precipitation_mm"] >= threshold).astype(int)
            )
            if wet_train.nunique() != 2:
                raise ValueError(f"Only one precipitation class for {label}")
            model = LogisticRegression(max_iter=1000, C=1.0).fit(
                train_features, wet_train
            )
            candidate = model.predict_proba(test_features)[:, 1]
            city_rate = wet_train.groupby(train["City"]).mean().to_dict()
            for row, probability in zip(test.itertuples(), candidate, strict=True):
                truth = (
                    float(row.Precipitation_mm > 0)
                    if threshold == 0
                    else float(row.Precipitation_mm >= threshold)
                )
                raw = (
                    float(row.forecast_precipitation_mm > 0)
                    if threshold == 0
                    else float(row.forecast_precipitation_mm >= threshold)
                )
                all_predictions.append(
                    {
                        "fold": f"2025-Q{quarter}",
                        "target_date_utc": row.target_date_utc.date().isoformat(),
                        "City": row.City,
                        "variable": label,
                        "truth": truth,
                        "raw_ifs": raw,
                        "candidate": float(probability),
                        "climatology": city_rate[row.City],
                    }
                )
    predictions = pd.DataFrame(all_predictions)
    results = {}
    for variable, rows in predictions.groupby("variable", sort=True):
        metric = "brier" if variable.startswith("precipitation") else "mae"
        scores = _scores(rows, variable, metric)
        scores["metric"] = metric
        scores["by_city"] = {
            city: _scores(subset, variable, metric)
            for city, subset in rows.groupby("City", sort=True)
        }
        scores["by_fold"] = {
            fold: _scores(subset, variable, metric)
            for fold, subset in rows.groupby("fold", sort=True)
        }
        if metric == "brier":
            scores["event_rate"] = float(rows["truth"].mean())
            scores["calibration"] = []
            for lower in np.arange(0, 1, 0.2):
                upper = round(float(lower + 0.2), 1)
                subset = rows.loc[
                    (rows["candidate"] >= lower)
                    & (
                        (rows["candidate"] < upper)
                        if upper < 1
                        else (rows["candidate"] <= upper)
                    )
                ]
                scores["calibration"].append(
                    {
                        "bin": [round(float(lower), 1), upper],
                        "n": len(subset),
                        "mean_probability": float(subset["candidate"].mean())
                        if len(subset)
                        else None,
                        "observed_rate": float(subset["truth"].mean())
                        if len(subset)
                        else None,
                    }
                )
        results[variable] = scores
    return {
        "reference": "ERA5 gridded reanalysis, not independent station observations",
        "evaluation_period": "2025-01-01 through 2025-12-31 UTC; weekly Wednesday targets",
        "issue_protocol": "Monday 00 UTC IFS run; declared decision Tuesday 12 UTC; Wednesday UTC daily target; ERA5 reference available for training no earlier than seven days after target day",
        "promotion": "No model is promoted to an operational forecast; inspect all cities and folds before selecting a correction.",
        "folds": fold_info,
        "results": results,
        "predictions": all_predictions,
    }


def write_report(
    report: dict, path: Path, forecast_csv: Path, reference_csv: Path
) -> None:
    report["input_sha256"] = {
        "archived_forecasts": hashlib.sha256(forecast_csv.read_bytes()).hexdigest(),
        "era5_reference": hashlib.sha256(reference_csv.read_bytes()).hexdigest(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    predictions_path = path.with_name(path.stem + "-predictions.csv")
    predictions = pd.DataFrame(report.pop("predictions"))
    predictions.to_csv(
        predictions_path, index=False, lineterminator="\n", float_format="%.8f"
    )
    report["predictions_artifact"] = {
        "path": predictions_path.name,
        "rows": len(predictions),
        "csv_sha256": hashlib.sha256(predictions_path.read_bytes()).hexdigest(),
    }
    path.write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
