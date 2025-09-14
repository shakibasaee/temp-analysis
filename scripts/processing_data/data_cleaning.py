import pandas as pd


def filter_by_date(df, start_date, end_date):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    df["Date_Time"] = pd.to_datetime(df["Date_Time"])
    if start_date > end_date:
        raise ValueError(
            f"Start date ({start_date.date()}) is bigger than end date ({end_date.date()})!"
        )
    return df.loc[(df["Date_Time"] >= start_date) & (df["Date_Time"] <= end_date)]


def filter_data(df):
    missing_values = ["na", "n.a", "n.a.", "NA"]
    df.replace(missing_values, pd.NA, inplace=True)
    df = df.dropna()
    return df


def validate_data(df):
    df_unvalid = df[
        (df["Temperature_C"] > 60)
        | (df["Temperature_C"] < -90)
        | (df["Precipitation_mm"] < 0)
        | (df["Precipitation_mm"] > 500)
        | (df["Wind_Speed_kmh"] < 0)
        | (df["Wind_Speed_kmh"] > 250)
        | (df["Pressure_hPa"] < 980)
        | (df["Pressure_hPa"] > 1045)
    ]
    return df.drop(df_unvalid.index)


def simplify_data(df):
    df_sampled = df.sample(n=200_000, random_state=42)
    return df_sampled


def save_data(df, output_path):
    df.to_csv(output_path, index=False)
    print(f"Cleaned data saved to {output_path}")


def get_clean_data(input_path, simplify=False):
    df = pd.read_csv(input_path)
    df = filter_data(df)
    df = validate_data(df)

    if simplify:
        df = simplify_data(df)

    return df
