import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib


def train_model(df, save_path=None):
    """
    Trains a linear regression model using your temperature data.
    It automatically creates features from the date (day of year, year) and one‑hot encodes cities.
    Splits the data 80/20 without shuffling (so it respects the timeline).
    Prints the MAE, RMSE, and R² on the test set.
    If you give a save_path (like "models/model.pkl"), it saves the model there.

    Args:
        df (DataFrame): Should have columns 'Date_Time', 'Temperature_C', 'City'.
        save_path (str, optional): Where to save the trained model. Default is None (no save).

    Returns:
        model: The trained LinearRegression object.
        feature_cols: List of feature column names used during training.
    """
    df = df.copy()
    df["Date_Time"] = pd.to_datetime(df["Date_Time"])
    df["Day_of_year"] = df["Date_Time"].dt.dayofyear
    df["Year"] = df["Date_Time"].dt.year

    df = pd.get_dummies(df, columns=["City"], dtype=int)

    feature_cols = ["Day_of_year", "Year"] + [
        col for col in df.columns if col.startswith("City_")
    ]
    X = df[feature_cols]
    y = df["Temperature_C"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )

    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print(f"MAE = {mae:.3f}")
    print(f"RMSE = {rmse:.3f}")
    print(f"R² = {r2:.3f}")

    if save_path:
        joblib.dump(model, save_path)
        print(f"Model saved to {save_path}")

    return model, feature_cols


def predict_future(model, feature_cols, city, target_date):
    """
    Predicts the temperature for a specific city on a single future date.
    Uses the trained model and the same feature columns.

    Args:
        model: Trained model (from train_model).
        feature_cols: List of feature column names (from train_model).
        city (str): Name of the city.
        target_date (str or datetime): The date you want to predict for (e.g., "2025-06-01").

    Returns:
        DataFrame with columns: Date, City, Predicted_Temperature.
    """
    pred_df = pd.DataFrame({"Date_Time": [pd.to_datetime(target_date)], "City": [city]})

    pred_df["Day_of_year"] = pred_df["Date_Time"].dt.dayofyear
    pred_df["Year"] = pred_df["Date_Time"].dt.year
    pred_df = pd.get_dummies(pred_df, columns=["City"], dtype=int)

    for col in feature_cols:
        if col not in pred_df.columns:
            pred_df[col] = 0

    X_pred = pred_df[feature_cols]

    temp_pred = model.predict(X_pred)[0]

    result = pd.DataFrame(
        {
            "Date": [pred_df["Date_Time"].iloc[0]],
            "City": [city],
            "Predicted_Temperature": [temp_pred],
        }
    )
    return result


def predict_batch(model, feature_cols, new_data_df):
    """
    Predicts temperatures for a whole batch of new data.
    Great for making predictions on a file like 'new_weather_data.csv'.

    Args:
        model: Trained model.
        feature_cols: List of feature column names.
        new_data_df (DataFrame): New data with at least 'Date_Time' and 'City' columns.

    Returns:
        DataFrame with columns: Date_Time, City, Predicted_Temperature.
    """
    new_df = new_data_df.copy()
    new_df["Date_Time"] = pd.to_datetime(new_df["Date_Time"])
    new_df["Day_of_year"] = new_df["Date_Time"].dt.dayofyear
    new_df["Year"] = new_df["Date_Time"].dt.year

    new_df = pd.get_dummies(new_df, columns=["City"], dtype=int)

    for col in feature_cols:
        if col not in new_df.columns:
            new_df[col] = 0

    X_new = new_df[feature_cols]
    predictions = model.predict(X_new)

    new_df["Predicted_Temperature"] = predictions
    return new_df[["Date_Time", "City", "Predicted_Temperature"]]
