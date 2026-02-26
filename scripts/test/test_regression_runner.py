import pandas as pd
from processing_data.regression_runner import reg_runner

class DummyModelOutput:

    def predict (self, x):
        return [25]

def dummy_regression(df):
    return DummyModelOutput(), ["Day_of_yer", "Year", "City"]

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


class DummyModelPredict:
    def __init__(self):
        self.called = False

    def predict(self, x):
        self.called = True
        return [30]
    


def dummy_regression(df):
    model = DummyModelPredict()
    return model, ["Day_of_year", "Year", "City"]


def test_predict_called():
    df = pd.DataFrame()
    model, cols = dummy_regression(df)

    result = reg_runner(
        regression_alg=lambda df: (model, cols),
        df=df,
        city="Tehran",
        start_day="2024-01-01"
    )

    assert model.called is True