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


@pytest.fixture
def load_filter_by_date(load_df):
    loaded_df = load_df
    start_date = pd.to_datetime("2023-10-10")   
    end_date = pd.to_datetime("2023-12-12")
    df = filter_by_date(loaded_df, start_date, end_date)
    return df


def test_filter_data(load_filter_by_date):
    df = load_filter_by_date
    clean_data = filter_data(load_filter_by_date)
    missing_values = ["na", "n.a", "n.a.", "NA"]

    assert not clean_data.isna().any().any()
    assert isinstance (clean_data, pd.DataFrame)
    assert len(clean_data) <= len(df)
    for i in missing_values:
        assert i not in clean_data.values


@pytest.fixture
def load_filter_data(load_df):
    loaded_df = load_df
    start_date = pd.to_datetime("2023-10-10")   
    end_date = pd.to_datetime("2023-12-12")
    df_filtered = filter_by_date(loaded_df, start_date, end_date)
    df = filter_data(df_filtered)
    return df


def test_validate_data(load_filter_data):
    df = load_filter_data
    validate_df = validate_data(df)
    valid_ranges = {
        "Temperature_C": (-90 , 60),
        "Precipitation_mm": (0 , 500),
        "Wind_Speed_kmh": (0 , 250),
        "Pressure_hPa": (980 , 1045)
    }

    assert isinstance (df, pd.DataFrame)
    assert len(df) >= len(validate_df)
    for col, (min_val, max_val) in valid_ranges.items():
        assert ((validate_df[col]>=min_val) & (validate_df[col]<=max_val)).all()
