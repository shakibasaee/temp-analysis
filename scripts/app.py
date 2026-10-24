"""Streamlit view of archived-run scores and the legacy temperature workflow."""

import json
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from matplotlib import pyplot as plt

from forecasting.config import ForecastConfig
from forecasting.data import load_daily_data
from forecasting.experiment import benchmark, predict_next_day, train_final
from scripts.analysis import (
    convert_to_season,
    get_date,
    get_months,
    months_plot,
    reg_plot,
    season_plot,
)
from scripts.processing_data.data_cleaning import filter_by_date

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "new_weather_data.csv"
CONFIG_PATH = PROJECT_ROOT / "configs" / "forecast.json"
ARCHIVED_REPORT = PROJECT_ROOT / "reports" / "archived-ifs-2025.json"


def benchmark_tables(report: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Expose the same committed benchmark at all dashboard breakdowns."""
    names = {
        "temperature_c": "Daily mean temperature (°C)",
        "wind_speed_kmh": "Daily mean wind (km/h)",
        "pressure_hpa": "Daily mean sea-level pressure (hPa)",
        "precipitation_gt_0mm": "Precipitation occurrence (>0 mm)",
        "precipitation_ge_1mm": "Precipitation occurrence (≥1 mm)",
    }
    summary, cities, folds = [], [], []
    for key, result in report["results"].items():
        common = {"Variable": names[key], "Metric": result["metric"].upper()}
        summary.append({**common, "Cases": result["n"], "Raw IFS": result["raw_ifs"], "Candidate": result["candidate"]})
        for city, scores in result["by_city"].items():
            cities.append({**common, "City": city, "Cases": scores["n"], "Raw IFS": scores["raw_ifs"], "Candidate": scores["candidate"]})
        for fold, scores in result["by_fold"].items():
            folds.append({**common, "Period": fold, "Cases": scores["n"], "Raw IFS": scores["raw_ifs"], "Candidate": scores["candidate"]})
    return pd.DataFrame(summary), pd.DataFrame(cities), pd.DataFrame(folds)


@st.cache_resource(show_spinner="Evaluating and fitting the next-day forecast...")
def forecast_bundle(
    data_path: str, config_path: str, data_modified: int, config_modified: int
):
    """Cache a forecast until the input data or configuration changes."""
    data = load_daily_data(data_path)
    config = ForecastConfig.from_json(config_path)
    report = benchmark(data, config)
    artifact = train_final(data, config, report["selected_model"])
    predictions = predict_next_day(artifact, data)
    return data, report, predictions


def streamlit() -> None:
    st.title("Weather forecasting: historical evaluation")
    st.write("Four daily variables across five Iranian city grid cells. These are archived forecasts scored against ERA5 reanalysis, not a live forecast service or station validation.")
    try:
        archived = json.loads(ARCHIVED_REPORT.read_text(encoding="utf-8"))
        summary, city_scores, fold_scores = benchmark_tables(archived)
    except (FileNotFoundError, KeyError, ValueError) as exc:
        st.error(f"Archived-run benchmark unavailable: {exc}")
        st.stop()
    st.caption("Historical test: 2025-01-01 to 2025-12-31, weekly Wednesday UTC targets. Monday 00 UTC ECMWF IFS HRES runs; decision time Tuesday 12 UTC. Reference: Open-Meteo ERA5 grid cells. MAE uses each variable's displayed unit; Brier is unitless and lower is better.")
    st.subheader("Raw model versus retrospective correction")
    st.dataframe(summary, hide_index=True)
    st.subheader("Results by city")
    st.dataframe(city_scores, hide_index=True)
    st.subheader("Results by rolling quarter")
    st.dataframe(fold_scores, hide_index=True)
    st.caption("Candidate: city-specific mean bias correction for continuous variables; logistic calibration for precipitation. Training uses only earlier archived runs and ERA5 labels assumed available seven days after the target. The two precipitation rows test different event thresholds. See the method and report for calibration bins and exceptions.")

    st.divider()
    st.header("Legacy temperature exploration")
    st.write("The charts and next-day estimate below use the original dataset, whose provenance is unknown. The displayed estimate is historical and separate from the four-variable evaluation above.")

    try:
        data, report, predictions = forecast_bundle(
            str(DATA_PATH),
            str(CONFIG_PATH),
            DATA_PATH.stat().st_mtime_ns,
            CONFIG_PATH.stat().st_mtime_ns,
        )
    except (FileNotFoundError, ValueError) as exc:
        st.error(f"Forecast data is unavailable: {exc}")
        st.stop()

    cities = sorted(data["City"].unique().tolist())
    selected_cities = st.multiselect("Select cities", cities, default=[cities[0]])
    if not selected_cities:
        st.warning("Please select at least one city.")
        st.stop()

    min_date = data["Date_Time"].min().date()
    max_date = data["Date_Time"].max().date()
    date_range = st.date_input(
        "Select historical date range:",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if len(date_range) != 2:
        st.info("Select both start and end dates.")
        st.stop()

    start_date, end_date = map(pd.Timestamp, date_range)
    filtered = filter_by_date(
        data.loc[data["City"].isin(selected_cities)].copy(), start_date, end_date
    )
    if filtered.empty:
        st.info("No observations in the selected date range.")
        st.stop()
    filtered = get_months(filtered)

    st.subheader("Daily Average Temperature")
    figure = get_date(filtered.copy())
    st.pyplot(figure)
    plt.close(figure)

    st.subheader("Monthly Temperature Statistics")
    figure = months_plot(filtered)
    st.pyplot(figure)
    plt.close(figure)

    filtered["Season"] = filtered["Month"].apply(convert_to_season)
    st.subheader("Seasonal Temperature Statistics")
    figure = season_plot(filtered)
    st.pyplot(figure)
    plt.close(figure)

    st.subheader("Historical next-day temperature estimate")
    selected_model = report["selected_model"]
    selected_report = report["models"][selected_model]
    st.caption(
        f"Latest observation: {max_date}; forecast date: {predictions['Date'].iloc[0]}. "
        f"Selected model: {selected_model}. Historical held-out MAE: "
        f"{selected_report['test']['mae']:.2f} °C."
    )
    if predictions["Date"].min() < date.today():
        st.warning(
            "The bundled observations are stale. This is a historical next-day "
            "estimate, not a current weather forecast."
        )
    shown = predictions.loc[predictions["City"].isin(selected_cities)].copy()
    shown["Held_out_MAE_C"] = shown["City"].map(
        {
            city: values["mae"]
            for city, values in selected_report["test_by_city"].items()
        }
    )
    st.dataframe(shown, hide_index=True)

    figure = reg_plot(filtered, shown, selected_cities)
    st.pyplot(figure)
    plt.close(figure)


if __name__ == "__main__":
    streamlit()
