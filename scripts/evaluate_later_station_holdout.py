"""Test the frozen Ridge policy on later local-day NOAA station observations."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from forecasting.multi_horizon import (
    LAG_DAYS,
    TARGETS,
    fit_ridge,
    load_dataset,
    make_examples,
    predict_all,
    score,
    score_by_city_season,
)
from scripts.audit_ssod import STATIONS
from scripts.evaluate_ghcnh_local import audit, load_stations

BASELINES = ("persistence", "seasonal_weekday")
TEST_START = pd.Timestamp("2026-01-01")
TEST_END = pd.Timestamp("2026-10-31")
FIRST_ISSUE = pd.Timestamp("2026-01-08")


def verified_data(path: Path) -> tuple[pd.DataFrame, dict]:
    raw = path.read_bytes()
    metadata = json.loads(path.with_suffix(".metadata.json").read_text(encoding="utf-8"))
    if metadata.get("sha256") != hashlib.sha256(raw).hexdigest():
        raise ValueError("ERA5 source does not match its SHA-256 manifest")
    if metadata.get("model") != "era5" or metadata.get("timezone") != "Asia/Tehran":
        raise ValueError("Expected local-day ERA5 data")
    data = load_dataset(path)
    if len(data) != metadata.get("rows"):
        raise ValueError("ERA5 row count differs from manifest")
    if data["Date"].min().date().isoformat() != metadata.get("start") or (
        data["Date"].max().date().isoformat() != metadata.get("end")
    ):
        raise ValueError("ERA5 date range differs from manifest")
    return data, metadata


def decision(matched: pd.DataFrame, predictions: dict[str, np.ndarray]) -> dict:
    if set(predictions) != {*BASELINES, "ridge"} or any(
        values.shape != (len(matched), len(TARGETS)) or not np.isfinite(values).all()
        for values in predictions.values()
    ):
        raise ValueError("Model predictions must be finite and aligned with matched targets")
    unique_days = matched.groupby("City")["target_date"].nunique().to_dict()
    counts = {city: int(unique_days.get(city, 0)) for city in STATIONS}
    missing = sorted(city for city, days in counts.items() if days < 100)
    by_target = []
    by_city_target = []
    for target_index, target in enumerate(TARGETS):
        actual = matched[target].to_numpy()
        errors = {
            model: np.abs(actual - values[:, target_index]) for model, values in predictions.items()
        }
        best_baseline_mae = min(float(errors[model].mean()) for model in BASELINES)
        best_baseline_coverage = max(
            float(100 * (errors[model] <= 2).mean()) for model in BASELINES
        )
        ridge_mae = float(errors["ridge"].mean())
        ridge_coverage = float(100 * (errors["ridge"] <= 2).mean())
        improvement = 100 * (best_baseline_mae - ridge_mae) / best_baseline_mae
        coverage_gain = ridge_coverage - best_baseline_coverage
        by_target.append(
            {
                "target": target,
                "best_baseline_mae_c": round(best_baseline_mae, 4),
                "ridge_mae_improvement_pct": round(improvement, 2),
                "best_baseline_within_2c_pct": round(best_baseline_coverage, 2),
                "ridge_within_2c_gain_points": round(coverage_gain, 2),
                "mae_gate_pass": improvement >= 10,
                "within_2c_gate_pass": coverage_gain >= 5,
            }
        )
        for city, indices in matched.groupby("City", sort=True).indices.items():
            actual = matched.iloc[indices][target].to_numpy()
            errors = {
                model: float(np.abs(actual - predictions[model][indices, target_index]).mean())
                for model in (*BASELINES, "ridge")
            }
            best = min(errors[model] for model in BASELINES)
            excess = errors["ridge"] - best
            by_city_target.append(
                {
                    "city": city,
                    "target": target,
                    "n_forecasts": len(indices),
                    "unique_target_days": counts[city],
                    "best_baseline_mae_c": round(best, 4),
                    "ridge_mae_c": round(errors["ridge"], 4),
                    "ridge_excess_mae_c": round(excess, 4),
                    "city_gate_pass": None if counts[city] < 100 else excess <= 0.5,
                }
            )
    all_pass = all(
        row["mae_gate_pass"] and row["within_2c_gate_pass"] for row in by_target
    ) and all(row["city_gate_pass"] for row in by_city_target)
    return {
        "policy": "docs/MODEL_ACCEPTANCE_POLICY_FA.md",
        "unique_station_target_days_by_city": counts,
        "cities_below_100_unique_days": missing,
        "by_target": by_target,
        "by_city_target": by_city_target,
        "status": "indeterminate" if missing else "pass" if all_pass else "fail",
    }


def failure_diagnostics(matched: pd.DataFrame, predictions: dict[str, np.ndarray]) -> dict:
    """Describe physical ordering and horizon failures without selecting a model."""
    actual = matched[list(TARGETS)].to_numpy()
    buckets = ((1, 7), (8, 14), (15, 30))
    result = []
    for model, values in predictions.items():
        if values.shape != actual.shape or not np.isfinite(values).all():
            raise ValueError("Predictions must be finite and aligned")
        violations = (values[:, 1] > values[:, 0]) | (values[:, 0] > values[:, 2])
        by_horizon = []
        for lower, upper in buckets:
            selected = matched["horizon"].between(lower, upper).to_numpy()
            if not selected.any():
                continue
            errors = np.abs(actual[selected] - values[selected])
            by_horizon.append(
                {
                    "horizon_days": [lower, upper],
                    "n_forecasts": int(selected.sum()),
                    "unique_city_target_days": int(
                        matched.loc[selected, ["City", "target_date"]].drop_duplicates().shape[0]
                    ),
                    "mae_c": {
                        target: round(float(errors[:, index].mean()), 4)
                        for index, target in enumerate(TARGETS)
                    },
                }
            )
        result.append(
            {
                "model": model,
                "ordering_violations": int(violations.sum()),
                "ordering_violation_pct": round(float(100 * violations.mean()), 2),
                "by_horizon": by_horizon,
            }
        )
    return {"models": result, "note": "Diagnostic only; no threshold or model selection"}


def evaluate(base_path: Path, extension_path: Path, station_dir: Path) -> tuple[dict, dict]:
    base, base_meta = verified_data(base_path)
    extension, extension_meta = verified_data(extension_path)
    if base["Date"].max() != pd.Timestamp("2025-12-31") or (
        extension["Date"].min() != pd.Timestamp("2026-01-01")
        or extension["Date"].max() != TEST_END
        or set(base["City"]) != set(extension["City"])
    ):
        raise ValueError("Unexpected base/extension boundary or city coverage")
    coordinates = (
        "city",
        "requested_latitude",
        "requested_longitude",
        "grid_latitude",
        "grid_longitude",
    )
    base_points = sorted(
        tuple(city[key] for key in coordinates) for city in base_meta["city_coverage"]
    )
    extension_points = sorted(
        tuple(city[key] for key in coordinates) for city in extension_meta["city_coverage"]
    )
    if base_points != extension_points:
        raise ValueError("ERA5 city/grid points changed between snapshots")
    data = load_dataset_from_frames(base, extension)
    examples = make_examples(data)
    train = examples[examples["target_date"] < TEST_START]
    test = examples[
        examples["target_date"].between(TEST_START, TEST_END)
        & examples["issue_date"].ge(FIRST_ISSUE)
    ].copy()
    if train.empty or test.empty or train["target_date"].max() > test["available_through"].min():
        raise ValueError("Training labels are unavailable at the first test issue")
    model = fit_ridge(train)
    test = test.reset_index(drop=True)
    predictions = predict_all(test, model)
    test["prediction_row"] = np.arange(len(test))
    observations, station_sources = load_stations(2026, station_dir)
    station_audit = audit(2026, station_dir)
    expected = {(s["city"], s["station_id"]): s["response_sha256"] for s in station_sources}
    audited = {
        (s["city"], s["station_id"]): s["response_sha256"] for s in station_audit["stations"]
    }
    if expected != audited:
        raise ValueError("Station files changed between audit and evaluation")
    matched = test.merge(
        observations,
        on=["City", "target_date"],
        how="inner",
        validate="many_to_one",
        suffixes=("_era5", ""),
    )
    if matched.empty:
        raise ValueError("No 2026 station observations match the test forecasts")
    indices = matched["prediction_row"].to_numpy(dtype=int)
    paired = {model: values[indices] for model, values in predictions.items()}
    overall, detail = score(matched, paired)
    gate = decision(matched, paired)
    report = {
        "report_schema_version": 1,
        "created_utc": datetime.now(UTC).isoformat(),
        "source": "Open-Meteo ERA5 retrospective estimates vs NOAA GHCNh hourly station proxies",
        "acceptance_policy_sha256": hashlib.sha256(
            Path("docs/MODEL_ACCEPTANCE_POLICY_FA.md").read_bytes()
        ).hexdigest(),
        "day_definition": "Asia/Tehran local calendar day",
        "base_data_sha256": base_meta["sha256"],
        "extension_data_sha256": extension_meta["sha256"],
        "training_target_end": "2025-12-31",
        "test_target_dates": ["2026-01-01", "2026-10-31"],
        "first_test_issue_date": FIRST_ISSUE.date().isoformat(),
        "available_data_lag_days": LAG_DAYS,
        "train_examples": len(train),
        "test_forecasts_total": len(test),
        "paired_forecasts": len(matched),
        "paired_unique_city_target_days": int(
            matched[["City", "target_date"]].drop_duplicates().shape[0]
        ),
        "station_raw_values_committed": False,
        "station_sources": station_sources,
        "station_overall": overall,
        "station_by_city_horizon": detail,
        "station_by_city_season": score_by_city_season(matched, paired),
        "failure_diagnostics": failure_diagnostics(matched, paired),
        "decision": gate,
        "limitations": (
            "ERA5 was downloaded retrospectively and can be revised. Station daily targets "
            "are proxies from quality-screened hourly reports, not true daily extrema. "
            "Overlapping forecasts and adjacent dates are dependent. "
            "This is not live forecast skill."
        ),
    }
    return report, station_audit


def load_dataset_from_frames(base: pd.DataFrame, extension: pd.DataFrame) -> pd.DataFrame:
    data = pd.concat([base, extension], ignore_index=True)
    if data.duplicated(["City", "Date"]).any():
        raise ValueError("Duplicate city/date across ERA5 snapshots")
    for _city, frame in data.groupby("City"):
        if not frame["Date"].sort_values().diff().dropna().eq(pd.Timedelta(days=1)).all():
            raise ValueError("Gap between ERA5 snapshots")
    return data.sort_values(["City", "Date"]).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, default=Path("data/era5_five_cities.csv"))
    parser.add_argument("--extension", type=Path, default=Path("data/era5_2026_five_cities.csv"))
    parser.add_argument("--station-dir", type=Path, default=Path("artifacts"))
    parser.add_argument("--out", type=Path, default=Path("docs/LATER_STATION_EVALUATION.json"))
    parser.add_argument(
        "--audit-out", type=Path, default=Path("docs/GHCNH_2026_STATION_AUDIT.json")
    )
    args = parser.parse_args()
    result, station_audit = evaluate(args.base, args.extension, args.station_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.audit_out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    args.audit_out.write_text(json.dumps(station_audit, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "paired_forecasts": result["paired_forecasts"],
                "paired_unique_city_target_days": result["paired_unique_city_target_days"],
                "station_overall": result["station_overall"],
                "decision": result["decision"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
