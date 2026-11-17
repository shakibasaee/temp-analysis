"""Offline checks for fixed-width GHCN-Daily coverage parsing."""

import unittest

from scripts.audit_ghcn_stations import parse_dly


def line(element, first, second=-9999, second_quality=" "):
    header = f"IRM00040821{2025:04d}{1:02d}{element}"
    fields = []
    for day in range(1, 32):
        value = first if day == 1 else second if day == 2 else -9999
        quality = second_quality if day == 2 else " "
        fields.append(f"{value:5d} {quality}S")
    return header + "".join(fields) + "\n"


class GhcnAuditTests(unittest.TestCase):
    def test_counts_only_quality_accepted_values(self):
        raw = (
            line("TAVG", 100, 110)
            + line("TMIN", 50, 60, second_quality="X")
            + line("TMAX", 150, 160)
        ).encode("ascii")
        result = parse_dly(raw, 2025, 2025)
        self.assertEqual({"TAVG": 2, "TMIN": 1, "TMAX": 2}, result["element_days"])
        self.assertEqual(1, result["all_three_days"])
        self.assertEqual(0, result["ordering_violations"])
        self.assertEqual("2025-01-01", result["latest_date"]["TMIN"])
        self.assertEqual({"TMIN": 1}, result["quality_rejected"])


if __name__ == "__main__":
    unittest.main()
