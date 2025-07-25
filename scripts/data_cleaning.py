import pandas as pd
import os

def load_data(file_path):
    df = pd.read_csv(
        "C:/Users/Nitro 5/Documents/GitHub/temp-analysis/data/weather_data.csv"
    )
    return df


def filter_data(df):
    df = df.dropna()
    return df


def simplify_data(df):
    df_sampled = df.sample(n=200_000, random_state=42)
    return df_sampled


def save_cleaned_data(df, output_path):
    output_path = "data/cleaned_weather_data.csv"
    df.to_csv(output_path, index=False)
    print(f"Cleaned data saved to {output_path}")

def clean_data():
    file_path = "data/weather_data.csv"
    output_path = "data/weather_data_cleaned.csv"

    df = load_data(file_path)
    df = filter_data(df)
    df = simplify_data(df)
    save_cleaned_data(df, output_path)


clean_data()
print("Data cleaning completed")
