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
