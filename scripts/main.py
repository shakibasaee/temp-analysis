from processing_data.load_data import load_data
from processing_data.data_cleaning import (
    filter_data,
    validate_data,
    simplify_data,
    save_data,
    get_clean_data,
)
from processing_data.detect_outliers import WeatherOutlierAnalyzer
from analysis import (
    get_months,
    convert_to_season,
    month_temp_statistics,
    season_temp_statistic,
    summry_statistic,
)
from visualization.plots import (
    months_plot,
    season_plot,
    get_date,
    save_all_plots,
)

import os


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
    os.makedirs("data", exist_ok=True)
    save_data(df, os.path.join("data", "cleaned_weather_data.csv"))

    df = get_months(df)
    df["Season"] = df["Month"].apply(convert_to_season)

    print("Weather data:\n", df.head())
    print("Monthly statistics:\n", month_temp_statistics(df))
    print("Seasonal statistics:\n", season_temp_statistic(df))
    print("Summary:\n", summry_statistic(df))
    months_plot(df)
    season_plot(df)
    get_date(df)
    save_all_plots(df)

    print("\n--- Outlier Detection ---")

    simple_detector = WeatherOutlierAnalyzer(method="iqr")
    simple_outliers = simple_detector.detect(df["Temperature"])
    os.makedirs("plots", exist_ok=True)
    simple_detector.plot(
        df["Temperature"], simple_outliers, os.path.join("plots", "simple_outliers.png")
    )
    print(f"Simple method found {len(simple_outliers)} outliers")

    # روش ML (IsolationForest)
    ml_detector = WeatherOutlierAnalyzer(method="isolationforest")
    ml_outliers = ml_detector.detect(df["Temperature"])
    ml_detector.plot(
        df["Temperature"], ml_outliers, os.path.join("plots", "ml_outliers.png")
    )
    print(f"ML method found {len(ml_outliers)} outliers")

    print("✅ Finished detecting outliers!")


if __name__ == "__main__":
    main()
