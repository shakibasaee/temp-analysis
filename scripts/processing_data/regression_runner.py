import pandas as pd
import datetime as dt


def reg_runner(regression_alg, df, city, start_day):
    
    model, model_columns = regression_alg(df)
    future_dates = pd.date_range(start_day, periods=1)
    pred_df = pd.DataFrame(
        {
            "Date_Time" : future_dates,
            "City" : [city],
        }
    )

    pred_df["Date_Time"] = pd.to_datetime(pred_df["Date_Time"])
    pred_df["Day_of_year"] = pred_df["Date_Time"].dt.dayofyear
    pred_df["Year"] = pred_df["Date_Time"].dt.year
    pred_df = pd.get_dummies(pred_df, columns=["City"])
    cols_to_int = [col for col in pred_df.columns if col not in ["Date_Time"]]
    pred_df[cols_to_int] = pred_df[cols_to_int].astype(int)

    date_col = pred_df["Date_Time"].copy()

    for col in model_columns:
        if col not in pred_df.columns:
            pred_df[col] = 0

    pred_df = pred_df[model_columns]

    y_future_pred = model.predict(pred_df)

    result = pd.DataFrame(
        {
            "Date": date_col,
            "City": city,
            "Predicted_Temprature" : y_future_pred
        }
    )
    return result