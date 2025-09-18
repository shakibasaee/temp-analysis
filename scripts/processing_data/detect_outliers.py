import os
import logging
from typing import Optional
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
from .data_cleaning import get_clean_data

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def clean_column_name(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


class WeatherOutlierAnalyzer:
    def __init__(
        self, df: pd.DataFrame, z_threshold: float = 3.0, contamination: float = 0.05
    ):
        self.df = df.copy()
        self.df.columns = [clean_column_name(c) for c in self.df.columns]
        self.z_threshold = z_threshold
        self.contamination = contamination
        self.results_df: Optional[pd.DataFrame] = None

    def _iqr_outliers(self, series: pd.Series) -> pd.Index:
        q1, q3 = np.percentile(series, [25, 75])
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        return series.index[(series < lower) | (series > upper)]

    def _zscore_outliers(self, series: pd.Series) -> pd.Index:
        mean, std = series.mean(), series.std()
        z_scores = (series - mean) / std
        return series.index[np.abs(z_scores) > self.z_threshold]

    def _isolation_forest_outliers(self, series: pd.Series) -> pd.Index:
        model = IsolationForest(contamination=self.contamination, random_state=42)
        preds = model.fit_predict(series.values.reshape(-1, 1))
        return series.index[preds == -1]

    def analyze(self, column: str) -> pd.DataFrame:
        column = clean_column_name(column)
        if column not in self.df.columns:
            raise KeyError(
                f"Column '{column}' not found. Available: {list(self.df.columns)}"
            )

        series = self.df[column]

        iqr_idx = self._iqr_outliers(series)
        z_idx = self._zscore_outliers(series)
        iso_idx = self._isolation_forest_outliers(series)

        comp_df = pd.DataFrame(
            {column: series, "IQR": 0, "Zscore": 0, "IsolationForest": 0}
        )

        comp_df.loc[iqr_idx, "IQR"] = 1
        comp_df.loc[z_idx, "Zscore"] = 1
        comp_df.loc[iso_idx, "IsolationForest"] = 1

        self.results_df = comp_df

        logging.info(
            f"Outlier counts → IQR: {len(iqr_idx)}, Z-score: {len(z_idx)}, IsolationForest: {len(iso_idx)}"
        )
        logging.info(
            f"Overlaps → IQR∩Z: {len(set(iqr_idx) & set(z_idx))}, "
            f"IQR∩ML: {len(set(iqr_idx) & set(iso_idx))}, "
            f"Z∩ML: {len(set(z_idx) & set(iso_idx))}"
        )

        return comp_df

    def plot_outliers(self, column: str, output_dir: str, city: Optional[str] = None):
        if self.results_df is None:
            raise RuntimeError("Please run analyze() first.")

        os.makedirs(output_dir, exist_ok=True)

        column = clean_column_name(column)
        df_plot = self.results_df.copy()
        if city and "city" in self.df.columns:
            df_plot = df_plot[self.df["city"] == city]

        plt.figure(figsize=(12, 6))
        plt.scatter(
            df_plot.index, df_plot[column], color="blue", label="Data", alpha=0.2, s=15
        )

        plt.scatter(
            df_plot.index[df_plot["IQR"] == 1],
            df_plot[column][df_plot["IQR"] == 1],
            color="green",
            label="IQR Outliers",
            s=80,
            alpha=0.9,
        )

        plt.scatter(
            df_plot.index[df_plot["Zscore"] == 1],
            df_plot[column][df_plot["Zscore"] == 1],
            color="orange",
            label="Z-score Outliers",
            s=80,
            alpha=0.9,
        )

        plt.scatter(
            df_plot.index[df_plot["IsolationForest"] == 1],
            df_plot[column][df_plot["IsolationForest"] == 1],
            color="red",
            label="IsolationForest Outliers",
            s=50,
            alpha=0.3,
        )

        plt.title(f"Outlier Analysis - {city if city else 'All Data'}")
        plt.xlabel("Index")
        plt.ylabel(column)
        plt.legend()
        fname = f"outliers_{city if city else 'all'}.png"
        plt.savefig(os.path.join(output_dir, fname), bbox_inches="tight")
        plt.close()
        logging.info(f"Plot saved: {fname}")


if __name__ == "__main__":
    df = get_clean_data("data/new_weather_data.csv")
    analyzer = WeatherOutlierAnalyzer(df, z_threshold=2.5, contamination=0.05)

    comparison_df = analyzer.analyze("Temperature_C")
    print("\n--- Comparison of Outliers ---")
    print(comparison_df.head(15))

    plots_dir = r"C:\Users\Nitro 5\Documents\GitHub\temp-analysis\plots"
    analyzer.plot_outliers("Temperature_C", plots_dir)
