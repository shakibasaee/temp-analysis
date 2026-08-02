import pandas as pd

from processing_data.load_data import load_data


def test_load_data_reads_csv_from_temporary_file(tmp_path):
    expected = pd.DataFrame(
        {
            "Date_Time": ["2024-01-01", "2024-01-02"],
            "City": ["Tehran", "Mashhad"],
            "Temperature_C": [10.5, 12.0],
        }
    )
    csv_path = tmp_path / "weather.csv"
    expected.to_csv(csv_path, index=False)

    result = load_data(csv_path, file_type="csv")

    assert isinstance(result, pd.DataFrame)
    assert not result.empty
    pd.testing.assert_frame_equal(result, expected)