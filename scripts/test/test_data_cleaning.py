import pandas as pd
import datetime as dt
import pytest
from processing_data.load_data import load_data
from processing_data.data_cleaning import (
    filter_by_date,
    filter_data,
    validate_data,
    simplify_data,
    save_data,
    get_clean_data
)


@pytest.fixture
def load_df():
    df = load_data()
    return df


def test_filter_by_date(load_df):
    start_date = pd.to_datetime("2023-10-10")   
    end_date = pd.to_datetime("2023-12-12")
    filtered_data = filter_by_date(load_df, start_date, end_date)
    filtered_data.loc[: , "Date_Time"] = pd.to_datetime(filtered_data["Date_Time"])

    assert isinstance (filtered_data, pd.DataFrame)
    mask = (filtered_data["Date_Time"] >= start_date) & (filtered_data["Date_Time"] <= end_date)
    assert mask.all()
    assert len(filtered_data) <= len(load_df)


# def test_filter_by_date_empty(df):
#     start_date = "2025-1-1"
#     end_date = "2024-2-2"
#     filtered_data = filter_by_date(df, start_date, end_date)
    
#     assert filtered_data.empty