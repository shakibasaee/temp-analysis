from data_cleaning import (
    load_data,
    filter_data,
    validate_data,
    simplify_data,
    save_data,
)

df = load_data("data/weather_data.csv")
df = filter_data(df)
df = validate_data(df)
df = simplify_data(df)
save_data(df, "data/cleaned_weather_data.csv")
