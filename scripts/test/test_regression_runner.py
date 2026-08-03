import pandas as pd

from processing_data.regression_runner import reg_runner


class DummyOutputModel:
    def predict(self, features):
        return [25]


class PredictSpyModel:
    def __init__(self):
        self.called = False

    def predict(self, features):
        self.called = True
        return [30]


def output_regression(_df):
    model_columns = [
        "Day_of_year",
        "Year",
        "City_Tehran",
    ]

    return DummyOutputModel(), model_columns


def test_regression_runner_returns_expected_output_structure():
    result = reg_runner(
    output_regression,
    pd.DataFrame(),
    "Tehran",
    "2024-01-01",
)

    assert list(result.columns) == [
        "Date",
        "City",
        "Predicted_Temprature",
    ]
    assert result.iloc[0]["Date"] == pd.Timestamp("2024-01-01")
    assert result.iloc[0]["City"] == "Tehran"
    assert result.iloc[0]["Predicted_Temprature"] == 25


def test_regression_runner_calls_model_predict():
    model = PredictSpyModel()
    model_columns = [
        "Day_of_year",
        "Year",
        "City_Tehran",
    ]

    def regression_stub(_df):
        return model, model_columns

    reg_runner(
    regression_stub,
    pd.DataFrame(),
    "Tehran",
    "2024-01-01",
)

    assert model.called is True