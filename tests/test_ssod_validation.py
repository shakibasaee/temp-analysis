"""Offline checks for SSOD coverage and UTC station alignment."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_ssod import summarize
from scripts.evaluate_ssod import evaluate, parse_station, validate_station_snapshots


def rows():
    return [
        {
            "STATION": "IRI0000OIGG",
            "DATE": "2025-01-01",
            "mean_temperature": "8.0",
            "min_temperature": "4.0",
            "max_temperature": "12.0",
        },
        {
            "STATION": "IRI0000OIGG",
            "DATE": "2025-01-02",
            "mean_temperature": "-9999.9",
            "min_temperature": "2.0",
            "max_temperature": "10.0",
        },
        {
            "STATION": "IRI0000OIGG",
            "DATE": "2025-01-03",
            "mean_temperature": "9.0",
            "min_temperature": "12.0",
            "max_temperature": "10.0",
        },
    ]


class SsodValidationTests(unittest.TestCase):
    def test_coverage_and_valid_three_target_days(self):
        raw = json.dumps(rows()).encode()
        audit = summarize(raw, "IRI0000OIGG", 2025)
        self.assertEqual(3, audit["element_days"]["min_temperature"])
        self.assertEqual(2, audit["element_days"]["mean_temperature"])
        self.assertEqual(2, audit["all_three_days"])
        self.assertEqual(1, audit["ordering_violations"])
        accepted = parse_station(raw, "IRI0000OIGG", 2025)
        self.assertEqual(["2025-01-01"], accepted["target_date"].dt.strftime("%Y-%m-%d").tolist())

    def test_rejects_duplicate_station_day(self):
        raw = json.dumps(rows()[:1] * 2).encode()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            parse_station(raw, "IRI0000OIGG", 2025)

    def test_rejects_local_day_dataset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "era5.csv"
            path.write_text("Date,City,Mean_C,Min_C,Max_C\n", encoding="utf-8")
            path.with_suffix(".metadata.json").write_text(
                json.dumps(
                    {
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "model": "era5",
                        "timezone": "Asia/Tehran",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "GMT-day"):
                evaluate(path)

    def test_rejects_changed_station_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.json"
            path.write_text(
                json.dumps(
                    {
                        "year": 2025,
                        "stations": [
                            {"city": "Rasht", "station_id": "IRI0000OIGG", "response_sha256": "old"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "changed"):
                validate_station_snapshots(
                    [{"city": "Rasht", "station_id": "IRI0000OIGG", "response_sha256": "new"}],
                    path,
                )


if __name__ == "__main__":
    unittest.main()
