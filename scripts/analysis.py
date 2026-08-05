from matplotlib import pyplot as plt
import pandas as pd
try:
    from .model_config import DEFAULT_CONFIG, LinearRegressionConfig
    from .models.linear_regression import LinearRegressionModel
except ImportError:
    from model_config import DEFAULT_CONFIG, LinearRegressionConfig
    from models.linear_regression import LinearRegressionModel


def get_months(df):
    df["Month"] = pd.to_datetime(df["Date_Time"]).dt.month
    return df


def convert_to_season(month):
    if month in [12, 1, 2]:
        return "Winter"
    elif month in [3, 4, 5]:
        return "Spring"
    elif month in [6, 7, 8]:
        return "Summer"
    elif month in [9, 10, 11]:
        return "Autumn"
    else:
        return "Unknown"


def month_temp_statistics(df):
    return (
        df.groupby("Month")["Temperature_C"]
        .agg(Mean_temp_c="mean", Min_temp_c="min", Max_temp_c="max")
        .reset_index()
    )


def season_temp_statistic(df):
    return (
        df.groupby("Season")["Temperature_C"]
        .agg(Mean_temp_C="mean", Max_temp_C="max", Min_temp_C="min")
        .reset_index()
    )


def summry_statistic(df):
    summry_df = df.drop(columns=["Month"])
    return summry_df.describe()


def regression_alg(
    df, config: LinearRegressionConfig | None = None
):
    """Train and evaluate the reusable linear-regression baseline.

    The tuple return is retained for compatibility with existing callers. The
    first item is now a ``LinearRegressionModel`` and the second contains the
    fitted pipeline's generated feature names.
    """
    model = LinearRegressionModel(config or DEFAULT_CONFIG)
    metrics = model.fit_evaluate(df, refit_full=True)
    print(
        f"MAE={metrics['mae']:.3f} "
        f"RMSE={metrics['rmse']:.3f} "
        f"R2={metrics['r2']:.3f}"
    )
    return model, model.feature_names_


def get_date(df):
    df["Date_Time"] = pd.to_datetime(df["Date_Time"])
    df["Date"] = df["Date_Time"].dt.date

    daily_avg = df.groupby("Date")["Temperature_C"].mean()

    fig, ax = plt.subplots(figsize=(10, 6))
    daily_avg.plot(kind="bar", ax=ax, color="purple")
    ax.set_title("Daily Average Temperature")
    ax.set_xlabel("Date")
    ax.set_ylabel("Temperature (°C)")
    ax.grid(True)
    plt.style.use("ggplot")
    plt.tight_layout()
    return fig


def months_plot(df):
    stats = month_temp_statistics(df)
    stats.set_index("Month", inplace=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    stats["Mean_temp_c"].plot(kind="bar", ax=ax, color="red")
    ax.set_title("Average Monthly Temperature")
    ax.set_xlabel("Month")
    ax.set_ylabel("Mean Temperature (°C)")
    ax.grid(True)
    plt.style.use("ggplot")
    return fig


def season_plot(df):
    stats = season_temp_statistic(df)
    stats.set_index("Season", inplace=True)

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.pie(
        stats["Mean_temp_C"],
        labels=stats.index,
        autopct="%1.1f%%",
        startangle=90,
        colors=["#ff9999", "#66b3ff", "#99ff99", "#ffcc99"],
    )
    ax.set_title("Average Seasonal Temperature")
    ax.axis("equal")
    plt.tight_layout()
    return fig



def reg_plot(df, result_pred_df, cities):
    if isinstance(cities, str):
        cities = [cities]

    df = df.copy()
    df["Date_Time"] = pd.to_datetime(df["Date_Time"])
    df = df.sort_values("Date_Time")

    fig, ax = plt.subplots(figsize=(10, 6))

    for city in cities:
        sub = df[df["City"] == city].sort_values("Date_Time")
        if sub.empty:
            continue
        ax.plot(sub["Date_Time"], sub["Temperature_C"], label=f"Actual - {city}")

    if "City" in result_pred_df.columns:
        for city in cities:
            psub = result_pred_df[result_pred_df["City"] == city]
            if psub.empty:
                continue
            ax.scatter(
                psub["Date"],
                psub["Predicted_Temprature"],
                marker="o",
                s=120,
                label=f"Predicted - {city}",
            )
        pred_date = pd.to_datetime(result_pred_df["Date"].iloc[0]).date()
    else:
        # fallback if City wasn't attached
        ax.scatter(result_pred_df["Date"], result_pred_df["Predicted_Temprature"],
                   marker="o", s=120, label="Predicted")
        pred_date = pd.to_datetime(result_pred_df["Date"].iloc[0]).date()

    ax.set_title(f"Predicted Temperature on {pred_date}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Temperature (°C)")
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.7)

    return fig
