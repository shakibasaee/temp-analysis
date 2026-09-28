"""Contract tests for the chronological one-day forecasting workflow."""

import json
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import pandas as pd

from forecasting.cli import main
from forecasting.config import ForecastConfig
from forecasting.data import load_daily_data, validate_daily_data
from forecasting.experiment import (
    benchmark,
    load_artifact,
    predict_next_day,
    save_artifact,
    split_examples,
    train_final,
)
from forecasting.features import FEATURES, make_examples


def sample_data(days: int = 120) -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", periods=days, freq="D")
    return pd.DataFrame(
        [
            {
                "Date_Time": day,
                "City": city,
                "Temperature_C": offset + 8 * np.sin(i / 15) + i * 0.01,
            }
            for city, offset in (("North", 5.0), ("South", 20.0))
            for i, day in enumerate(dates)
        ]
    )


class ForecastingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = sample_data()
        self.config = ForecastConfig(
            train_end="2023-03-01", validation_end="2023-04-01"
        )

    def test_load_and_validate_sorts_daily_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "weather.csv"
            self.data.sample(frac=1, random_state=3).to_csv(path, index=False)
            loaded = load_daily_data(path)
        self.assertEqual(len(loaded), 240)
        self.assertEqual(loaded.iloc[0]["City"], "North")
        self.assertEqual(loaded.iloc[0]["Date_Time"], pd.Timestamp("2023-01-01"))

    def test_invalid_dates_duplicates_gaps_targets_and_cities(self):
        cases = [
            (self.data.drop(columns="City"), "Missing required"),
            (pd.concat([self.data, self.data.iloc[[0]]]), "Duplicate"),
            (self.data.drop(index=1), "contiguous"),
            (self.data.assign(Temperature_C=np.inf), "finite"),
            (self.data.assign(Temperature_C=100), "plausible"),
            (self.data.assign(City=""), "nonempty"),
            (self.data.assign(Date_Time="bad"), "midnight"),
        ]
        for data, error in cases:
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                validate_daily_data(data)

    def test_features_use_only_observations_at_or_before_issue_date(self):
        original = make_examples(self.data)
        changed = self.data.copy()
        changed.loc[
            (changed.City == "North") & (changed.Date_Time == "2023-03-01"),
            "Temperature_C",
        ] += 20
        altered = make_examples(changed)
        earlier = original.issue_date < pd.Timestamp("2023-03-01")
        pd.testing.assert_frame_equal(
            original.loc[earlier, list(FEATURES)], altered.loc[earlier, list(FEATURES)]
        )
        # The changed day is a label for the previous day's forecast, never its predictor.
        previous = original[
            (original.City == "North") & (original.issue_date == "2023-02-28")
        ].iloc[0]
        previous_changed = altered[
            (altered.City == "North") & (altered.issue_date == "2023-02-28")
        ].iloc[0]
        self.assertEqual(previous_changed.target - previous.target, 20)
        self.assertEqual(previous_changed.temp_today, previous.temp_today)
        self.assertEqual(original["target"].isna().sum(), 2)

    def test_chronological_split_uses_target_dates(self):
        train, validation, test = split_examples(make_examples(self.data), self.config)
        self.assertEqual(train.target_date.max(), pd.Timestamp("2023-03-01"))
        self.assertEqual(validation.target_date.min(), pd.Timestamp("2023-03-02"))
        self.assertEqual(test.target_date.min(), pd.Timestamp("2023-04-02"))
        self.assertEqual(
            train.iloc[-1].issue_date + pd.Timedelta(days=1), train.iloc[-1].target_date
        )

    def test_benchmark_train_save_load_and_prediction(self):
        report = benchmark(validate_daily_data(self.data), self.config)
        self.assertEqual(
            set(report["models"]),
            {
                "persistence",
                "seasonal_naive_7",
                "calendar_linear",
                "ridge_lags",
                "extra_trees_lags",
            },
        )
        best = min(
            report["models"],
            key=lambda name: report["models"][name]["validation"]["mae"],
        )
        gain = (
            report["models"]["persistence"]["validation"]["mae"]
            - report["models"][best]["validation"]["mae"]
        ) / report["models"]["persistence"]["validation"]["mae"]
        self.assertEqual(
            report["selected_model"],
            best if gain >= self.config.minimum_relative_mae_gain else "persistence",
        )
        artifact = train_final(
            validate_daily_data(self.data), self.config, report["selected_model"]
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.joblib"
            save_artifact(artifact, path)
            loaded = load_artifact(path)
            predictions = predict_next_day(loaded, self.data)
        self.assertEqual(
            list(predictions.columns), ["Date", "City", "Predicted_Temperature_C"]
        )
        self.assertEqual(len(predictions), 2)
        self.assertTrue(np.isfinite(predictions.Predicted_Temperature_C).all())
        self.assertEqual(predictions.Date.nunique(), 1)
        self.assertEqual(predictions.Date.iloc[0], pd.Timestamp("2023-05-01").date())
        with self.assertRaisesRegex(ValueError, "predates"):
            predict_next_day(
                loaded, self.data.iloc[:-1].loc[lambda d: d.Date_Time < "2023-04-30"]
            )
        extra = self.data.loc[self.data.City == "North"].assign(City="East")
        with self.assertRaisesRegex(ValueError, "No trained model"):
            predict_next_day(loaded, pd.concat([self.data, extra]))

    def test_cli_benchmark_and_predict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data_path = root / "daily.csv"
            config_path = root / "forecast.json"
            model_path = root / "model.joblib"
            report_path = root / "report.json"
            self.data.to_csv(data_path, index=False)
            config_path.write_text(json.dumps(self.config.to_dict()), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(
                        [
                            "train",
                            "--data",
                            str(data_path),
                            "--config",
                            str(config_path),
                            "--model-out",
                            str(model_path),
                            "--report-out",
                            str(report_path),
                        ]
                    ),
                    0,
                )
            self.assertTrue(model_path.exists())
            self.assertEqual(
                json.loads(report_path.read_text(encoding="utf-8"))["data"][
                    "observations"
                ],
                240,
            )
            with redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(
                        [
                            "predict",
                            "--data",
                            str(data_path),
                            "--model",
                            str(model_path),
                        ]
                    ),
                    0,
                )


if __name__ == "__main__":
    unittest.main()
