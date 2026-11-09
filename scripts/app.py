"""Streamlit exploration and the selected next-day forecast."""

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
    st.title("Weather Data Analysis")
    st.write("Explore historical temperatures and the selected next-day forecast.")

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

    st.subheader("Next-day forecast")
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
