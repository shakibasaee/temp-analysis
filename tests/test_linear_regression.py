import unittest

import numpy as np
import pandas as pd

from scripts.model_config import LinearRegressionConfig
from scripts.models.linear_regression import LinearRegressionModel
from scripts.processing_data.regression_runner import reg_runner


def make_weather_data() -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", periods=40, freq="D")
    rows = []
    for city, city_effect in [("Rasht", 3.0), ("Yazd", 8.0)]:
        for date in dates:
            rows.append(
                {
                    "Date_Time": date,
                    "City": city,
                    "Temperature_C": 10 + city_effect + 0.08 * date.dayofyear,
                }
            )
    return pd.DataFrame(rows)


class LinearRegressionModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.weather_data = make_weather_data()

    def test_feature_engineering_is_temporal_and_does_not_mutate_input(self):
        original_columns = self.weather_data.columns.tolist()
        model = LinearRegressionModel()

        features = model.engineer_features(self.weather_data)

        self.assertEqual(self.weather_data.columns.tolist(), original_columns)
        self.assertTrue(
            {"day_of_year", "day_of_year_sin", "month_cos", "City"}.issubset(
                features.columns
            )
        )

    def test_time_split_keeps_dates_separate(self):
        model = LinearRegressionModel(LinearRegressionConfig(test_size=0.25))

        train, test = model.split_data(self.weather_data)

        self.assertLess(train["Date_Time"].max(), test["Date_Time"].min())
        self.assertTrue(
            set(train["Date_Time"]).isdisjoint(set(test["Date_Time"]))
        )

    def test_model_evaluates_and_supports_unseen_city(self):
        model = LinearRegressionModel()
        metrics = model.fit_evaluate(self.weather_data)

        prediction = model.predict(
            pd.DataFrame({"Date_Time": ["2024-01-01"], "City": ["New City"]})
        )

        self.assertEqual(set(metrics), {"mae", "rmse", "mape", "r2"})
        self.assertIn("confidence_interval", model.metrics_report_["metrics"]["mae"])
        self.assertTrue(np.isfinite(prediction).all())
        self.assertTrue(any("City_" in name for name in model.feature_names_))

    def test_runner_reuses_a_fitted_model(self):
        model = LinearRegressionModel().fit(self.weather_data)

        result = reg_runner(model, self.weather_data, "Rasht", "2024-02-01")

        self.assertEqual(
            result.columns.tolist(), ["Date", "City", "Predicted_Temprature"]
        )
        self.assertEqual(result.loc[0, "City"], "Rasht")
        self.assertTrue(np.isfinite(result.loc[0, "Predicted_Temprature"]))

    def test_specific_city_configuration_filters_training_data(self):
        config = LinearRegressionConfig(
            feature_selection_mode="specific", selected_cities=["Rasht"]
        )
        model = LinearRegressionModel(config).fit(self.weather_data)

        self.assertEqual(model.training_rows_, 40)

    def test_invalid_configuration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "test_size"):
            LinearRegressionModel(LinearRegressionConfig(test_size=1.0))


if __name__ == "__main__":
    unittest.main()
