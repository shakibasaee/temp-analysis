"""Offline checks for the read-only provider coverage probe."""

import io
import json
import unittest
from datetime import date
from unittest.mock import patch

from scripts.audit_open_meteo import CITY_POINTS, VARIABLES, audit


def response(missing=False):
    items = []
    for _ in CITY_POINTS:
        daily = {
            "time": ["2023-01-01", "2023-01-02"],
            "temperature_2m_mean": [10, None if missing else 11],
            "temperature_2m_min": [5, 6],
            "temperature_2m_max": [15, 16],
        }
        items.append(
            {
                "timezone": "Asia/Tehran",
                "daily": daily,
                "daily_units": {name: "°C" for name in VARIABLES},
            }
        )
    return io.BytesIO(json.dumps(items).encode("utf-8"))


class SourceAuditTests(unittest.TestCase):
    def test_counts_and_request_contract(self):
        with patch(
            "scripts.audit_open_meteo.urlopen", return_value=response(missing=True)
        ) as fetch:
            report = audit(date(2023, 1, 1), date(2023, 1, 2))
        self.assertEqual(5, len(report["cities"]))
        self.assertEqual(1, report["cities"][0]["missing"]["temperature_2m_mean"])
        self.assertEqual(0, report["cities"][0]["inconsistent_min_mean_max"])
        url = fetch.call_args.args[0]
        self.assertIn("models=era5", url)
        self.assertIn("timezone=Asia%2FTehran", url)

    def test_rejects_reversed_dates(self):
        with self.assertRaises(ValueError):
            audit(date(2023, 1, 2), date(2023, 1, 1))


if __name__ == "__main__":
    unittest.main()
