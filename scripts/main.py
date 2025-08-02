from analysis import (
    get_months,
    convert_to_season,
    month_temp_statistics,
    season_temp_statistic,
    # summry_statistic,
)
from data_cleaning import (
    load_data,
    filter_data,
    validate_data,
    simplify_data,
    save_data,
)
from visualization.plots import (
    months_plot,
    season_plot,
    get_date,
    save_all_plots,
)

df = load_data("data/weather_data.csv")
df = filter_data(df)
df = validate_data(df)
df = simplify_data(df)
save_data(df, "data/cleaned_weather_data.csv")


df = get_months(df)

df["Season"] = df["Month"].apply(convert_to_season)
print(f"Weather data is:\n{df}")
month_temp_statistic_df = month_temp_statistics(df)
print(f"Statistics based on month:\n{month_temp_statistic_df}")
season_temp_statistic_df = season_temp_statistic(df)
print(f"Statistics based on season:\n{season_temp_statistic_df}")
months_plot(df)
season_plot(df)
get_date(df)
save_all_plots(df)
