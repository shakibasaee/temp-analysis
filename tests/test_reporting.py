import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from scripts.models.linear_regression import LinearRegressionModel
from scripts.reporting.report_generator import ModelReportGenerator
from tests.test_linear_regression import make_weather_data


class ModelReportGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = make_weather_data()
        self.model = LinearRegressionModel()
        self.model.fit_evaluate(self.dataset)

    def test_report_contains_required_sections(self):
        report = ModelReportGenerator().build_report(self.model, self.dataset)

        self.assertIn("configuration", report["model"])
        self.assertEqual(report["dataset_summary"]["rows"], 80)
        self.assertIn("train", report["metrics"])
        self.assertIn("test", report["metrics"])
        self.assertEqual(
            report["feature_importance"]["method"],
            "linear_regression_coefficients",
        )

    def test_json_yaml_and_markdown_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            generator = ModelReportGenerator(directory)
            report = generator.build_report(self.model, self.dataset)

            json_path = generator.save_json(report)
            yaml_path = generator.save_yaml(report)
            markdown_path = generator.save_markdown(report)

            self.assertTrue(json_path.exists())
            self.assertTrue(yaml_path.exists())
            self.assertTrue(markdown_path.exists())
            decoded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(decoded["dataset_summary"]["city_count"], 2)

    @unittest.skipUnless(
        importlib.util.find_spec("reportlab"), "ReportLab is not installed"
    )
    def test_pdf_output(self):
        with tempfile.TemporaryDirectory() as directory:
            generator = ModelReportGenerator(directory)
            report = generator.build_report(self.model, self.dataset)

            pdf_path = generator.save_pdf(report)

            self.assertTrue(pdf_path.exists())
            self.assertGreater(Path(pdf_path).stat().st_size, 1_000)


if __name__ == "__main__":
    unittest.main()
