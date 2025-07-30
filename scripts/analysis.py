from matplotlib import pyplot as plt
import pandas as pd
# from main import df


def get_months(df):
    df["Month"] = pd.to_datetime(df["Date_Time"]).dt.month  # convert "Date_Time" to datetime and add to "Month" series
    return df


def convert_to_season(month):
    if month in [12,1,2]:
        return "Winter"
    elif month in [3,4,5]:
        return "Spring"
    elif month in [6,7,8]:
        return "Summer"
    elif month in [9,10,11]:
        return "Autumn"


def month_temp_statistics(df):
    month_temp_statistic_df = df.groupby("Month")["Temperature_C"].agg(
        Mean_temp_c = "mean",
        Min_temp_c = "min",
        Max_temp_c = "max"
    ).reset_index()
    
    return month_temp_statistic_df


def season_temp_statistic(df):
    season_temp_statistic_df = df.groupby("Season")["Temperature_C"].agg(
        Mean_temp_C = "mean",
        Max_temp_C = "max",
        Min_temp_C = "min"
    ).reset_index()
    return season_temp_statistic_df


def summry_statistic(df):
    df.drop(columns= ["Month"], inplace = True)
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
    plt.xticks(fontsize=7)

    plt.show()


