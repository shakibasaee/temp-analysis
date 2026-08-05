import json
import unittest

from scripts.evaluation.metrics import MetricsCalculator


class MetricsCalculatorTests(unittest.TestCase):
    def test_known_metric_values(self):
        calculator = MetricsCalculator(n_bootstrap=20)

        metrics = calculator.calculate([10, 20, 30], [12, 18, 33])

        self.assertAlmostEqual(metrics["mae"], 7 / 3)
        self.assertAlmostEqual(metrics["rmse"], (17 / 3) ** 0.5)
        self.assertAlmostEqual(metrics["mape"], (0.2 + 0.1 + 0.1) / 3 * 100)

    def test_mape_excludes_zero_targets_and_reports_count(self):
        calculator = MetricsCalculator(n_bootstrap=20)

        report = calculator.generate_report([0, 10], [5, 8])

        self.assertAlmostEqual(report["metrics"]["mape"]["value"], 20.0)
        self.assertEqual(report["metadata"]["mape_excluded_zero_targets"], 1)

    def test_all_zero_targets_make_mape_undefined(self):
        calculator = MetricsCalculator()

        with self.assertRaisesRegex(ValueError, "MAPE is undefined"):
            calculator.calculate([0, 0], [1, 2])

    def test_confidence_intervals_are_reproducible(self):
        first = MetricsCalculator(n_bootstrap=100, random_seed=7)
        second = MetricsCalculator(n_bootstrap=100, random_seed=7)
        actual = [10, 12, 14, 16, 18]
        predicted = [11, 11, 15, 14, 19]

        first_intervals = first.confidence_intervals(actual, predicted)
        second_intervals = second.confidence_intervals(actual, predicted)

        self.assertEqual(first_intervals, second_intervals)
        self.assertLessEqual(
            first_intervals["mae"]["lower"],
            first_intervals["mae"]["upper"],
        )

    def test_report_is_json_serializable(self):
        calculator = MetricsCalculator(n_bootstrap=20)

        payload = calculator.generate_json_report([1, 2, 3], [1, 2, 4])
        decoded = json.loads(payload)

        self.assertEqual(decoded["metadata"]["sample_size"], 3)
        self.assertIn("rmse", decoded["metrics"])

    def test_rejects_non_finite_values(self):
        calculator = MetricsCalculator()

        with self.assertRaisesRegex(ValueError, "finite"):
            calculator.calculate([1, float("nan")], [1, 2])


if __name__ == "__main__":
    unittest.main()
