import streamlit as st
import pandas as pd
from matplotlib import pyplot as plt
import datetime as dt
from pathlib import Path
from scripts.analysis import (
    months_plot,
    season_plot,
    get_date,
    get_months,
    convert_to_season,
    regression_alg,
    reg_plot,
)
from scripts.processing_data.data_cleaning import filter_by_date

from scripts.processing_data.regression_runner import reg_runner


def streamlit():
    st.title("Weather Data Analysis")
    st.write("This app analyzes weather data.")

    data_path = Path(__file__).resolve().parents[1] / "data" / "new_weather_data.csv"
    df = pd.read_csv(data_path)
    df["Date_Time"] = pd.to_datetime(df["Date_Time"])

    min_date = df["Date_Time"].min()
    max_date = df["Date_Time"].max()

    date_range = st.date_input(
        "Select date range:",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if len(date_range) == 2:
        start_date, end_date = (
            pd.to_datetime(date_range[0]),
            pd.to_datetime(date_range[1]),
        )
        filtered_df = filter_by_date(df, start_date, end_date)
        filtered_df = get_months(filtered_df)

        st.subheader("Daily Average Temperature")
        figure = get_date(filtered_df)
        st.pyplot(figure)
        plt.close(figure)

        st.subheader("Monthly Temperature Statistics")
        figure = months_plot(filtered_df)
        st.pyplot(figure)
        plt.close(figure)

        filtered_df["Season"] = filtered_df["Month"].apply(convert_to_season)
        st.subheader("Seasonal Temperature Statistics")
        figure = season_plot(filtered_df)
        st.pyplot(figure)
        plt.close(figure)

        st.subheader("Prediction section")
        st.caption("Exploratory calendar-only estimate. For validated next-day forecasts, use the forecasting CLI.")
        pre_date = st.date_input(
            "Select date to predect",
            value=(max_date + dt.timedelta(days=1)).date(),
            min_value=(max_date + dt.timedelta(days=1)).date(),
        )

        cities = sorted(df["City"].dropna().unique().tolist())

        selected_cities = st.multiselect(
            "Select cities",
            cities,
            default=[cities[0]],
        )

        if not selected_cities:
            st.warning("Please select at least one city.")
            st.stop()

        cities_df = filtered_df[filtered_df["City"].isin(selected_cities)].copy()

        st.subheader("temp prediction")

        # Train once, then reuse the same fitted preprocessing/model pipeline
        # for every selected city.
        regression_model, _ = regression_alg(df)
        pred_frames = []
        for c in selected_cities:
            pred = reg_runner(regression_model, df, c, pre_date)
            pred["City"] = c
            pred_frames.append(pred)

        result_pred_df = pd.concat(pred_frames, ignore_index=True)

        fig = reg_plot(cities_df, result_pred_df, selected_cities)

        st.pyplot(fig)
        plt.close(fig)


if __name__ == "__main__":
    streamlit()
