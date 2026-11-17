"""Temporal and schema checks for the three-target research backtest."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from forecasting.multi_horizon import (
    FEATURES,
    NUMERIC,
    fit_ridge,
    largest_ridge_errors,
    load_dataset,
    make_examples,
    validate_temporal_contract,
)


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

    def test_all_horizons_and_targets_ignore_unavailable_future_values(self):
        original = make_examples(self.data)
        issue = pd.Timestamp("2023-02-20")
        selected = original[original["issue_date"].eq(issue)].set_index("horizon")
        self.assertEqual({1, 30}, {1, 30} & set(selected.index))
        available = issue - pd.Timedelta(days=7)
        changed_data = self.data.copy()
        changed_data.loc[changed_data["Date"] > available, ["Mean_C", "Min_C", "Max_C"]] += 1000
        changed = make_examples(changed_data)
        selected_changed = changed[changed["issue_date"].eq(issue)].set_index("horizon")
        for horizon in (1, 30):
            for feature in (
                *(feature for feature in FEATURES if feature != "horizon"),
                "seasonal_mean",
                "seasonal_min",
                "seasonal_max",
            ):
                self.assertEqual(
                    selected.loc[horizon, feature], selected_changed.loc[horizon, feature]
                )
            for target in ("Mean_C", "Min_C", "Max_C"):
                self.assertNotEqual(
                    selected.loc[horizon, target], selected_changed.loc[horizon, target]
                )

    def test_rejects_tampered_temporal_contract(self):
        examples = make_examples(self.data)
        invalid = examples.copy()
        invalid.loc[0, "available_through"] += pd.Timedelta(days=1)
        with self.assertRaisesRegex(ValueError, "publication lag"):
            validate_temporal_contract(invalid)
        invalid = examples.copy()
        invalid.loc[0, "target_date"] += pd.Timedelta(days=1)
        with self.assertRaisesRegex(ValueError, "Target date"):
            validate_temporal_contract(invalid)

    def test_scaling_is_fit_on_training_rows(self):
        examples = make_examples(self.data)
        train = examples.iloc[:20]
        fitted = fit_ridge(train)
        scaler = fitted.named_steps["preprocess"].named_transformers_["numeric"]
        np.testing.assert_allclose(scaler.mean_, train[list(NUMERIC)].mean().to_numpy())

    def test_rejects_missing_calendar_day(self):
        invalid = self.data.drop(index=17)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "daily.csv"
            invalid.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "date gap"):
                load_dataset(path)

    def test_rejects_invalid_dates_and_missing_target(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "daily.csv"
            invalid = self.data.copy()
            invalid["Date"] = invalid["Date"].astype(str)
            invalid.loc[0, "Date"] = "not-a-date"
            invalid.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "Missing or invalid"):
                load_dataset(path)
            invalid = self.data.copy()
            invalid.loc[0, "Mean_C"] = np.nan
            invalid.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "Missing or invalid"):
                load_dataset(path)

    def test_largest_errors_count_distinct_city_target_days(self):
        rows = pd.DataFrame(
            {
                "City": ["Yazd"] * 3,
                "issue_date": pd.to_datetime(["2025-01-01", "2025-01-02", "2025-01-02"]),
                "target_date": pd.to_datetime(["2025-01-03", "2025-01-03", "2025-01-04"]),
                "horizon": [2, 1, 2],
                "Mean_C": [10.0, 10.0, 8.0],
                "Min_C": [10.0, 10.0, 8.0],
                "Max_C": [10.0, 10.0, 8.0],
            }
        )
        worst = largest_ridge_errors(rows, np.zeros((3, 3)), top=2)
        for target in ("Mean_C", "Min_C", "Max_C"):
            dates = [row["target_date"] for row in worst if row["target"] == target]
            self.assertEqual(["2025-01-03", "2025-01-04"], dates)


if __name__ == "__main__":
    unittest.main()
