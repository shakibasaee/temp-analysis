"""Temporal and schema checks for the three-target research backtest."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from forecasting.multi_horizon import load_dataset, make_examples


class MultiHorizonTests(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range("2023-01-01", periods=100)
        self.data = pd.DataFrame(
            {
                "Date": dates,
                "City": "Yazd",
                "Mean_C": np.arange(100, dtype=float),
                "Min_C": np.arange(100, dtype=float) - 2,
                "Max_C": np.arange(100, dtype=float) + 2,
            }
        )

    def test_features_only_use_values_available_at_issue(self):
        examples = make_examples(self.data)
        row = examples[(examples["issue_date"] == "2023-02-07") & (examples["horizon"] == 1)].iloc[
            0
        ]
        self.assertEqual(pd.Timestamp("2023-01-31"), row["available_through"])
        self.assertEqual(pd.Timestamp("2023-02-08"), row["target_date"])
        self.assertEqual(30, row["last_mean"])
        self.assertEqual(24, row["seasonal_mean"])
        modified = self.data.copy()
        modified.loc[modified["Date"] > "2023-01-31", "Mean_C"] += 1000
        changed = make_examples(modified)
        changed_row = changed[
            (changed["issue_date"] == "2023-02-07") & (changed["horizon"] == 1)
        ].iloc[0]
        self.assertEqual(row["last_mean"], changed_row["last_mean"])
        self.assertEqual(row["week_mean"], changed_row["week_mean"])
        self.assertNotEqual(row["Mean_C"], changed_row["Mean_C"])

    def test_rejects_inconsistent_daily_values(self):
        invalid = self.data.copy()
        invalid.loc[0, "Min_C"] = 10
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "daily.csv"
            invalid.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "inconsistent"):
                load_dataset(path)


if __name__ == "__main__":
    unittest.main()
