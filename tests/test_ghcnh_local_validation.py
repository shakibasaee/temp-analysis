"""Offline checks for quality-screened local-day station summaries."""

import io
import unittest

import pandas as pd

from scripts.evaluate_ghcnh_local import parse_local_station

STATION = "IRI0000OIGG"


def station_file(rows: list[tuple[str, str, str, str]]) -> bytes:
    output = io.StringIO()
    output.write("STATION|DATE|temperature|temperature_Quality_Code\n")
    for station, timestamp, temperature, quality in rows:
        output.write(f"{station}|{timestamp}|{temperature}|{quality}\n")
    return output.getvalue().encode()


def local_day_rows(day: str, hours: range = range(24)) -> list[tuple[str, str, str, str]]:
    local_start = pd.Timestamp(day, tz="Asia/Tehran")
    return [
        (
            STATION,
            (local_start + pd.Timedelta(hours=hour))
            .tz_convert("UTC")
            .strftime("%Y-%m-%dT%H:%M:%S"),
            str(hour),
            "1",
        )
        for hour in hours
    ]


class GhcnhLocalValidationTests(unittest.TestCase):
    def test_local_hour_aggregation_and_quality_filter(self):
        rows = local_day_rows("2025-01-03")
        rows.append((STATION, rows[0][1], "50", "2"))
        rows.append((STATION, rows[0][1], "2", "1"))
        rows.append((STATION, rows[0][1], "0", "1"))
        daily, coverage = parse_local_station(station_file(rows), STATION, 2025)
        self.assertEqual("2025-01-03", daily.loc[0, "target_date"].strftime("%Y-%m-%d"))
        self.assertEqual(11.5, daily.loc[0, "Mean_C"])
        self.assertEqual(0, daily.loc[0, "Min_C"])
        self.assertEqual(23, daily.loc[0, "Max_C"])
        self.assertEqual(26, coverage["quality_accepted_reports"])
        self.assertEqual(24, coverage["distinct_local_hour_bins"])

    def test_rejects_sparse_day_even_with_eighteen_hours(self):
        hours = range(18)
        rows = local_day_rows("2025-01-03", hours)
        rows += local_day_rows("2025-01-04")
        daily, _ = parse_local_station(station_file(rows), STATION, 2025)
        self.assertEqual(["2025-01-04"], daily["target_date"].dt.strftime("%Y-%m-%d").tolist())

    def test_excludes_incomplete_first_local_day(self):
        rows = local_day_rows("2025-01-01", range(4, 24))
        rows += local_day_rows("2025-01-03")
        daily, _ = parse_local_station(station_file(rows), STATION, 2025)
        self.assertEqual(["2025-01-03"], daily["target_date"].dt.strftime("%Y-%m-%d").tolist())

    def test_rejects_wrong_station(self):
        rows = local_day_rows("2025-01-03")
        rows[0] = ("OTHER", *rows[0][1:])
        with self.assertRaisesRegex(ValueError, "station ID"):
            parse_local_station(station_file(rows), STATION, 2025)


if __name__ == "__main__":
    unittest.main()
