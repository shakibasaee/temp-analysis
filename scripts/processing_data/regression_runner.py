import pandas as pd

try:
    from ..model_config import LinearRegressionConfig
    from ..models.linear_regression import LinearRegressionModel
except ImportError:
    from model_config import LinearRegressionConfig
    from models.linear_regression import LinearRegressionModel


def reg_runner(
    model_or_factory,
    df: pd.DataFrame,
    city: str,
    start_day,
    config: LinearRegressionConfig | None = None,
) -> pd.DataFrame:
    """Predict one future date while preserving the legacy call signature.

    ``model_or_factory`` may be a fitted ``LinearRegressionModel`` (preferred)
    or the legacy ``regression_alg`` callable. Passing a fitted model lets the
    dashboard predict several cities without retraining for every city.
    """
    if isinstance(model_or_factory, LinearRegressionModel):
        model = model_or_factory
    elif callable(model_or_factory):
        trained = model_or_factory(df, config=config) if config else model_or_factory(df)
        model = trained[0] if isinstance(trained, tuple) else trained
    else:
        model = LinearRegressionModel(config).fit(df)

    if not isinstance(model, LinearRegressionModel):
        raise TypeError("Regression factory must return a LinearRegressionModel")

    prediction_frame = pd.DataFrame(
        {
            model.config.date_column: [pd.to_datetime(start_day)],
            model.config.city_column: [city],
        }
    )
    prediction = model.predict(prediction_frame)
    return pd.DataFrame(
        {
            "Date": prediction_frame[model.config.date_column],
            "City": [city],
            # Keep the historical misspelling for dashboard compatibility.
            "Predicted_Temprature": prediction,
        }
    )
