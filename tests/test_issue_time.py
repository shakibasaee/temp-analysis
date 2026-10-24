"""Guard the archived benchmark's timing, integrity and committed scores."""

import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from forecasting.archived_runs import parse_run
from forecasting.issue_time import evaluate, load_pairs, training_before_issue

ROOT = Path(__file__).resolve().parents[1]
FORECAST = ROOT / "data" / "archived_ifs_weekly.csv"
REFERENCE = ROOT / "data" / "era5_daily_2022_2025.csv"
MANIFEST = ROOT / "data" / "archived_ifs_weekly.manifest.json"
REPORT = ROOT / "reports" / "archived-ifs-2025.json"


class ArchivedRunTests(unittest.TestCase):
    def assert_reports_close(self, actual, expected):
        """Allow platform-level floating point differences, not changed scores."""
        if isinstance(actual, dict):
            self.assertEqual(set(actual), set(expected))
            for key in actual:
                self.assert_reports_close(actual[key], expected[key])
        elif isinstance(actual, list):
            self.assertEqual(len(actual), len(expected))
            for left, right in zip(actual, expected, strict=True):
                self.assert_reports_close(left, right)
        elif isinstance(actual, float):
            self.assertTrue(math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-9))
        else:
            self.assertEqual(actual, expected)

    def test_snapshot_integrity_and_fixed_lead(self):
        metadata = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(
            hashlib.sha256(FORECAST.read_bytes()).hexdigest(), metadata["csv_sha256"]
        )
        self.assertEqual(len(metadata["requests"]), 92)
        self.assertEqual(len(metadata["response_grid_coordinates"]), 5)
        self.assertEqual(len({r["response_sha256"] for r in metadata["requests"]}), 92)
        pairs = load_pairs(FORECAST, REFERENCE)
        self.assertEqual(len(pairs), 460)
        self.assertEqual(pairs.groupby("target_date_utc").size().unique().tolist(), [5])
        dates = pairs["target_date_utc"].drop_duplicates().sort_values()
        self.assertTrue((dates.diff().dropna() == pd.Timedelta(days=7)).all())

    def test_future_reference_cannot_enter_training(self):
        pairs = load_pairs(FORECAST, REFERENCE)
        first_issue = pairs.loc[
            pairs["target_date_utc"].dt.year == 2025, "issue_utc"
        ].min()
        training = training_before_issue(pairs, first_issue)
        self.assertEqual(
            training["target_date_utc"].max().date().isoformat(), "2024-12-18"
        )
        self.assertFalse(
            (training["target_date_utc"] >= pd.Timestamp("2024-12-25", tz="UTC")).any()
        )
        self.assertTrue(
            (training["target_date_utc"] + pd.Timedelta(days=7) <= first_issue).all()
        )

    def test_shifted_target_and_missing_reference_rejected(self):
        sample = pd.read_csv(FORECAST)
        with tempfile.TemporaryDirectory() as directory:
            altered = Path(directory) / "forecast.csv"
            sample.loc[0, "target_date_utc"] = "2025-01-02"
            sample.to_csv(altered, index=False)
            with self.assertRaises(ValueError):
                load_pairs(altered, REFERENCE)
            sample = pd.read_csv(FORECAST)
            sample.loc[0, "City"] = "Unknown"
            sample.to_csv(altered, index=False)
            with self.assertRaises(ValueError):
                load_pairs(altered, REFERENCE)

    def test_reproducible_scores_and_thresholds(self):
        measured = evaluate(load_pairs(FORECAST, REFERENCE))
        committed = json.loads(REPORT.read_text(encoding="utf-8"))
        self.assert_reports_close(measured["results"], committed["results"])
        self.assertEqual(measured["folds"], committed["folds"])
        predictions = REPORT.with_name(committed["predictions_artifact"]["path"])
        self.assertEqual(
            hashlib.sha256(predictions.read_bytes()).hexdigest(),
            committed["predictions_artifact"]["csv_sha256"],
        )
        self.assertEqual(
            set(measured["results"]),
            {
                "temperature_c",
                "wind_speed_kmh",
                "pressure_hpa",
                "precipitation_gt_0mm",
                "precipitation_ge_1mm",
            },
        )
        for scores in measured["results"].values():
            self.assertEqual(scores["n"], 265)

    def test_parser_rejects_incomplete_target(self):
        from datetime import date

        item = {
            "timezone": "GMT",
            "utc_offset_seconds": 0,
            "daily_units": {
                "temperature_2m_mean": "°C",
                "wind_speed_10m_mean": "km/h",
                "pressure_msl_mean": "hPa",
                "precipitation_sum": "mm",
            },
            "daily": {
                "time": ["2025-01-06", "2025-01-07", "2025-01-08"],
                "temperature_2m_mean": [1, 2, None],
                "wind_speed_10m_mean": [1, 2, 3],
                "pressure_msl_mean": [1000, 1001, 1002],
                "precipitation_sum": [0, 0, 0],
            },
        }
        with self.assertRaises(ValueError):
            parse_run([item.copy() for _ in range(5)], date(2025, 1, 6))


if __name__ == "__main__":
    unittest.main()
