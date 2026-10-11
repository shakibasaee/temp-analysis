"""Keep the existing Streamlit entry point runnable from the repository root."""

import unittest
from pathlib import Path


class DashboardSmokeTests(unittest.TestCase):
    def test_dashboard_renders_default_view(self):
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError:
            self.skipTest("Streamlit is not installed")
        app_path = Path(__file__).resolve().parents[1] / "scripts" / "app.py"
        app = AppTest.from_file(str(app_path), default_timeout=120).run()
        self.assertEqual([error.message for error in app.exception], [])
        self.assertEqual(app.title[0].value, "Weather Data Analysis")
        self.assertTrue(
            any("Selected model: persistence" in caption.value for caption in app.caption)
        )
        forecast = app.dataframe[0].value
        self.assertEqual(forecast["City"].tolist(), ["Bandar_Abbas"])
        self.assertEqual(str(forecast["Date"].iloc[0]), "2025-01-01")
        self.assertEqual(float(forecast["Predicted_Temperature_C"].iloc[0]), 21.8)
        self.assertIn("bundled observations are stale", app.warning[0].value)
        app.multiselect[0].set_value(["Rasht", "Yazd"]).run()
        self.assertEqual([error.message for error in app.exception], [])
        self.assertEqual(set(app.dataframe[0].value["City"]), {"Rasht", "Yazd"})
