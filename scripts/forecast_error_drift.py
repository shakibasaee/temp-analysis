"""Check ordered one-day forecast errors with River Page-Hinkley."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import river
from river import drift

from scripts.one_city_forecast_eval import prepare_city

plt.switch_backend("Agg")


SETTINGS = {
    "min_instances": 30,
    "delta": 0.005,
    "threshold": 50.0,
    "alpha": 0.9999,
    "mode": "both",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_aligned(
    eval_path: Path, metadata_path: Path, source_path: Path
) -> tuple[pd.DataFrame, dict]:
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if sha256(eval_path) != metadata["forecast_eval_sha256"]:
        raise ValueError("Evaluation CSV differs from its recorded SHA-256")
    if sha256(source_path) != metadata["dataset_sha256"]:
        raise ValueError("Source CSV differs from its recorded SHA-256")
    rows = pd.read_csv(eval_path)
    if list(rows.columns) != ["date", "actual", "predicted"] or rows.empty:
        raise ValueError("Expected a nonempty date,actual,predicted CSV")
    rows["date"] = pd.to_datetime(rows["date"], format="%Y-%m-%d", errors="raise")
    if rows["date"].duplicated().any() or not rows["date"].is_monotonic_increasing:
        raise ValueError("Evaluation dates must be unique and chronological")
    if not rows["date"].diff().dropna().eq(pd.Timedelta(days=1)).all():
        raise ValueError("Evaluation dates must be consecutive")
    if not np.isfinite(rows[["actual", "predicted"]].to_numpy(dtype=float)).all():
        raise ValueError("Evaluation temperatures must be finite")
    if (
        len(rows) != metadata["test_rows"]
        or [
            rows["date"].iloc[0].strftime("%Y-%m-%d"),
            rows["date"].iloc[-1].strftime("%Y-%m-%d"),
        ]
        != metadata["test_dates"]
    ):
        raise ValueError("Evaluation dates differ from the recorded holdout")

    city, _ = prepare_city(source_path, metadata["data_audit"]["city"])
    lookup = city.set_index("Date_Time")["Temperature_C"]
    actual = lookup.reindex(rows["date"]).to_numpy(dtype=float)
    previous = lookup.reindex(rows["date"] - pd.Timedelta(days=1)).to_numpy(dtype=float)
    if not np.isfinite(actual).all() or not np.isfinite(previous).all():
        raise ValueError("Actual or previous-day baseline is unavailable")
    if not np.allclose(actual, rows["actual"].to_numpy(dtype=float), rtol=0, atol=1e-9):
        raise ValueError("Evaluation actual values do not match source dates")
    rows["error"] = rows["actual"] - rows["predicted"]
    rows["baseline_error"] = rows["actual"] - previous
    return rows, metadata


def metrics(rows: pd.DataFrame) -> dict:
    return {
        "count": len(rows),
        "regression_mean_signed_error_c": float(rows["error"].mean()),
        "regression_mae_c": float(rows["error"].abs().mean()),
        "persistence_mean_signed_error_c": float(rows["baseline_error"].mean()),
        "persistence_mae_c": float(rows["baseline_error"].abs().mean()),
    }


def analyze(rows: pd.DataFrame, window_days: int = 14, settings: dict | None = None) -> dict:
    if window_days < 1:
        raise ValueError("window_days must be positive")
    settings = SETTINGS.copy() if settings is None else settings.copy()
    detector = drift.PageHinkley(**settings)
    alerts = []
    for index, row in enumerate(rows.itertuples(index=False)):
        detector.update(float(row.error))
        if detector.drift_detected:
            size = min(window_days, index, len(rows) - index - 1)
            before = rows.iloc[index - size : index]
            after = rows.iloc[index + 1 : index + 1 + size]
            alerts.append(
                {
                    "detected_date": row.date.strftime("%Y-%m-%d"),
                    "index": index,
                    "comparison_days_each_side": size,
                    "before_dates": [
                        before.iloc[0]["date"].strftime("%Y-%m-%d"),
                        before.iloc[-1]["date"].strftime("%Y-%m-%d"),
                    ]
                    if size
                    else None,
                    "after_dates": [
                        after.iloc[0]["date"].strftime("%Y-%m-%d"),
                        after.iloc[-1]["date"].strftime("%Y-%m-%d"),
                    ]
                    if size
                    else None,
                    "before": metrics(before) if size else None,
                    "after": metrics(after) if size else None,
                }
            )
    return {
        "river_version": river.__version__,
        "settings": settings,
        "window_days_requested": window_days,
        "holdout_dates": [
            rows["date"].iloc[0].strftime("%Y-%m-%d"),
            rows["date"].iloc[-1].strftime("%Y-%m-%d"),
        ],
        "overall": metrics(rows),
        "alerts": alerts,
        "interpretation": (
            "Alert date is detection time, not necessarily change onset. "
            "Alerts are exploratory, not proof of causal or meteorological drift."
        ),
    }


def save_plot(rows: pd.DataFrame, alerts: list[dict], path: Path, city: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(rows["date"], rows["error"], linewidth=1, color="#185a7d")
    ax.axhline(0, color="grey", linewidth=0.8)
    for alert in alerts:
        ax.axvline(
            pd.Timestamp(alert["detected_date"]), color="#b22222", linestyle="--", linewidth=1
        )
    ax.set(
        ylabel="Actual - predicted (C)",
        xlabel="Target date",
        title=f"{city}: one-day regression signed errors",
    )
    fig.autofmt_xdate()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval", type=Path, default=Path("forecast_eval.csv"))
    parser.add_argument("--metadata", type=Path, default=Path("forecast_eval.metadata.json"))
    parser.add_argument("--source-data", type=Path, default=Path("data/new_weather_data.csv"))
    parser.add_argument("--out", type=Path, default=Path("docs/FORECAST_DRIFT.json"))
    parser.add_argument("--plot", type=Path, default=Path("docs/forecast_drift.png"))
    parser.add_argument("--window-days", type=int, default=14)
    args = parser.parse_args()
    rows, metadata = load_aligned(args.eval, args.metadata, args.source_data)
    result = analyze(rows, args.window_days)
    result.update(
        {
            "city": metadata["data_audit"]["city"],
            "source_dataset_sha256": metadata["dataset_sha256"],
            "evaluation_csv_sha256": metadata["forecast_eval_sha256"],
            "unit_caveat": metadata["data_audit"]["unit"],
        }
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    save_plot(rows, result["alerts"], args.plot, result["city"])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
