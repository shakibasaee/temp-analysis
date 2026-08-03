import pandas as pd
import pytest # type: ignore

from processing_data.data_cleaning import (
    filter_by_date,
    filter_data,
    get_clean_data,
    save_data,
    simplify_data,
    validate_data,
)


@pytest.fixture
def weather_df():
    return pd.DataFrame(
        {
            "Date_Time": [
                "2023-10-09",
                "2023-10-10",
                "2023-11-01",
                "2023-12-12",
                "2023-12-13",
            ],
            "City": ["Sanandaj"] * 5,
            "Temperature_C": [8, 10, 12, 14, 16],
            "Precipitation_mm": [0, 1, 2, 3, 4],
            "Wind_Speed_kmh": [5, 10, 15, 20, 25],
            "Pressure_hPa": [1000, 1005, 1010, 1015, 1020],
        }
    )


def test_filter_by_date_keeps_only_requested_range(weather_df):
    start_date = pd.Timestamp("2023-10-10")
    end_date = pd.Timestamp("2023-12-12")

    result = filter_by_date(
        weather_df.copy(),
        start_date,
        end_date,
    )

    assert isinstance(result, pd.DataFrame)
    assert result["Date_Time"].between(start_date, end_date).all()
    assert result["Date_Time"].min() == start_date
    assert result["Date_Time"].max() == end_date
    assert len(result) == 3


def test_filter_data_removes_missing_markers_without_mutating_input():
    source = pd.DataFrame(
        {
            "City": [
                "Sanandaj",
                "NA",
                "Mashhad",
                "Rasht",
            ],
            "Temperature_C": [
                10,
                20,
                pd.NA,
                15,
            ],
        }
    )
    original = source.copy(deep=True)

    result = filter_data(source)

    pd.testing.assert_frame_equal(source, original)

    assert result.to_dict("records") == [
        {
            "City": "Sanandaj",
            "Temperature_C": 10,
        },
        {
            "City": "Rasht",
            "Temperature_C": 15,
        },
    ]


def test_validate_data_removes_rows_outside_valid_ranges():
    source = pd.DataFrame(
        {
            "Temperature_C": [10, 100],
            "Precipitation_mm": [0, 10],
            "Wind_Speed_kmh": [10, 70],
            "Pressure_hPa": [1000, 1250],
        }
    )

    result = validate_data(source)

    assert len(result) == 1
    assert result.iloc[0]["Temperature_C"] == 10


def test_simplify_data_returns_reproducible_sample():
    source = pd.DataFrame(
        {
            "value": range(200_001),
        }
    )

    first = simplify_data(source)
    second = simplify_data(source)

    assert len(first) == 200_000
    assert list(first.columns) == list(source.columns)
    pd.testing.assert_frame_equal(first, second)


def test_save_data_writes_csv_to_temporary_directory(
    tmp_path,
    capfd,
    weather_df,
):
    output_path = tmp_path / "cleaned_weather.csv"

    save_data(weather_df, output_path)

    loaded = pd.read_csv(output_path)
    out, _ = capfd.readouterr()

    assert output_path.exists()
    pd.testing.assert_frame_equal(loaded, weather_df)
    assert f"Cleaned data saved to {output_path}" in out


def test_get_clean_data_keeps_valid_rows(tmp_path):
    source = pd.DataFrame(
        {
            "Date_Time": ["2023-01-01"],
            "City": ["Sanandaj"],
            "Temperature_C": [10],
            "Precipitation_mm": [0],
            "Wind_Speed_kmh": [10],
            "Pressure_hPa": [1010],
        }
    )
    input_path = tmp_path / "weather.csv"
    source.to_csv(input_path, index=False)

    result = get_clean_data(input_path)

    pd.testing.assert_frame_equal(result, source)


def test_get_clean_data_can_simplify_large_input(tmp_path):
    source = pd.DataFrame(
        {
            "Date_Time": ["2023-01-01"] * 200_001,
            "City": ["Sanandaj"] * 200_001,
            "Temperature_C": [10] * 200_001,
            "Precipitation_mm": [0] * 200_001,
            "Wind_Speed_kmh": [10] * 200_001,
            "Pressure_hPa": [1010] * 200_001,
        }
    )
    input_path = tmp_path / "weather.csv"
    source.to_csv(input_path, index=False)

    result = get_clean_data(
        input_path,
        simplify=True,
    )

    assert len(result) == 200_000


def test_get_clean_data_removes_invalid_rows(tmp_path):
    source = pd.DataFrame(
        {
            "Date_Time": [
                "2023-01-01",
                "2023-01-02",
            ],
            "City": [
                "Sanandaj",
                "Bandar_Abbas",
            ],
            "Temperature_C": [
                10,
                100,
            ],
            "Precipitation_mm": [
                0,
                10,
            ],
            "Wind_Speed_kmh": [
                10,
                70,
            ],
            "Pressure_hPa": [
                1000,
                1250,
            ],
        }
    )
    input_path = tmp_path / "weather.csv"
    source.to_csv(input_path, index=False)

    result = get_clean_data(input_path)

    assert len(result) == 1
    assert result.iloc[0]["City"] == "Sanandaj"