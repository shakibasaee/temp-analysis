"""Reusable linear-regression baseline for city temperature forecasting."""

from __future__ import annotations

from math import ceil
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.utils.validation import check_is_fitted

try:  # Package import (tests and library usage)
    from ..evaluation.metrics import MetricsCalculator
    from ..model_config import DEFAULT_CONFIG, LinearRegressionConfig
except ImportError:  # Script import (streamlit run scripts/app.py)
    from evaluation.metrics import MetricsCalculator
    from model_config import DEFAULT_CONFIG, LinearRegressionConfig


class LinearRegressionModel(BaseEstimator):
    """Linear-regression baseline with shared training/inference preprocessing.

    Dates are expanded into configurable calendar features. Periodic calendar
    values also receive sine/cosine representations so that, for example,
    December 31 and January 1 are close in feature space. Cities are encoded
    by the fitted pipeline, avoiding hard-coded city names.
    """

    _SUPPORTED_TEMPORAL_FEATURES = {
        "day_of_year": ("dayofyear", 365.25),
        "month": ("month", 12.0),
        "year": ("year", None),
        "day_of_week": ("dayofweek", 7.0),
        "day": ("day", 31.0),
        "week_of_year": ("isocalendar_week", 52.1775),
    }

    def __init__(self, config: LinearRegressionConfig | None = None) -> None:
        self.config = config or DEFAULT_CONFIG
        self._validate_config()

    def _validate_config(self) -> None:
        if not 0 < self.config.test_size < 1:
            raise ValueError("test_size must be strictly between 0 and 1")
        if self.config.feature_selection_mode not in {"all", "specific"}:
            raise ValueError("feature_selection_mode must be 'all' or 'specific'")
        if (
            self.config.feature_selection_mode == "specific"
            and not self.config.selected_cities
        ):
            raise ValueError(
                "selected_cities is required when feature_selection_mode='specific'"
            )

        unknown = set(self.config.temporal_features) - set(
            self._SUPPORTED_TEMPORAL_FEATURES
        )
        if unknown:
            raise ValueError(f"Unsupported temporal features: {sorted(unknown)}")

    def _validate_frame(self, df: pd.DataFrame, require_target: bool) -> None:
        required = {self.config.date_column, self.config.city_column}
        if require_target:
            required.add(self.config.target_column)
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")
        if df.empty:
            raise ValueError("Cannot use an empty dataframe")

    def _filter_cities(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.config.feature_selection_mode != "specific":
            return df.copy()
        filtered = df[df[self.config.city_column].isin(self.config.selected_cities)]
        if filtered.empty:
            raise ValueError("No rows match the configured selected_cities")
        return filtered.copy()

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create model-ready calendar and city features without mutating input."""
        self._validate_frame(df, require_target=False)
        result = pd.DataFrame(index=df.index)
        dates = pd.to_datetime(df[self.config.date_column], errors="coerce")
        if dates.isna().any():
            invalid_count = int(dates.isna().sum())
            raise ValueError(
                f"{self.config.date_column} contains {invalid_count} invalid date(s)"
            )

        for feature in self.config.temporal_features:
            accessor, period = self._SUPPORTED_TEMPORAL_FEATURES[feature]
            if accessor == "isocalendar_week":
                values = dates.dt.isocalendar().week.astype(float)
            else:
                values = getattr(dates.dt, accessor).astype(float)
            result[feature] = values
            if period is not None:
                angle = 2 * np.pi * values / period
                result[f"{feature}_sin"] = np.sin(angle)
                result[f"{feature}_cos"] = np.cos(angle)

        result[self.config.city_column] = df[self.config.city_column].astype(str)
        return result

    def _build_pipeline(self, temporal_columns: list[str]) -> Pipeline:
        numeric_transformer: Any = (
            StandardScaler() if self.config.normalize_features else "passthrough"
        )
        preprocessor = ColumnTransformer(
            transformers=[
                ("temporal", numeric_transformer, temporal_columns),
                (
                    "city",
                    OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                    [self.config.city_column],
                ),
            ],
            remainder="drop",
        )
        return Pipeline(
            [("preprocessor", preprocessor), ("regressor", LinearRegression())]
        )

    def fit(self, df: pd.DataFrame) -> "LinearRegressionModel":
        """Fit the full preprocessing and regression pipeline."""
        self._validate_frame(df, require_target=True)
        training_df = self._filter_cities(df).dropna(
            subset=[self.config.target_column]
        )
        if training_df.empty:
            raise ValueError("No non-null target values are available for training")

        features = self.engineer_features(training_df)
        target = pd.to_numeric(
            training_df[self.config.target_column], errors="coerce"
        )
        valid = target.notna()
        if not valid.any():
            raise ValueError("Target column contains no numeric values")

        self.temporal_columns_ = [
            column for column in features.columns if column != self.config.city_column
        ]
        self.pipeline_ = self._build_pipeline(self.temporal_columns_)
        self.pipeline_.fit(features.loc[valid], target.loc[valid])
        self.training_rows_ = int(valid.sum())
        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict temperatures for raw date/city rows."""
        check_is_fitted(self, "pipeline_")
        return self.pipeline_.predict(self.engineer_features(df))

    def evaluate(self, df: pd.DataFrame) -> dict[str, float]:
        """Return flat metrics and retain a detailed confidence-interval report."""
        self._validate_frame(df, require_target=True)
        actual = pd.to_numeric(df[self.config.target_column], errors="coerce")
        valid = actual.notna()
        if not valid.any():
            raise ValueError("Evaluation target contains no numeric values")
        predicted = self.predict(df.loc[valid])
        calculator = MetricsCalculator(random_seed=self.config.random_seed)
        self.metrics_report_ = calculator.generate_report(actual.loc[valid], predicted)
        return calculator.calculate(actual.loc[valid], predicted)

    def split_data(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Split data reproducibly, keeping whole dates together by default."""
        self._validate_frame(df, require_target=True)
        data = self._filter_cities(df)
        if self.config.shuffle:
            train, test = train_test_split(
                data,
                test_size=self.config.test_size,
                shuffle=True,
                random_state=self.config.random_seed,
            )
            return train.copy(), test.copy()

        dates = pd.to_datetime(data[self.config.date_column], errors="coerce")
        if dates.isna().any():
            raise ValueError(f"{self.config.date_column} contains invalid dates")
        unique_dates = np.sort(dates.unique())
        if len(unique_dates) < 2:
            raise ValueError("At least two distinct dates are required for evaluation")
        test_date_count = min(
            max(1, ceil(len(unique_dates) * self.config.test_size)),
            len(unique_dates) - 1,
        )
        first_test_date = unique_dates[-test_date_count]
        train = data.loc[dates < first_test_date].sort_values(self.config.date_column)
        test = data.loc[dates >= first_test_date].sort_values(self.config.date_column)
        return train.copy(), test.copy()

    def fit_evaluate(
        self, df: pd.DataFrame, *, refit_full: bool = True
    ) -> dict[str, float]:
        """Fit on the training period, evaluate on the future period, then refit."""
        train, test = self.split_data(df)
        self.fit(train)
        self.evaluate(train)
        train_report = self.metrics_report_
        metrics = self.evaluate(test)
        test_report = self.metrics_report_
        self.train_metrics_report_ = train_report
        self.test_metrics_report_ = test_report
        self.train_rows_ = len(train)
        self.test_rows_ = len(test)
        self.metrics_ = metrics
        if refit_full:
            self.fit(self._filter_cities(df))
            self.metrics_ = metrics
            self.metrics_report_ = test_report
        return metrics

    @property
    def feature_names_(self) -> list[str]:
        """Names of transformed features used by the fitted regressor."""
        check_is_fitted(self, "pipeline_")
        names = self.pipeline_.named_steps["preprocessor"].get_feature_names_out()
        return [str(name) for name in names]
