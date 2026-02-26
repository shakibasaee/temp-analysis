import pandas as pd
from processing_data.regression_runner import reg_runner

class DummyModel:

    def predict (self, x):
        return [25]

def dummy_regression(df):
    return DummyModel(), ["Day_of_yer", "Year", "City"]

def test_regression_runner_output_structure():
    df = pd.DataFrame()
    result = reg_runner(
        regression_alg = dummy_regression,
        df = df,
        city = "Tehran",
        start_day = "2024-01-01"
    )

    assert isinstance(result , pd.DataFrame)
    assert "Date" in result.columns
    assert "City" in result.columns
    assert "Predicted_Temprature" in result.columns
    assert result.iloc[0]["City"] == "Tehran"
