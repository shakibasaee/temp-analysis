from analysis import (
    get_months,
    convert_to_season,
    month_temp_statistics,
    season_temp_statistic,
    summry_statistic,
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


file_type = input("Enter your file type (csv, excel or json):\n").strip().lower()
file_path = input("Add your file address plz:\n").strip().lower()

new_kwargs = {}
while True:
    key = input("Enter parameter (fill this fild blank and enter when your don):\n").strip()
    if not key:
        break
    value = input(f"Enter value of {key}:\n").strip()
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
    elif value.isdigit():
        value = int(value)
    new_kwargs[key] = value

df = load_data(file_path, file_type, **new_kwargs)

start_date = input("Enter start date (YYYY/MM/DD):\n")
end_date = input("Enter end date (YYYY/MM/DD):\n")
df = filter_by_date(df,start_date,end_date)
print(df)

# df = load_data("data/new_weather_data.csv")
df = filter_data(df)
df = validate_data(df)
if (len(df)>200_000):
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
