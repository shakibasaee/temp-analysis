import pandas as pd
import pytest
from processing_data.load_data import load_data

@pytest.fixture
def csv_path():
    return "C:\\Users\\MSI\\temp-analysis\\data\\new_weather_data.csv"

def test_load_data(csv_path):
    df = load_data(csv_path)
    assert isinstance (df, pd.DataFrame)
    assert not df.empty
    assert "Temperature_C" in df.columns