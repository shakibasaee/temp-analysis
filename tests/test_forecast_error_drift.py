"""Tests for ordered signed-error drift diagnostics."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.forecast_error_drift import analyze, load_aligned


class ForecastErrorDriftTests(unittest.TestCase):
    def test_constant_errors_have_no_alert(self):
        rows = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=100),
                "error": [1.0] * 100,
                "baseline_error": [0.0] * 100,
            }
        )
        self.assertEqual([], analyze(rows)["alerts"])

    def test_detected_date_and_equal_windows(self):
        dates = pd.date_range("2024-01-01", periods=100)
        errors = [0.0] * 50 + [10.0] * 50
        rows = pd.DataFrame({"date": dates, "error": errors, "baseline_error": [0.0] * 100})
        result = analyze(
            rows,
            window_days=14,
            settings={
                "min_instances": 10,
                "delta": 0.005,
                "threshold": 20.0,
                "alpha": 0.9999,
                "mode": "both",
            },
        )
        self.assertTrue(result["alerts"])
        alert = result["alerts"][0]
        self.assertGreaterEqual(alert["index"], 50)
        self.assertEqual(alert["before"]["count"], alert["after"]["count"])
        self.assertEqual(alert["comparison_days_each_side"], 14)

    def test_rejects_modified_evaluation_file(self):
        with tempfile.TemporaryDirectory() as folder:
            altered = Path(folder) / "forecast_eval.csv"
            altered.write_bytes(Path("forecast_eval.csv").read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                load_aligned(
                    altered,
                    Path("forecast_eval.metadata.json"),
                    Path("data/new_weather_data.csv"),
                )


if __name__ == "__main__":
    unittest.main()
