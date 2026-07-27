"""Regression metrics and uncertainty estimates.

MAPE is reported as a percentage. Targets whose absolute value is at or below
``mape_epsilon`` are excluded because percentage error is undefined at zero.
Confidence intervals use paired moving-block bootstrap resampling so each
actual/predicted pair remains aligned and short-range time dependence is not
discarded.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np


class MetricsCalculator:
    """Calculate regression metrics and deterministic bootstrap intervals.

    Args:
        confidence_level: Coverage of the two-sided percentile interval.
        n_bootstrap: Number of paired bootstrap resamples.
        random_seed: Seed used to make confidence intervals reproducible.
        mape_epsilon: Absolute targets at or below this value are excluded
            from MAPE to avoid division by zero and unstable percentages.
        block_size: Moving-bootstrap block length. By default, the square root
            of the sample size is used. Set to 1 for ordinary IID bootstrap.
    """

    def __init__(
        self,
        confidence_level: float = 0.95,
        n_bootstrap: int = 1_000,
        random_seed: int = 42,
        mape_epsilon: float = 1e-8,
        block_size: int | None = None,
    ) -> None:
        if not 0 < confidence_level < 1:
            raise ValueError("confidence_level must be strictly between 0 and 1")
        if n_bootstrap < 1:
            raise ValueError("n_bootstrap must be at least 1")
        if mape_epsilon < 0:
            raise ValueError("mape_epsilon cannot be negative")
        if block_size is not None and block_size < 1:
            raise ValueError("block_size must be at least 1")
        self.confidence_level = confidence_level
        self.n_bootstrap = n_bootstrap
        self.random_seed = random_seed
        self.mape_epsilon = mape_epsilon
        self.block_size = block_size

    @staticmethod
    def _as_arrays(
        y_true: Sequence[float], y_pred: Sequence[float]
    ) -> tuple[np.ndarray, np.ndarray]:
        actual = np.asarray(y_true, dtype=float).reshape(-1)
        predicted = np.asarray(y_pred, dtype=float).reshape(-1)
        if actual.size == 0:
            raise ValueError("Metrics require at least one observation")
        if actual.shape != predicted.shape:
            raise ValueError("y_true and y_pred must have the same length")
        if not np.isfinite(actual).all() or not np.isfinite(predicted).all():
            raise ValueError("y_true and y_pred must contain only finite values")
        return actual, predicted

    @staticmethod
    def mae(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
        """Return mean absolute error in the target's original unit."""
        actual, predicted = MetricsCalculator._as_arrays(y_true, y_pred)
        return float(np.mean(np.abs(actual - predicted)))

    @staticmethod
    def rmse(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
        """Return root mean squared error in the target's original unit."""
        actual, predicted = MetricsCalculator._as_arrays(y_true, y_pred)
        return float(np.sqrt(np.mean(np.square(actual - predicted))))

    def mape(self, y_true: Sequence[float], y_pred: Sequence[float]) -> float:
        """Return mean absolute percentage error as a percentage (0-100+)."""
        actual, predicted = self._as_arrays(y_true, y_pred)
        valid = np.abs(actual) > self.mape_epsilon
        if not valid.any():
            raise ValueError("MAPE is undefined because all target values are zero")
        percentage_errors = np.abs(
            (actual[valid] - predicted[valid]) / actual[valid]
        )
        return float(np.mean(percentage_errors) * 100.0)

    @staticmethod
    def r2(y_true: Sequence[float], y_pred: Sequence[float]) -> float:
        """Return the coefficient of determination."""
        actual, predicted = MetricsCalculator._as_arrays(y_true, y_pred)
        if actual.size < 2:
            return float("nan")
        denominator = np.sum(np.square(actual - np.mean(actual)))
        if denominator == 0:
            return float("nan")
        numerator = np.sum(np.square(actual - predicted))
        return float(1.0 - numerator / denominator)

    def _metric_functions(self) -> dict[str, Callable[..., float]]:
        return {
            "mae": self.mae,
            "rmse": self.rmse,
            "mape": self.mape,
            "r2": self.r2,
        }

    def calculate(
        self, y_true: Sequence[float], y_pred: Sequence[float]
    ) -> dict[str, float]:
        """Return a flat metrics dictionary for application compatibility."""
        actual, predicted = self._as_arrays(y_true, y_pred)
        return {
            name: metric(actual, predicted)
            for name, metric in self._metric_functions().items()
        }

    def confidence_intervals(
        self, y_true: Sequence[float], y_pred: Sequence[float]
    ) -> dict[str, dict[str, float]]:
        """Estimate percentile intervals using paired moving-block bootstrap."""
        actual, predicted = self._as_arrays(y_true, y_pred)
        rng = np.random.default_rng(self.random_seed)
        block_size = min(
            self.block_size or max(1, round(np.sqrt(actual.size))), actual.size
        )
        block_count = int(np.ceil(actual.size / block_size))
        samples: dict[str, list[float]] = {
            name: [] for name in self._metric_functions()
        }

        for _ in range(self.n_bootstrap):
            starts = rng.integers(
                0, actual.size - block_size + 1, size=block_count
            )
            indices = np.concatenate(
                [np.arange(start, start + block_size) for start in starts]
            )[: actual.size]
            sample_actual = actual[indices]
            sample_predicted = predicted[indices]
            for name, metric in self._metric_functions().items():
                try:
                    value = metric(sample_actual, sample_predicted)
                except ValueError:
                    continue
                if np.isfinite(value):
                    samples[name].append(value)

        alpha = (1.0 - self.confidence_level) / 2.0
        intervals: dict[str, dict[str, float]] = {}
        for name, values in samples.items():
            if not values:
                intervals[name] = {"lower": float("nan"), "upper": float("nan")}
                continue
            lower, upper = np.quantile(values, [alpha, 1.0 - alpha])
            intervals[name] = {"lower": float(lower), "upper": float(upper)}
        return intervals

    def generate_report(
        self, y_true: Sequence[float], y_pred: Sequence[float]
    ) -> dict[str, Any]:
        """Return a JSON-serializable report with values and uncertainty."""
        actual, predicted = self._as_arrays(y_true, y_pred)
        values = self.calculate(actual, predicted)
        intervals = self.confidence_intervals(actual, predicted)
        excluded_from_mape = int(
            np.sum(np.abs(actual) <= self.mape_epsilon)
        )
        return {
            "metadata": {
                "sample_size": int(actual.size),
                "confidence_level": self.confidence_level,
                "bootstrap_iterations": self.n_bootstrap,
                "bootstrap_method": "paired_moving_block",
                "bootstrap_block_size": min(
                    self.block_size or max(1, round(np.sqrt(actual.size))),
                    actual.size,
                ),
                "random_seed": self.random_seed,
                "mape_unit": "percent",
                "mape_excluded_zero_targets": excluded_from_mape,
            },
            "metrics": {
                name: {
                    "value": value,
                    "confidence_interval": intervals[name],
                }
                for name, value in values.items()
            },
        }

    @staticmethod
    def to_json(report: dict[str, Any], indent: int = 2) -> str:
        """Serialize a generated metrics report to JSON."""
        return json.dumps(report, indent=indent, allow_nan=True)

    def generate_json_report(
        self,
        y_true: Sequence[float],
        y_pred: Sequence[float],
        indent: int = 2,
    ) -> str:
        """Calculate and serialize a metrics report in one call."""
        return self.to_json(self.generate_report(y_true, y_pred), indent=indent)
