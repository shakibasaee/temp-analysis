import os
import logging
from typing import Optional, Dict

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from data_cleaning import get_clean_data

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class OutlierDetector:
    """Detects outliers using IQR or Z-score and can save plots per city."""

    def __init__(self, df: pd.DataFrame, threshold: float = 3.0):
        self.df = df
        self.threshold = threshold
        self.df.columns = self.df.columns.str.lower()

    def _iqr(self, df: pd.DataFrame, column: str) -> pd.DataFrame:
        q1, q3 = df[column].quantile([0.25, 0.75])
        iqr = q3 - q1
        lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        return df[(df[column] < lower) | (df[column] > upper)]

    def _zscore(self, df: pd.DataFrame, column: str, threshold: Optional[float] = None) -> pd.DataFrame:
        threshold = threshold or self.threshold
        z_scores = (df[column] - df[column].mean()) / df[column].std()
        return df[z_scores.abs() > threshold]

    def detect_per_city(self, column: str, method: str = "iqr", threshold: Optional[float] = None) -> Dict[str, pd.DataFrame]:
        if "city" not in self.df.columns:
            logging.warning("Column 'city' does not exist. Skipping per-city detection.")
            return {}
        results = {}
        for city, group in self.df.groupby("city"):
            if method.lower() == "iqr":
                results[city] = self._iqr(group, column)
            elif method.lower() == "zscore":
                results[city] = self._zscore(group, column, threshold)
            else:
                raise ValueError(f"Unknown method: {method}")
        return results

    def save_all_city_outlier_plots(self, column: str, output_dir: str):
        """Save IQR and Z-score plots for each city in output_dir."""
        if "city" not in self.df.columns:
            logging.warning("Column 'city' not found. Skipping plots.")
            return

        os.makedirs(output_dir, exist_ok=True)

        for city, group in self.df.groupby("city"):
            # Plot IQR
            plt.figure(figsize=(10, 5))
            sns.boxplot(y=group[column])
            plt.title(f"IQR Outliers - {city}")
            iqr_file = os.path.join(output_dir, f"{city}_iqr.png")
            plt.savefig(iqr_file, bbox_inches="tight")
            plt.close()
            logging.info(f"IQR plot saved: {iqr_file}")

            # Plot Z-score
            z_outliers = self._zscore(group, column)
            plt.figure(figsize=(10, 5))
            plt.scatter(group.index, group[column], label="Data")
            plt.scatter(z_outliers.index, z_outliers[column], color="red", label="Outliers")
            plt.title(f"Z-score Outliers - {city}")
            plt.legend()
            z_file = os.path.join(output_dir, f"{city}_zscore.png")
            plt.savefig(z_file, bbox_inches="tight")
            plt.close()
            logging.info(f"Z-score plot saved: {z_file}")


if __name__ == "__main__":
    df = get_clean_data("data/new_weather_data.csv")
    detector = OutlierDetector(df, threshold=2.5)

    plots_folder = r"C:\Users\Nitro 5\Documents\GitHub\temp-analysis\scripts\processing_data\plots"
    detector.save_all_city_outlier_plots("temperature_c", plots_folder)

    # Optional: Print summary counts
    iqr_outliers = detector.detect_per_city("temperature_c", method="iqr")
    zscore_outliers = detector.detect_per_city("temperature_c", method="zscore")

    print("--- IQR Outliers ---")
    for city, out in iqr_outliers.items():
        print(f"{city}: {len(out)}")

    print("\n--- Z-score Outliers ---")
    for city, out in zscore_outliers.items():
        print(f"{city}: {len(out)}")
