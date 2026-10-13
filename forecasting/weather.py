"""Experimental next-day benchmark for four daily weather targets.

Forecasts are issued after the current day's measurements become available.
The bundled CSV has unknown provenance, so scores are internal diagnostics.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import brier_score_loss, mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .config import ForecastConfig
from .data import validate_daily_data
from .experiment import split_examples

WEATHER_COLUMNS = ("Precipitation_mm", "Wind_Speed_kmh", "Pressure_hPa")
NUMERIC_FEATURES = (
    "temp_today",
    "temp_lag_1",
    "temp_mean_7",
    "wind_today",
    "wind_mean_7",
    "pressure_today",
    "pressure_mean_7",
    "rain_today",
    "rain_rate_30",
    "day_of_year_sin",
    "day_of_year_cos",
)
FEATURES = (*NUMERIC_FEATURES, "City")
TARGETS = {
    "temperature_c": ("target_temperature", "temp_today", "mae"),
    "wind_speed_kmh": ("target_wind", "wind_today", "mae"),
    "pressure_hpa": ("target_pressure", "pressure_today", "mae"),
    "rain_probability": ("target_rain", "rain_rate_30", "brier"),
}


def validate_weather_data(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate the daily key and weather columns without filling missing values."""
    missing = set(WEATHER_COLUMNS) - set(frame)
    if missing:
        raise ValueError(f"Missing weather columns: {sorted(missing)}")
    daily = validate_daily_data(frame)
    extra = frame.loc[:, ["Date_Time", "City", *WEATHER_COLUMNS]].copy()
    extra["Date_Time"] = pd.to_datetime(extra["Date_Time"], errors="coerce")
    for column in WEATHER_COLUMNS:
        raw = extra[column]
        extra[column] = pd.to_numeric(raw, errors="coerce")
        if (raw.notna() & extra[column].isna()).any():
            raise ValueError(f"{column} must contain numeric values or blanks")
        observed = extra[column].dropna().to_numpy(dtype=float)
        if not np.isfinite(observed).all():
            raise ValueError(f"{column} must contain finite values")
        if column != "Pressure_hPa" and (observed < 0).any():
            raise ValueError(f"{column} cannot be negative")
        if column == "Pressure_hPa" and (observed <= 0).any():
            raise ValueError("Pressure_hPa must be positive")
    return (
        daily.merge(extra, on=["Date_Time", "City"], how="left", validate="one_to_one")
        .sort_values(["City", "Date_Time"])
        .reset_index(drop=True)
    )


def make_weather_examples(
    frame: pd.DataFrame, min_history_days: int = 30
) -> pd.DataFrame:
    """Create next-day labels from issue-day and earlier measurements only."""
    if min_history_days < 30:
        raise ValueError("At least 30 days are needed for weather features")
    data = validate_weather_data(frame)
    counts = data.groupby("City", sort=False).size()
    short = counts[counts < min_history_days]
    if not short.empty:
        raise ValueError(
            f"Insufficient daily history for cities: {short.index.tolist()}"
        )
    group = data.groupby("City", sort=False)
    result = (
        data[["City", "Date_Time"]].rename(columns={"Date_Time": "issue_date"}).copy()
    )
    result["target_date"] = result["issue_date"] + pd.Timedelta(days=1)
    result["temp_today"] = data["Temperature_C"]
    result["temp_lag_1"] = group["Temperature_C"].shift(1)
    result["temp_mean_7"] = group["Temperature_C"].transform(
        lambda series: series.rolling(7).mean()
    )
    for column, prefix in (
        ("Wind_Speed_kmh", "wind"),
        ("Pressure_hPa", "pressure"),
    ):
        result[f"{prefix}_today"] = data[column]
        result[f"{prefix}_mean_7"] = group[column].transform(
            lambda series: series.rolling(7, min_periods=3).mean()
        )
    rain = pd.Series(
        np.where(
            data["Precipitation_mm"].isna(),
            np.nan,
            (data["Precipitation_mm"] > 0).astype(float),
        ),
        index=data.index,
    )
    result["rain_today"] = rain
    result["rain_rate_30"] = rain.groupby(data["City"], sort=False).transform(
        lambda series: series.rolling(30, min_periods=15).mean()
    )
    day_of_year = result["target_date"].dt.dayofyear
    result["day_of_year_sin"] = np.sin(2 * np.pi * day_of_year / 365.25)
    result["day_of_year_cos"] = np.cos(2 * np.pi * day_of_year / 365.25)
    result["target_temperature"] = group["Temperature_C"].shift(-1)
    result["target_wind"] = group["Wind_Speed_kmh"].shift(-1)
    result["target_pressure"] = group["Pressure_hPa"].shift(-1)
    result["target_rain"] = rain.groupby(data["City"], sort=False).shift(-1)
    age = group.cumcount() + 1
    result = result.loc[age >= min_history_days].copy()
    if result.empty:
        raise ValueError("No city has enough daily history")
    return result.reset_index(drop=True)


def _fit_model(task: str, train: pd.DataFrame) -> Pipeline:
    numeric = Pipeline(
        [
            ("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
            ("scale", StandardScaler()),
        ]
    )
    transformer = ColumnTransformer(
        [
            ("numeric", numeric, list(NUMERIC_FEATURES)),
            ("city", OneHotEncoder(handle_unknown="ignore"), ["City"]),
        ]
    )
    if task == "rain_probability":
        if train["target"].nunique() < 2:
            raise ValueError("Rain training period needs both wet and dry days")
        estimator = LogisticRegression(max_iter=1000)
    else:
        estimator = Ridge(alpha=10.0)
    model = Pipeline([("features", transformer), ("model", estimator)])
    return model.fit(train[list(FEATURES)], train["target"])


def _model_prediction(task: str, model: Pipeline, part: pd.DataFrame) -> np.ndarray:
    if task == "rain_probability":
        return model.predict_proba(part[list(FEATURES)])[:, 1]
    return np.asarray(model.predict(part[list(FEATURES)]), dtype=float)


def _metrics(
    task: str, part: pd.DataFrame, predictions: np.ndarray
) -> dict[str, float]:
    actual = part["target"].to_numpy(dtype=float)
    if task == "rain_probability":
        return {"brier": round(float(brier_score_loss(actual, predictions)), 4)}
    return {
        "mae": round(float(mean_absolute_error(actual, predictions)), 4),
        "rmse": round(float(np.sqrt(mean_squared_error(actual, predictions))), 4),
        "bias": round(float(np.mean(predictions - actual)), 4),
    }


def _scores(task: str, model: Pipeline, part: pd.DataFrame) -> dict[str, Any]:
    baseline = part[TARGETS[task][1]].to_numpy(dtype=float)
    candidate = _model_prediction(task, model, part)
    return {
        "rows": int(len(part)),
        "baseline": _metrics(task, part, baseline),
        "model": _metrics(task, part, candidate),
        "by_city": {
            city: {
                "rows": int(len(city_rows)),
                "baseline": _metrics(
                    task, city_rows, city_rows[TARGETS[task][1]].to_numpy(dtype=float)
                ),
                "model": _metrics(
                    task,
                    city_rows,
                    candidate[part["City"].to_numpy() == city],
                ),
            }
            for city, city_rows in part.groupby("City", sort=True)
        },
    }


def benchmark_weather(frame: pd.DataFrame, config: ForecastConfig) -> dict[str, Any]:
    """Compare baseline and model on chronological validation and test periods."""
    examples = make_weather_examples(frame, config.min_history_days)
    tasks: dict[str, Any] = {}
    for task, (target, baseline, primary_metric) in TARGETS.items():
        eligible = examples.loc[
            examples[target].notna() & examples[baseline].notna()
        ].copy()
        eligible["target"] = eligible[target]
        train, validation, test = split_examples(eligible, config)
        validation_model = _fit_model(task, train)
        test_model = _fit_model(task, pd.concat([train, validation]))
        tasks[task] = {
            "target": target,
            "primary_metric": primary_metric,
            "model": "logistic_regression" if task == "rain_probability" else "ridge",
            "baseline": "30_day_wet_frequency"
            if task == "rain_probability"
            else "persistence",
            "eligible_rows": int(len(eligible)),
            "excluded_missing_target_or_baseline": int(len(examples) - len(eligible)),
            "train_rows": int(len(train)),
            "validation": _scores(task, validation_model, validation),
            "test": _scores(task, test_model, test),
        }
    data = validate_weather_data(frame)
    return {
        "task": "Next-day city weather after issue-day measurements are available",
        "source_metadata": "Not supplied; document dataset origin before using scores as external evidence",
        "evaluation": "Chronological target-date splits; model fit through each split boundary; daily actuals may update lag features",
        "config": config.to_dict(),
        "data": {
            "rows": int(len(data)),
            "cities": sorted(data["City"].unique().tolist()),
            "first_date": str(data["Date_Time"].min().date()),
            "last_date": str(data["Date_Time"].max().date()),
        },
        "targets": tasks,
    }


def predict_weather_baselines(
    frame: pd.DataFrame,
    min_history_days: int = 30,
    *,
    allow_historical: bool = False,
    today: date | None = None,
) -> pd.DataFrame:
    """Issue transparent baselines; require an explicit flag for stale data."""
    examples = make_weather_examples(frame, min_history_days)
    latest = examples.groupby("City", sort=False).tail(1).sort_values("City")
    if latest["issue_date"].nunique() != 1:
        raise ValueError("Cities must have the same latest observation date")
    forecast_date = latest["target_date"].iloc[0].date()
    if not allow_historical and forecast_date < (today or date.today()):
        raise ValueError(
            "Input history is stale; use --allow-historical for a dated replay"
        )
    required = [entry[1] for entry in TARGETS.values()]
    if latest[required].isna().any().any():
        raise ValueError(
            "Latest daily weather values are incomplete for baseline forecasts"
        )
    return pd.DataFrame(
        {
            "Date": latest["target_date"].dt.date.to_numpy(),
            "City": latest["City"].to_numpy(),
            "Temperature_C_Baseline": latest["temp_today"].to_numpy(),
            "Wind_Speed_kmh_Baseline": latest["wind_today"].to_numpy(),
            "Pressure_hPa_Baseline": latest["pressure_today"].to_numpy(),
            "Rain_Probability_Baseline": latest["rain_rate_30"].to_numpy(),
        }
    )
