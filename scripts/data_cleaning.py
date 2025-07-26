import pandas as pd


def load_data(file_path):
    df = pd.read_csv(file_path)
    return df


def filter_data(df):
    missing_values = ["na","n.a","n.a.","NA",0,0.0]
    df.replace(missing_values, pd.NA, replace = True)
    df = df.dropna()
    return df


def validate_data(df):
    df_unvalid = df[
        (df["Humidity_pct"] < 0)
        | (df["Humidity_pct"] > 100)
        | (df["Temperature_C"] > 60)
        | (df["Temperature_C"] < -90)
        | (df["Precipitation_mm"] < 0)
        | (df["Precipitation_mm"] > 500)
        | (df["Wind_Speed_kmh"] < 0)
        | (df["Wind_Speed_kmh"] > 250)
    ]
    return df.drop(df_unvalid.index)


def simplify_data(df):
    df_sampled = df.sample(n=200_000, random_state=42)
    return df_sampled


def save_data(df, output_path):
    df.to_csv(output_path, index=False)
    print(f"Cleaned data saved to {output_path}")
