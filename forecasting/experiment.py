"""Chronological model comparison, selection, persistence and inference."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import ForecastConfig
from .features import FEATURES, NUMERIC_FEATURES, make_examples

MODEL_NAMES = (
    "persistence",
    "seasonal_naive_7",
    "calendar_linear",
    "ridge_lags",
    "extra_trees_lags",
)


def split_examples(
    examples: pd.DataFrame, config: ForecastConfig
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Partition by forecast target date, never by randomly chosen rows."""
    labelled = examples.loc[examples["target"].notna()].copy()
    train_end = pd.Timestamp(config.train_end)
    validation_end = pd.Timestamp(config.validation_end)
    train = labelled.loc[labelled["target_date"] <= train_end]
    validation = labelled.loc[
        (labelled["target_date"] > train_end)
        & (labelled["target_date"] <= validation_end)
    ]
    test = labelled.loc[labelled["target_date"] > validation_end]
    if min(map(len, (train, validation, test))) == 0:
        raise ValueError(
            "Train, validation and test periods must each contain examples"
        )
    if not (
        train["target_date"].max()
        < validation["target_date"].min()
        < test["target_date"].min()
    ):
        raise ValueError("Chronological partitions overlap")
    return train, validation, test


def _fit(name: str, train: pd.DataFrame, seed: int) -> Any:
    if name in ("persistence", "seasonal_naive_7"):
        return None
    if name == "calendar_linear":
        # Preserve the original project's calendar-only regression as a comparator.
        from scripts.models.linear_regression import LinearRegressionModel

        calendar = train.rename(
            columns={"target_date": "Date_Time", "target": "Temperature_C"}
        )
        return LinearRegressionModel().fit(calendar)
    transformer = ColumnTransformer(
        [
            ("numeric", StandardScaler(), list(NUMERIC_FEATURES)),
            ("city", OneHotEncoder(handle_unknown="ignore"), ["City"]),
        ]
    )
    estimator = (
        Ridge(alpha=10.0)
        if name == "ridge_lags"
        else ExtraTreesRegressor(
            n_estimators=200,
            min_samples_leaf=3,
            max_features=0.8,
            random_state=seed,
            n_jobs=1,
        )
    )
    pipeline = Pipeline([("features", transformer), ("model", estimator)])
    return pipeline.fit(train[list(FEATURES)], train["target"])


def _predict(name: str, model: Any, examples: pd.DataFrame) -> np.ndarray:
    if name == "persistence":
        return examples["temp_today"].to_numpy(dtype=float)
    if name == "seasonal_naive_7":
        return examples["temp_lag_6"].to_numpy(dtype=float)
    if name == "calendar_linear":
        calendar = examples.rename(columns={"target_date": "Date_Time"})
        return np.asarray(model.predict(calendar), dtype=float)
    return np.asarray(model.predict(examples[list(FEATURES)]), dtype=float)


def _metrics(actual: pd.Series, predicted: np.ndarray) -> dict[str, float]:
    y = actual.to_numpy(dtype=float)
    denominator = np.abs(y) + np.abs(predicted)
    smape = (
        np.mean(
            np.divide(
                2 * np.abs(y - predicted),
                denominator,
                out=np.zeros_like(y),
                where=denominator > 0,
            )
        )
        * 100
    )
    return {
        "mae": round(float(mean_absolute_error(y, predicted)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(y, predicted))), 4),
        "smape_percent": round(float(smape), 4),
        "r2": round(float(r2_score(y, predicted)), 4),
    }


def benchmark(data: pd.DataFrame, config: ForecastConfig) -> dict[str, Any]:
    """Select on validation MAE, then evaluate all candidates once on held-out test."""
    examples = make_examples(data, config.min_history_days)
    train, validation, test = split_examples(examples, config)
    results: dict[str, Any] = {}
    for name in MODEL_NAMES:
        validation_model = _fit(name, train, config.random_seed)
        validation_metrics = _metrics(
            validation["target"], _predict(name, validation_model, validation)
        )
        results[name] = {"validation": validation_metrics}
    best = min(MODEL_NAMES, key=lambda name: results[name]["validation"]["mae"])
    baseline_mae = results["persistence"]["validation"]["mae"]
    relative_gain = (
        (baseline_mae - results[best]["validation"]["mae"]) / baseline_mae
        if baseline_mae > 0
        else 0.0
    )
    selected = (
        best if relative_gain >= config.minimum_relative_mae_gain else "persistence"
    )
    for name in MODEL_NAMES:
        test_model = _fit(name, pd.concat([train, validation]), config.random_seed)
        test_metrics = _metrics(test["target"], _predict(name, test_model, test))
        results[name]["test"] = test_metrics
    return {
        "task": "Next-day recorded daily temperature (C) by city; forecast issued after today's observation",
        "selection_rule": "Minimum validation MAE, provided relative gain over persistence meets configured threshold; test untouched until selection",
        "config": config.to_dict(),
        "data": {
            "observations": int(len(data)),
            "cities": sorted(data["City"].unique().tolist()),
            "first_date": str(data["Date_Time"].min().date()),
            "last_date": str(data["Date_Time"].max().date()),
        },
        "splits": {
            label: {
                "rows": int(len(part)),
                "first_target": str(part["target_date"].min().date()),
                "last_target": str(part["target_date"].max().date()),
            }
            for label, part in (
                ("train", train),
                ("validation", validation),
                ("test", test),
            )
        },
        "models": results,
        "selected_model": selected,
    }


def train_final(
    data: pd.DataFrame, config: ForecastConfig, selected_model: str
) -> dict[str, Any]:
    """Fit the selected model on all known labelled dates for future inference."""
    if selected_model not in MODEL_NAMES:
        raise ValueError(f"Unknown model: {selected_model}")
    labelled = make_examples(data, config.min_history_days).dropna(subset=["target"])
    return {
        "format_version": 1,
        "selected_model": selected_model,
        "model": _fit(selected_model, labelled, config.random_seed),
        "config": config.to_dict(),
        "trained_through": str(data["Date_Time"].max().date()),
        "cities": sorted(data["City"].unique().tolist()),
        "training_rows": int(len(labelled)),
    }


def predict_next_day(artifact: dict[str, Any], data: pd.DataFrame) -> pd.DataFrame:
    """Forecast the day after each city's most recent supplied observation."""
    if artifact.get("format_version") != 1:
        raise ValueError("Unsupported model artifact version")
    config = ForecastConfig(**artifact["config"])
    examples = make_examples(data, config.min_history_days)
    latest = examples.groupby("City", sort=False).tail(1).sort_values("City").copy()
    missing_cities = set(artifact["cities"]) - set(latest["City"])
    if missing_cities:
        raise ValueError(
            f"Missing history for trained cities: {sorted(missing_cities)}"
        )
    unseen_cities = set(latest["City"]) - set(artifact["cities"])
    if unseen_cities:
        raise ValueError(f"No trained model for cities: {sorted(unseen_cities)}")
    if (
        latest["issue_date"].dt.date < date.fromisoformat(artifact["trained_through"])
    ).any():
        raise ValueError("Prediction history predates the model's training data")
    predicted = _predict(artifact["selected_model"], artifact["model"], latest)
    return pd.DataFrame(
        {
            "Date": latest["target_date"].dt.date.to_numpy(),
            "City": latest["City"].to_numpy(),
            "Predicted_Temperature_C": predicted,
        }
    )


def save_artifact(artifact: dict[str, Any], path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, target)


def load_artifact(path: str | Path) -> dict[str, Any]:
    """Load only artifacts from trusted local sources; joblib uses pickle."""
    artifact = joblib.load(path)
    if not isinstance(artifact, dict) or artifact.get("format_version") != 1:
        raise ValueError("Invalid model artifact")
    return artifact
