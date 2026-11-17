"""Score the UTC ERA5 research forecasts against independent SSODv2 stations."""

from __future__ import annotations

import argparse
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from forecasting.multi_horizon import (
    TARGETS,
    fit_ridge,
    load_dataset,
    make_examples,
    predict_all,
    score,
    score_by_city_season,
    split_examples,
)
from scripts.audit_ssod import (
    STATIONS,
    fetch_station,
    valid_temperature,
)
from scripts.audit_ssod import (
    TARGETS as SSOD_TARGETS,
)


def parse_station(raw: bytes, station_id: str, year: int) -> pd.DataFrame:
    """Keep only unique UTC days with three physically ordered station targets."""
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError("SSOD response must be a list")
    rows = []
    seen = set()
    for item in payload:
        if item.get("STATION") != station_id:
            raise ValueError("Unexpected station ID")
        stamp = pd.to_datetime(item.get("DATE"), format="%Y-%m-%d", errors="coerce")
        if pd.isna(stamp) or stamp.year != year:
            raise ValueError("Invalid or out-of-range station date")
        if stamp in seen:
            raise ValueError("Duplicate station date")
        seen.add(stamp)
        if not all(valid_temperature(item.get(name)) for name in SSOD_TARGETS):
            continue
        mean, minimum, maximum = (float(item[name]) for name in SSOD_TARGETS)
        if not minimum <= mean <= maximum:
            continue
        rows.append((stamp, mean, minimum, maximum))
    return pd.DataFrame(rows, columns=["target_date", *TARGETS])


def load_stations(year: int) -> tuple[pd.DataFrame, list[dict]]:
    def retrieve(item: tuple[str, tuple[str, str, float, float]]) -> tuple[pd.DataFrame, dict]:
        city, (station_id, name, _lat, _lon) = item
        raw, url = fetch_station(station_id, year)
        frame = parse_station(raw, station_id, year)
        frame.insert(0, "City", city)
        return frame, {
            "city": city,
            "station_id": station_id,
            "station_name": name,
            "source_url": url,
            "response_sha256": hashlib.sha256(raw).hexdigest(),
            "valid_three_target_days": len(frame),
        }

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(retrieve, STATIONS.items()))
    return pd.concat([frame for frame, _ in results], ignore_index=True), [
        metadata for _, metadata in results
    ]


def validate_station_snapshots(stations: list[dict], audit_path: Path) -> str:
    raw = audit_path.read_bytes()
    audit = json.loads(raw)
    if audit.get("year") != 2025:
        raise ValueError("Station audit must cover the 2025 test year")
    expected = {
        (item["city"], item["station_id"]): item["response_sha256"] for item in audit["stations"]
    }
    actual = {(item["city"], item["station_id"]): item["response_sha256"] for item in stations}
    if actual != expected:
        raise ValueError("NOAA station responses changed since the coverage audit")
    return hashlib.sha256(raw).hexdigest()


def evaluate(
    path: Path,
    station_audit_path: Path = Path("docs/SSOD_STATION_AUDIT.json"),
    *,
    observation_loader=load_stations,
    timezone: str = "GMT",
    source: str = "NOAA SSODv2 station summaries",
    day_definition: str = "00:00–23:59 UTC",
    station_limitations: str = (
        "SSOD mean uses 4–24 synoptic/hourly reports when available; "
        "reported min/max can miss true daily extremes. Station and ERA5 grid points differ."
    ),
) -> dict:
    metadata = json.loads(path.with_suffix(".metadata.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if metadata.get("sha256") != digest or metadata.get("model") != "era5":
        raise ValueError("ERA5 data and provenance metadata do not match")
    if metadata.get("timezone") != timezone:
        raise ValueError(f"Station day requires a {timezone}-day ERA5 dataset")
    data = load_dataset(path)
    if len(data) != metadata["rows"] or set(data["City"]) != set(STATIONS):
        raise ValueError("Unexpected ERA5 dataset coverage")
    train, validation, test = split_examples(make_examples(data))
    model = fit_ridge(pd.concat([train, validation], ignore_index=True))
    test = test.reset_index(drop=True)
    predictions = predict_all(test, model)
    test["prediction_row"] = np.arange(len(test))
    observations, station_metadata = observation_loader(2025)
    audit_sha256 = validate_station_snapshots(station_metadata, station_audit_path)
    matched = test.merge(
        observations,
        on=["City", "target_date"],
        how="inner",
        validate="many_to_one",
        suffixes=("_era5", ""),
    )
    if matched.empty:
        raise ValueError("No test forecasts match station observations")
    indices = matched["prediction_row"].to_numpy(dtype=int)
    paired_predictions = {name: values[indices] for name, values in predictions.items()}
    era5_targets = matched[[f"{target}_era5" for target in TARGETS]].to_numpy()
    station_overall, station_detail = score(matched, paired_predictions)
    grid_overall, _ = score(matched, {"era5_grid": era5_targets})
    unmatched = test.groupby("City").size() - matched.groupby("City").size().reindex(
        test["City"].unique(), fill_value=0
    )
    return {
        "report_schema_version": 1,
        "retrieved_utc": datetime.now(UTC).isoformat(),
        "era5_data_sha256": digest,
        "era5_retrieved_utc": metadata["retrieved_utc"],
        "source": f"Open-Meteo ERA5 reanalysis forecasts versus {source}",
        "day_definition": day_definition,
        "test_target_year": 2025,
        "issue_time_assumption": (
            "ERA5 values available through issue date minus 7 days; "
            "retrospective values may have been revised"
        ),
        "station_limitations": station_limitations,
        "station_raw_values_committed": False,
        "station_audit_sha256": audit_sha256,
        "station_sources": station_metadata,
        "test_forecasts_total": len(test),
        "paired_forecasts": len(matched),
        "paired_unique_city_target_days": int(
            matched[["City", "target_date"]].drop_duplicates().shape[0]
        ),
        "unmatched_forecasts_by_city": {city: int(n) for city, n in unmatched.items()},
        "station_overall": station_overall,
        "station_by_city_horizon": station_detail,
        "station_by_city_season": score_by_city_season(matched, paired_predictions),
        "era5_grid_vs_station_overall": grid_overall,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path("data/era5_utc_five_cities.csv"))
    parser.add_argument("--out", type=Path, default=Path("docs/SSOD_EVALUATION.json"))
    parser.add_argument("--station-audit", type=Path, default=Path("docs/SSOD_STATION_AUDIT.json"))
    args = parser.parse_args()
    result = evaluate(args.data, args.station_audit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "paired_forecasts": result["paired_forecasts"],
                "paired_unique_city_target_days": result["paired_unique_city_target_days"],
                "station_overall": result["station_overall"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
