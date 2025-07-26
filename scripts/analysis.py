import pandas as pd
from main import df
# from data_cleaning import df

# def get_df_from_data_cleaning():
#     df = validate_data()
#     return df
# df = get_df_from_data_cleaning()

def get_months():
    df["Month"] = (pd.to_datetime(df["Date_Time"]).dt.month)        # convert "Date_Time" to datetime and add to "Month" series

get_months()

def conver_to_season(month):
    if month in [12,1,2]:
        return "Spring"
    elif month in [3,4,5]:
        return "Summer"
    elif month in [6,7,8]:
        return "Full"
    elif month in [9,10,11]:
        return "Winter"
    
def get_season():
    df["Season"] = df["Month"].apply(conver_to_season)
    print(df)

get_season()

def summry_statistic():
    df.drop(columns= ["Month"], inplace = True)
    print(f"\nSummary of statistics:\n{df.describe()}")

summry_statistic()