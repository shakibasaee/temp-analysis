"""Checks for the isolated next-day regression evaluation."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.one_city_forecast_eval import evaluate, prepare_city


class OneCityForecastEvalTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "weather.csv"
        dates = pd.date_range("2023-01-01", periods=50)
        self.data = pd.DataFrame(
            {
                "Date_Time": dates,
                "City": "Mashhad",
                "Temperature_C": 10 + np.sin(np.arange(50) / 5),
            }
        )
        self.data.to_csv(self.path, index=False)

    def test_chronological_split_and_no_test_target_in_model(self):
        output, summary = evaluate(self.path, "Mashhad")
        self.assertEqual(["date", "actual", "predicted"], output.columns.tolist())
        self.assertEqual(40, summary["train_rows"])
        self.assertEqual(10, summary["test_rows"])
        self.assertEqual("2023-02-10", output.iloc[0]["date"])
        changed = self.data.copy()
        changed.loc[40:, "Temperature_C"] += 100
        changed.to_csv(self.path, index=False)
        changed_output, _ = evaluate(self.path, "Mashhad")
        np.testing.assert_allclose(output["predicted"], changed_output["predicted"])

    def test_reports_missing_date(self):
        self.data.drop(index=10).to_csv(self.path, index=False)
        with self.assertRaisesRegex(ValueError, "2023-01-11"):
            prepare_city(self.path, "Mashhad")


if __name__ == "__main__":
    unittest.main()
