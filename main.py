import pandas as pd

missing_values = ["na","n.a","n.a.","NA",0,0.0]
df = pd.read_csv("C:\our customs\code\Python\wheater analyis\WeatherData.csv", na_values= missing_values)
df.dropna(axis= 0, inplace= True, how="any")
df_unvalid = df[(df["Humidity_pct"]<0)|
                (df["Humidity_pct"]>100)|
                (df["Temperature_C"]>60)|
                (df["Temperature_C"]<-90)|
                (df["Precipitation_mm"]<0)|
                (df["Precipitation_mm"]>500)|
                (df["Wind_Speed_kmh"]<0)|
                (df["Wind_Speed_kmh"]>250)
                ]
df = df.drop(df_unvalid.index)
print(df)
print(f"\nSummary of statistics:\n{df.describe()}")