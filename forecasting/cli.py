"""Commands for chronological temperature and experimental weather forecasts."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

import pandas as pd

from .config import ForecastConfig
from .data import load_daily_data
from .experiment import (
    benchmark,
    load_artifact,
    predict_next_day,
    save_artifact,
    train_final,
)
from .open_meteo import fetch_era5, save_snapshot
from .weather import benchmark_weather, predict_weather_baselines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch-era5", help="Fetch a documented ERA5 snapshot")
    fetch.add_argument("--start", required=True, type=date.fromisoformat)
    fetch.add_argument("--end", required=True, type=date.fromisoformat)
    fetch.add_argument("--out", required=True, type=Path)
    fetch.add_argument("--manifest-out", required=True, type=Path)
    for name in (
        "benchmark",
        "train",
        "predict",
        "weather-benchmark",
        "weather-baseline",
    ):
        command = commands.add_parser(name)
        command.add_argument("--data", default="data/new_weather_data.csv", type=Path)
        if name != "predict":
            command.add_argument("--config", default="configs/forecast.json", type=Path)
        if name == "train":
            command.add_argument(
                "--model-out", default="artifacts/temperature_model.joblib", type=Path
            )
            command.add_argument(
                "--report-out", default="artifacts/benchmark.json", type=Path
            )
        if name == "weather-benchmark":
            command.add_argument("--report-out", type=Path)
            command.add_argument("--manifest", type=Path)
        if name == "weather-baseline":
            command.add_argument("--allow-historical", action="store_true")
        if name == "predict":
            command.add_argument(
                "--model", default="artifacts/temperature_model.joblib", type=Path
            )
    args = parser.parse_args(argv)
    if args.command == "fetch-era5":
        try:
            data, manifest = fetch_era5(args.start, args.end)
            save_snapshot(data, manifest, args.out, args.manifest_out)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        print(f"Wrote {len(data)} rows to {args.out} and {args.manifest_out}")
        return 0
    if args.command.startswith("weather-"):
        data = pd.read_csv(args.data)
        config = ForecastConfig.from_json(args.config)
        if args.command == "weather-baseline":
            try:
                output = predict_weather_baselines(
                    data,
                    config.min_history_days,
                    allow_historical=args.allow_historical,
                )
            except ValueError as exc:
                parser.error(str(exc))
            print(output.to_csv(index=False), end="")
            return 0
        report = benchmark_weather(data, config)
        report["data"]["source_sha256"] = hashlib.sha256(
            args.data.read_bytes()
        ).hexdigest()
        if args.manifest:
            manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
            if manifest.get("csv_sha256") != report["data"]["source_sha256"]:
                parser.error("Manifest checksum does not match the input CSV")
            report["source_metadata"] = {
                "source": manifest["source"],
                "source_url": manifest["source_url"],
                "model": manifest["model"],
                "nature": manifest["nature"],
                "license": manifest["license"],
                "retrieved_at_utc": manifest["retrieved_at_utc"],
                "manifest": args.manifest.as_posix(),
            }
        rendered = json.dumps(report, indent=2) + "\n"
        print(rendered, end="")
        if args.report_out:
            args.report_out.parent.mkdir(parents=True, exist_ok=True)
            args.report_out.write_text(rendered, encoding="utf-8")
        return 0
    data = load_daily_data(args.data)
    if args.command == "predict":
        output = predict_next_day(load_artifact(args.model), data)
        print(output.to_csv(index=False), end="")
        return 0
    config = ForecastConfig.from_json(args.config)
    report = benchmark(data, config)
    report["data"]["source_sha256"] = hashlib.sha256(args.data.read_bytes()).hexdigest()
    print(json.dumps(report, indent=2))
    if args.command == "train":
        artifact = train_final(data, config, report["selected_model"])
        artifact["source_sha256"] = report["data"]["source_sha256"]
        save_artifact(artifact, args.model_out)
        args.report_out.parent.mkdir(parents=True, exist_ok=True)
        args.report_out.write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
