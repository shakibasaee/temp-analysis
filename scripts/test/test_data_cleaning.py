import pandas as pd
import datetime as dt
import pytest
import os
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



@pytest.fixture
def load_validate_date(load_df):
    loaded_df = load_df
    start_date = pd.to_datetime("2023-10-10")   
    end_date = pd.to_datetime("2023-12-12")
    df_filtered = filter_by_date(loaded_df, start_date, end_date)
    clean_df = filter_data(df_filtered)
    df = validate_data(clean_df)
    return df



def test_simplify_data(load_validate_date):
    df = load_validate_date
    df_large = pd.concat([df]*1000, ignore_index = True)
    simplify_df = simplify_data(df_large)
    sample1 = simplify_data(df_large)
    sample2 = simplify_data(df_large)

    assert isinstance (simplify_df, pd.DataFrame)
    assert len(simplify_df) == 200_000
    assert all(simplify_df.columns == df.columns)
    pd.testing.assert_frame_equal(sample1, sample2)



def test_save_data(load_validate_date, capfd):
    df = load_validate_date
    output_path = "data/cleaned_weather_data.csv"
    save_data(df , output_path)
    df_loaded = pd.read_csv(output_path)
    out , err = capfd.readouterr()
    

    assert os.path.exists(output_path)
    assert df.shape[0] == df_loaded.shape[0] , "Numbers of rows mismatch"
    assert df.shape[1] == df_loaded.shape[1] , "Numbers of columns mismatch"
    assert list(df.columns) == list(df_loaded.columns)
    assert f"Cleaned data saved to {output_path}" in out

    os.remove(output_path)


def test_get_clean_data_valid(tmp_path):
    df = pd.DataFrame({
        "Data_Time": ["2023-01-01"],
        "City": ["Sanandaj"],
        "Temperature_C": [10],
        "Precipitation_mm": [0],
        "Wind_Speed_kmh": [10],
        "Pressure_hPa": [1010]
    })

    input_csv = tmp_path / "temp_weather.csv"
    df.to_csv(input_csv, index = False)\
    
    result = get_clean_data(input_csv)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 1



def test_get_clean_big_data(tmp_path):
    df = pd.DataFrame({
        "Date_Time": ["2023-01-01"] * 500_000,
        "City": ["Sanandaj"] * 500_000,
        "Temperature_C": [10] * 500_000,
        "Precipitation_mm": [0] * 500_000,
        "Wind_Speed_kmh": [10] * 500_000,
        "Pressure_hPa": [1010] * 500_000
    })


    input_csv = tmp_path / "tmp_weather.csv"
    df.to_csv(input_csv , index = False)

    result = get_clean_data(input_csv , simplify = True)

    assert len(result) == 200_000