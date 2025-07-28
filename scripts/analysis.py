import pandas as pd
from main import df

def get_months():
    df["Month"] = (pd.to_datetime(df["Date_Time"]).dt.month)        # convert "Date_Time" to datetime and add to "Month" series

get_months()

def conver_to_season(month):
    if month in [12,1,2]:
        return "Winter"
    elif month in [3,4,5]:
        return "Spring"
    elif month in [6,7,8]:
        return "Summer"
    elif month in [9,10,11]:
        return "Fall"
    
def get_season():
    df["Season"] = df["Month"].apply(conver_to_season)
    # print(df)

    print (print(df["Month"].value_counts().sort_index()))    
    print (print(df["Season"].value_counts())
)

get_season()

# def month_season_temprature_statistics():
#     temperature_mean = df.groupby(["Month", "Season"])["Temperature_C"].mean().reset_index()
#     temperature_max = df["Temperature_C"].max()
#     temperature_min = df["Temperature_C"].min()
#     return temperature_mean

# print(month_season_temprature_statistics())

# def summry_statistic():
#     print(f"\nSummary of statistics:\n{df.drop(columns= ["Month"]).describe()}")

# summry_statistic()