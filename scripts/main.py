from processing_data.load_data import load_data
from processing_data.data_cleaning import (
    filter_data,
    validate_data,
    simplify_data,
    save_data,
    get_clean_data,
)
from processing_data.detect_outliers import OutlierDetector
from analysis import (
    get_months,
    convert_to_season,
    month_temp_statistics,
    season_temp_statistic,
    summry_statistic,
    regression_alg
)
from processing_data.data_cleaning import (
    filter_data,
    validate_data,
    simplify_data,
    save_data,
    filter_by_date
)
from visualization.plots import (
    months_plot,
    season_plot,
    get_date,
    save_all_plots,
)
from processing_data.load_data import (
    load_data
)
import pandas as pd


def get_user_inputs():
    file_type = input("Enter file type (csv, excel, json): ").strip().lower()
    file_path = input("Enter file path: ").strip()
    kwargs = {}
    while True:
        key = input("Enter parameter (leave blank to finish): ").strip()
        if not key:
            break
        value = input(f"Enter value for {key}: ").strip()
        if value.lower() in ["true", "false"]:
            value = value.lower() == "true"
        elif value.isdigit():
            value = int(value)
        kwargs[key] = value
    return file_path, file_type, kwargs


def main():
    file_path, file_type, kwargs = get_user_inputs()
    df = load_data(file_path, file_type, **kwargs)

    df = filter_data(df)
    df = validate_data(df)
    if len(df) > 200_000:
        df = simplify_data(df)
    save_data(df, "data/cleaned_weather_data.csv")

    df = get_months(df)
    df["Season"] = df["Month"].apply(convert_to_season)
    print(f"Weather data is:\n{df}")

    month_temp_statistic_df = month_temp_statistics(df)
    print(f"Statistics based on month:\n{month_temp_statistic_df}")
    season_temp_statistic_df = season_temp_statistic(df)
    print(f"Statistics based on season:\n{season_temp_statistic_df}")

    df_summry= summry_statistic(df)
    print (df_summry)
    months_plot(df)
    season_plot(df)
    get_date(df)
    save_all_plots(df)


    model, model_columns = regression_alg(df)
    start_day = input("Enter date:\n")
    future_dates = pd.date_range(start_day, periods=1)
    pred_df = pd.DataFrame(
        {
            "Date_Time" : future_dates,
            "City" : ["Sanandaj"],
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
            "City": "Sanandaj",
            "Predicted_Temprature" : y_future_pred
        }
    )

    print (result)

if __name__ == "__main__":
    main()
