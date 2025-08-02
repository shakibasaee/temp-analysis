import matplotlib.pyplot as plt
import pandas as pd
import os
from analysis import save, month_temp_statistics, season_temp_statistic


def get_date(df, save=True):
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
        plt.savefig("figures/daily_avg_temperature.png", dpi=300)
        plt.close()
    else:
        plt.show()


def months_plot(df, save=True):
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
        os.makedirs("figures", exist_ok=True)
        plt.savefig("figures/monthly_avg_temperature.png", dpi=300)
        plt.close()
    else:
        plt.show()


def season_plot(df, save=True):
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
        plt.savefig("figures/seasonal_avg_temperature.png", dpi=300)
        plt.close()
    else:
        plt.show()


def save_all_plots(df):
    os.makedirs("figures", exist_ok=True)

    get_date(df, save=True)
    months_plot(df, save=True)
    season_plot(df, save=True)

    print('\nAll plots saved in "visualization/figures" folder.')
