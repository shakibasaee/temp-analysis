"""Check the predeclared model gate without contacting live data sources."""

import unittest

import numpy as np
import pandas as pd

from forecasting.multi_horizon import TARGETS
from scripts.audit_ssod import STATIONS
from scripts.evaluate_later_station_holdout import decision, failure_diagnostics


def example(days: int) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    frame = pd.DataFrame(
        [
            (city, date, 10.0, 10.0, 10.0)
            for city in STATIONS
            for date in pd.date_range("2026-01-01", periods=days)
        ],
        columns=["City", "target_date", *TARGETS],
    )
    predictions = {
        "persistence": np.full((len(frame), 3), 13.0),
        "seasonal_weekday": np.full((len(frame), 3), 14.0),
        "ridge": np.full((len(frame), 3), 11.0),
    }
    return frame, predictions


class LaterStationHoldoutTests(unittest.TestCase):
    def test_passes_only_with_unique_day_coverage(self):
        frame, predictions = example(100)
        result = decision(frame, predictions)
        self.assertEqual("pass", result["status"])
        self.assertEqual(100, result["unique_station_target_days_by_city"]["Rasht"])

    def test_few_days_are_indeterminate_despite_many_overlapping_forecasts(self):
        frame, predictions = example(99)
        result = decision(frame, predictions)
        self.assertEqual("indeterminate", result["status"])
        self.assertIsNone(result["by_city_target"][0]["city_gate_pass"])

    def test_fails_when_accuracy_gain_does_not_meet_gate(self):
        frame, predictions = example(100)
        predictions["ridge"][:] = 12.9
        result = decision(frame, predictions)
        self.assertEqual("fail", result["status"])
        self.assertFalse(result["by_target"][0]["mae_gate_pass"])

    def test_rejects_misaligned_predictions(self):
        frame, predictions = example(100)
        predictions["ridge"] = predictions["ridge"][:-1]
        with self.assertRaisesRegex(ValueError, "aligned"):
            decision(frame, predictions)

    def test_failure_diagnostics_count_ordering_and_horizon(self):
        frame, predictions = example(1)
        frame["horizon"] = 1
        predictions["ridge"][:, 1] = 12.0
        result = failure_diagnostics(frame, predictions)
        ridge = next(item for item in result["models"] if item["model"] == "ridge")
        self.assertEqual(len(frame), ridge["ordering_violations"])
        self.assertEqual(5, ridge["by_horizon"][0]["unique_city_target_days"])
        self.assertEqual([1, 7], ridge["by_horizon"][0]["horizon_days"])


if __name__ == "__main__":
    unittest.main()
