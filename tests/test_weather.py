"""Contract checks for the experimental four-target weather benchmark."""

import unittest
from datetime import date

import numpy as np
import pandas as pd

from forecasting.config import ForecastConfig
from forecasting.weather import (
    TARGETS,
    benchmark_weather,
    make_weather_examples,
    predict_weather_baselines,
    validate_weather_data,
)


def sample_weather(days: int = 160) -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", periods=days, freq="D")
    return pd.DataFrame(
        [
            {
                "Date_Time": day,
                "City": city,
                "Temperature_C": offset + 5 * np.sin(i / 9),
                "Precipitation_mm": 4.0 if i % (6 + shift) == 0 else 0.0,
                "Wind_Speed_kmh": 9 + shift + 2 * np.sin(i / 5),
                "Pressure_hPa": 1010 + shift + 3 * np.cos(i / 7),
            }
            for city, offset, shift in (("North", 8.0, 0), ("South", 22.0, 1))
            for i, day in enumerate(dates)
        ]
    )


class WeatherBenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = sample_weather()
        self.config = ForecastConfig(
            train_end="2023-03-01", validation_end="2023-04-01"
        )

    def test_weather_contract_rejects_bad_values_but_allows_missing_measurements(self):
        data = self.data.copy()
        data.loc[10, "Precipitation_mm"] = np.nan
        data.loc[11, "Pressure_hPa"] = np.nan
        validated = validate_weather_data(data)
        self.assertEqual(int(validated.Precipitation_mm.isna().sum()), 1)
        self.assertEqual(int(validated.Pressure_hPa.isna().sum()), 1)
        with self.assertRaisesRegex(ValueError, "Missing weather columns"):
            validate_weather_data(data.drop(columns="Wind_Speed_kmh"))
        with self.assertRaisesRegex(ValueError, "cannot be negative"):
            validate_weather_data(data.assign(Precipitation_mm=-1))

    def test_future_measurement_changes_label_not_earlier_features(self):
        original = make_weather_examples(self.data)
        changed = self.data.copy()
        changed.loc[
            (changed.City == "North") & (changed.Date_Time == "2023-03-01"),
            ["Wind_Speed_kmh", "Pressure_hPa", "Precipitation_mm"],
        ] = [25.0, 990.0, 7.0]
        altered = make_weather_examples(changed)
        earlier = original.issue_date < pd.Timestamp("2023-03-01")
        feature_columns = [
            "temp_today",
            "wind_today",
            "wind_mean_7",
            "pressure_today",
            "pressure_mean_7",
            "wet_today",
            "wet_rate_30",
        ]
        pd.testing.assert_frame_equal(
            original.loc[earlier, feature_columns],
            altered.loc[earlier, feature_columns],
        )
        previous = (original.City == "North") & (
            original.issue_date == pd.Timestamp("2023-02-28")
        )
        self.assertNotEqual(
            original.loc[previous, "target_precipitation"].item(),
            altered.loc[previous, "target_precipitation"].item(),
        )

    def test_benchmark_has_time_split_baselines_and_city_results(self):
        report = benchmark_weather(self.data, self.config)
        self.assertEqual(set(report["targets"]), set(TARGETS))
        for task, result in report["targets"].items():
            metric = result["primary_metric"]
            self.assertGreater(result["train_rows"], 0)
            self.assertEqual(set(result["test"]["by_city"]), {"North", "South"})
            for candidate in ("baseline", "model"):
                self.assertTrue(np.isfinite(result["test"][candidate][metric]))
            if task == "precipitation_probability":
                self.assertLessEqual(result["test"]["model"]["brier"], 1)

    def test_stale_baselines_require_explicit_historical_replay(self):
        with self.assertRaisesRegex(ValueError, "stale"):
            predict_weather_baselines(self.data, today=date(2026, 10, 13))
        output = predict_weather_baselines(self.data, allow_historical=True)
        self.assertEqual(len(output), 2)
        self.assertEqual(output.Date.nunique(), 1)
        self.assertEqual(
            len(predict_weather_baselines(self.data, today=output.Date.iloc[0])), 2
        )
        self.assertTrue(output.Precipitation_Probability_Baseline.between(0, 1).all())


if __name__ == "__main__":
    unittest.main()
