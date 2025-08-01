from matplotlib import pyplot as plt
from matplotlib.pylab import save
import pandas as pd
import os


def get_months(df):
    df["Month"] = pd.to_datetime(
        df["Date_Time"]
    ).dt.month  # convert "Date_Time" to datetime and add to "Month" series
    return df


def convert_to_season(month):
    if month in [12, 1, 2]:
        return "Winter"
    elif month in [3, 4, 5]:
        return "Spring"
    elif month in [6, 7, 8]:
        return "Summer"
    elif month in [9, 10, 11]:
        return "Autumn"
    else:
        return "Unknown"


def month_temp_statistics(df):
    month_temp_statistic_df = (
        df.groupby("Month")["Temperature_C"]
        .agg(Mean_temp_c="mean", Min_temp_c="min", Max_temp_c="max")
        .reset_index()
    )

    return month_temp_statistic_df


def season_temp_statistic(df):
    season_temp_statistic_df = (
        df.groupby("Season")["Temperature_C"]
        .agg(Mean_temp_C="mean", Max_temp_C="max", Min_temp_C="min")
        .reset_index()
    )
    return season_temp_statistic_df


def summry_statistic(df):
    df.drop(columns=["Month"], inplace=True)
    print(f"\nSummary of statistics:\n{df.describe()}")


def get_date(df):
    df["Date_Time"] = pd.to_datetime(df["Date_Time"])
    df["Date"] = df["Date_Time"].dt.date

    daily_avg = df.groupby("Date")["Temperature_C"].mean()
    daily_avg.plot(kind="bar", figsize=(10, 6), color="purple")
    plt.title("Daily Average Temperature")
    plt.xlabel("Date")
    plt.ylabel("Temperature (C)")
    plt.grid(True)
    plt.style.use("ggplot")
    plt.tight_layout()

    if save:
        plt.savefig("outputs/daily_avg_temperature.png", dpi=300)
        plt.close()
    else:
        plt.show()


def months_plot(df):
    stats = month_temp_statistics(df)
    stats.set_index("Month", inplace=True)

    stats["Mean_temp_c"].plot(kind="bar", figsize=(10, 6), color="red")
    plt.style.use("ggplot")
    plt.title("Average Monthly Temperature")
    plt.xlabel("Month")
    plt.ylabel("Mean Temperature (°C)")
    plt.grid(True)
    plt.style.use("ggplot")

    if save:
        plt.savefig("outputs/monthly_avg_temperature.png", dpi=300)
        plt.close()
    else:
        plt.show()


def season_plot(df):
    stats = season_temp_statistic(df)
    stats.set_index("Season", inplace=True)
    plt.style.use("ggplot")

    plt.figure(figsize=(8, 8))
    plt.pie(
        stats["Mean_temp_C"],
        labels=stats.index,
        autopct="%1.1f%%",
        startangle=90,
        colors=["#ff9999", "#66b3ff", "#99ff99", "#ffcc99"],
    )
    plt.title("Average Seasonal Temperature")
    plt.axis("equal")
    plt.tight_layout()

    if save:
        plt.savefig("outputs/seasonal_avg_temperature.png", dpi=300)
        plt.close()
    else:
        plt.show()


def save_all_plots(df):
    os.makedirs("outputs", exist_ok=True)

    get_date(df, save=True)
    months_plot(df, save=True)
    season_plot(df, save=True)

    print("All plots saved in 'outputs/' folder.")
