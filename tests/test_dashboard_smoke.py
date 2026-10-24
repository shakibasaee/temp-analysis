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
        self.assertEqual(
            app.title[0].value, "Weather forecasting: historical evaluation"
        )
        self.assertIn("Historical test: 2025-01-01", app.caption[0].value)
        self.assertEqual(len(app.dataframe[0].value), 5)
        self.assertIn(
            "Daily mean temperature (°C)", set(app.dataframe[0].value["Variable"])
        )
        self.assertEqual(len(app.dataframe[1].value), 25)
        self.assertEqual(len(app.dataframe[2].value), 20)
        self.assertTrue(
            any("Legacy temperature exploration" in h.value for h in app.header)
        )
        self.assertTrue(
            any("Selected model: persistence" in c.value for c in app.caption)
        )
        forecast = app.dataframe[3].value
        self.assertEqual(forecast["City"].tolist(), ["Bandar_Abbas"])
        self.assertEqual(str(forecast["Date"].iloc[0]), "2025-01-01")
        self.assertEqual(float(forecast["Predicted_Temperature_C"].iloc[0]), 21.8)
        self.assertIn("bundled observations are stale", app.warning[0].value)
        app.multiselect[0].set_value(["Rasht", "Yazd"]).run()
        self.assertEqual([error.message for error in app.exception], [])
        self.assertEqual(set(app.dataframe[3].value["City"]), {"Rasht", "Yazd"})
