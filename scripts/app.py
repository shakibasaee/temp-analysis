import streamlit as st
import pandas as pd
from matplotlib import pyplot as plt
import datetime as dt
from analysis import (
    months_plot, 
    season_plot, 
    get_date, 
    get_months, 
    convert_to_season,
    regression_alg, 
    reg_plot)
from processing_data.data_cleaning import filter_by_date
from processing_data.load_data import load_data
from processing_data.regression_runner import reg_runner

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

        st.subheader("Prediction section")
        pre_date = st.date_input(
            "Select date to predect", 
            value=(pd.to_datetime(date_range[1]) + dt.timedelta(days = 1)).date()
        )

        cities = ["Sanandaj", "Mashhad", "Yazd", "Bandar Abbas", "Rasht"]
        city = st.selectbox("Select city", cities)
        
        st.subheader("Temprature prediction")
        result_pred_df = reg_runner(regression_alg, df, city, pre_date)
        fig = reg_plot(filtered_df, result_pred_df, city)
        st.pyplot(fig)


streamlit()