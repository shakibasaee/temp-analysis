from processing_data.load_data import load_data
from processing_data.data_cleaning import (
    filter_data,
    validate_data,
    simplify_data,
    save_data,
    filter_by_date,
)
from analysis import (
    get_months,
    convert_to_season,
    month_temp_statistics,
    season_temp_statistic,
    summry_statistic,
    regression_alg,
    months_plot,
    season_plot,
    get_date,
)
import pandas as pd
from processing_data.regression_runner import reg_runner
from matplotlib import pyplot as plt
from pathlib import Path

from processing_data.detect_outliers import WeatherOutlierAnalyzer


def get_user_inputs():
    file_type = input("Enter file type (csv, excel, json): ").strip().lower()
    file_path = input("Enter file path: ").strip()
    start_date = input("Enter start date (YYYY/MM/DD): ")
    end_date = input("Enter end date (YYYY/MM/DD): ")
    city = input("Enter city: ").strip()
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
    return file_path, file_type, kwargs, start_date, end_date, city


def main():
    file_path, file_type, kwargs, start_date, end_date, city = get_user_inputs()
    df = load_data(file_path, file_type, **kwargs)
    df = filter_data(df)
    df = validate_data(df)
    if len(df) > 200_000:
        df = simplify_data(df)
    output_dir = Path("artifacts")
    output_dir.mkdir(exist_ok=True)
    save_data(df, output_dir / "cleaned_weather_data.csv")

    if start_date or end_date:
        df_view = filter_by_date(
            df.copy(),
            start_date or df["Date_Time"].min(),
            end_date or df["Date_Time"].max(),
        )
    else:
        df_view = df.copy()
    if df_view.empty:
        raise ValueError("The selected date range contains no observations")

    df_view = get_months(df_view)
    df_view["Season"] = df_view["Month"].apply(convert_to_season)

    print("Weather data:\n", df_view.head())
    print("Monthly statistics:\n", month_temp_statistics(df_view))
    print("Seasonal statistics:\n", season_temp_statistic(df_view))
    print("Summary:\n", summry_statistic(df_view))
    plot_dir = output_dir / "plots"
    plot_dir.mkdir(exist_ok=True)
    for name, plotter in (
        ("daily", get_date),
        ("monthly", months_plot),
        ("seasonal", season_plot),
    ):
        figure = plotter(df_view.copy())
        figure.savefig(plot_dir / f"{name}.png", bbox_inches="tight")
        plt.close(figure)

    print("\n--- Outlier Detection ---")

    detector = WeatherOutlierAnalyzer(df_view)
    outliers = detector.analyze("Temperature_C")
    detector.plot_outliers("Temperature_C", str(plot_dir))
    print(
        f"Outlier counts: {outliers[['IQR', 'Zscore', 'IsolationForest']].sum().to_dict()}"
    )

    start_day = input("Enter date:\n")
    if pd.to_datetime(start_day) <= pd.to_datetime(df["Date_Time"]).max():
        raise ValueError("Prediction date must follow the latest observation")
    model, _ = regression_alg(df)
    result = reg_runner(model, df, city, start_day)

    print(result)


if __name__ == "__main__":
    main()
