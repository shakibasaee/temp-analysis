"""Validate ERA5 ingestion at the source boundary without network calls."""

import json
import hashlib
import tempfile
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd

from forecasting.open_meteo import archive_url, daily_from_response, save_snapshot
from forecasting.weather import validate_weather_data


def response() -> dict:
    hours = pd.date_range("2025-01-01", periods=48, freq="h")
    return {
        "timezone": "GMT",
        "utc_offset_seconds": 0,
        "hourly_units": {
            "temperature_2m": "°C",
            "wind_speed_10m": "km/h",
            "pressure_msl": "hPa",
        },
        "daily_units": {"precipitation_sum": "mm"},
        "daily": {
            "time": ["2025-01-01", "2025-01-02"],
            "precipitation_sum": [12.0, 0.0],
        },
        "hourly": {
            "time": hours.strftime("%Y-%m-%dT%H:%M").tolist(),
            "temperature_2m": [10.0] * 24 + [12.0] * 24,
            "wind_speed_10m": [8.0] * 24 + [9.0] * 24,
            "pressure_msl": [1010.0] * 24 + [1012.0] * 24,
        },
    }


class Era5IngestionTests(unittest.TestCase):
    def test_committed_snapshot_manifest_and_report_agree(self):
        root = Path(__file__).resolve().parents[1]
        csv = root / "data/era5_daily_2022_2025.csv"
        manifest = json.loads(
            (root / "data/era5_daily_2022_2025.manifest.json").read_text(
                encoding="utf-8"
            )
        )
        report = json.loads(
            (root / "reports/era5-weather-benchmark.json").read_text(encoding="utf-8")
        )
        digest = hashlib.sha256(csv.read_bytes()).hexdigest()
        self.assertEqual(digest, manifest["csv_sha256"])
        self.assertEqual(digest, report["data"]["source_sha256"])
        data = validate_weather_data(pd.read_csv(csv))
        self.assertEqual(len(data), manifest["rows"])
        self.assertEqual(len(manifest["requests"]), 20)
        self.assertEqual(set(data.City), set(report["data"]["cities"]))

    def test_request_pins_model_units_timezone_and_city_coordinates(self):
        query = parse_qs(
            urlparse(archive_url("Rasht", date(2025, 1, 1), date(2025, 1, 2))).query
        )
        self.assertEqual(query["models"], ["era5"])
        self.assertEqual(query["timezone"], ["UTC"])
        self.assertEqual(query["latitude"], ["37.27611"])
        self.assertEqual(
            query["hourly"],
            ["temperature_2m,wind_speed_10m,pressure_msl"],
        )
        self.assertEqual(query["daily"], ["precipitation_sum"])

    def test_utc_daily_aggregation_and_gap_rejection(self):
        payload = response()
        daily = daily_from_response(
            payload, "Rasht", date(2025, 1, 1), date(2025, 1, 2)
        )
        self.assertEqual(daily.Temperature_C.tolist(), [10.0, 12.0])
        self.assertEqual(daily.Precipitation_mm.tolist(), [12.0, 0.0])
        self.assertEqual(daily.Pressure_hPa.tolist(), [1010.0, 1012.0])
        payload["hourly"]["time"].pop()
        with self.assertRaisesRegex(ValueError, "Missing, duplicated"):
            daily_from_response(payload, "Rasht", date(2025, 1, 1), date(2025, 1, 2))

    def test_manifest_checksum_matches_saved_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            csv = Path(directory) / "weather.csv"
            manifest_path = Path(directory) / "weather.json"
            manifest = {"source": "test"}
            save_snapshot(
                daily_from_response(
                    response(), "Rasht", date(2025, 1, 1), date(2025, 1, 2)
                ),
                manifest,
                csv,
                manifest_path,
            )
            saved = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["csv_sha256"], manifest["csv_sha256"])
            self.assertNotIn(b"\r\n", csv.read_bytes())
            self.assertIn("2025-01-01", csv.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
