import streamlit as st
import pandas as pd
from matplotlib import pyplot as plt
from analysis import months_plot, season_plot, get_date, get_months, convert_to_season
from processing_data.data_cleaning import filter_by_date
from processing_data.load_data import load_data

def streamlit():
    st.title("Weather Data Analysis")
    st.write("This app analyzes weather data.")

    df = load_data()
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
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
        filtered_df = filter_by_date(df, start_date, end_date)
        filtered_df = get_months(filtered_df)

        st.subheader("Daily Average Temperature")
        get_date(filtered_df)
        st.pyplot(plt)

        st.subheader("Monthly Temperature Statistics")
        months_plot(filtered_df)
        st.pyplot(plt)

        filtered_df["Season"] = filtered_df["Month"].apply(convert_to_season)
        st.subheader("Seasonal Temperature Statistics")
        season_plot(filtered_df)
        st.pyplot(plt)

streamlit()