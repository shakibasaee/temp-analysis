import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def main():
    csv_path = Path(__file__).resolve().parents[1] / "data" / "new_weather_data.csv"
    df = pd.read_csv(csv_path)

    print("CSV:", csv_path)
    print("shape:", df.shape)
    print("columns:", df.columns.tolist())
    print()

    # basic cleaning
    df["Date_Time"] = pd.to_datetime(df["Date_Time"], errors="coerce")
    df["City"] = df["City"].astype(str).str.strip()

    # sanity checks
    print("---- Missing values ----")
    print(df.isna().sum())
    print()

    print("---- Date range ----")
    print("min:", df["Date_Time"].min(), "max:", df["Date_Time"].max())
    print()

    print("---- Cities ----")
    cities = sorted(df["City"].dropna().unique())
    print("count:", len(cities))
    print("cities:", cities)
    print()

    print("---- Per-city min/max Temperature_C ----")
    for city in cities:
        sub = df[df["City"] == city].copy()
        sub = sub.dropna(subset=["Date_Time", "Temperature_C"])
        sub = sub.sort_values("Date_Time")

        if sub.empty:
            print(city, "-> NO DATA after cleaning")
            continue

        i_min = sub["Temperature_C"].idxmin()
        i_max = sub["Temperature_C"].idxmax()

        tmin = sub.loc[i_min, "Temperature_C"]
        dmin = sub.loc[i_min, "Date_Time"]
        tmax = sub.loc[i_max, "Temperature_C"]
        dmax = sub.loc[i_max, "Date_Time"]

        is_sorted = sub["Date_Time"].is_monotonic_increasing

        dup_count = sub.duplicated(subset=["Date_Time"]).sum()

        print(
            f"{city:15} | rows={len(sub):4} | "
            f"min={tmin:7.2f} @ {dmin.date()} | "
            f"max={tmax:7.2f} @ {dmax.date()} | "
            f"sorted={is_sorted} | dups(Date_Time)={dup_count}"
        )

    print()

    print("---- Plot test ----")
    # 1) one plot per city
    for city in cities:
        sub = df[df["City"] == city].dropna(subset=["Date_Time", "Temperature_C"]).copy()
        sub = sub.sort_values("Date_Time")

        if sub.empty:
            continue

        plt.figure(figsize=(10, 4))
        plt.plot(sub["Date_Time"], sub["Temperature_C"])
        plt.title(f"Temperature over time - {city}")
        plt.xlabel("Date_Time")
        plt.ylabel("Temperature_C")
        plt.tight_layout()
        plt.show()

    print("Done.")

if __name__ == "__main__":
    main()
