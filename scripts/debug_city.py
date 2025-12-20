import pandas as pd
from pathlib import Path

csv_path = Path(__file__).resolve().parents[1] / "data" / "new_weather_data.csv"
df = pd.read_csv(csv_path)

print("CSV:", csv_path)
print("shape:", df.shape)
print("columns:", df.columns.tolist())

s = df["City"].astype(str)

bad = df[s.str.strip() != s]
print("rows with leading/trailing spaces:", bad.shape[0])
print("examples:", bad["City"].head(20).tolist())

print("unique before:", s.nunique())
print("unique after:", s.str.strip().nunique())
print("cities:", sorted(s.str.strip().unique())[:50])
