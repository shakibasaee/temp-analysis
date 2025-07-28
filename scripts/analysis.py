from matplotlib import pyplot as plt
import pandas as pd
from main import df

def get_months():
    df["Month"] = pd.to_datetime(
        df["Date_Time"]
    ).dt.month  # convert "Date_Time" to datetime and add to "Month" series


get_months()


def convert_to_season(month):
    if month in [12, 1, 2]:
        return "Winter"
    elif month in [3, 4, 5]:
        return "Spring"
    elif month in [6, 7, 8]:
        return "Summer"
    elif month in [9, 10, 11]:
        return "Fall"


def get_season():
    df["Season"] = df["Month"].apply(convert_to_season)
    print(df)


get_season()


def summry_statistic():
    df.drop(columns= ["Month"], inplace = True)
    print(f"\nSummary of statistics:\n{df.describe()}")


summry_statistic()


def get_date():
    df["Date_Time"] = pd.to_datetime(df["Date_Time"])
    df["Date"] = df["Date_Time"].dt.date

    daily_avg = df.groupby("Date")["Temperature_C"].mean()
    daily_avg.plot(kind="bar", figsize=(10, 6), color="purple")
    plt.title("Daily Average Temperature")
    plt.xlabel("Date")
    plt.ylabel("Temperature (C)")
    plt.grid(True)
    plt.style.use("ggplot")
    plt.xticks(fontsize=7)

    plt.show()


get_date()
