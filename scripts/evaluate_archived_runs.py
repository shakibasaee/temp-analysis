"""Reproduce the issue-time archived forecast benchmark."""

from pathlib import Path

from forecasting.issue_time import evaluate, load_pairs, write_report

ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    forecast = ROOT / "data" / "archived_ifs_weekly.csv"
    reference = ROOT / "data" / "era5_daily_2022_2025.csv"
    report = evaluate(load_pairs(forecast, reference))
    write_report(
        report, ROOT / "reports" / "archived-ifs-2025.json", forecast, reference
    )
    for variable, scores in report["results"].items():
        print(
            variable,
            scores["metric"],
            "raw",
            round(scores["raw_ifs"], 4),
            "candidate",
            round(scores["candidate"], 4),
        )
