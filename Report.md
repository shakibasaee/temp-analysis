Tehran weather data analysis report

Introduction:
In this project, daily temperature data from Tehran were analyzed to identify seasonal and monthly patterns.

## Summery statidtics:

Average temperature: 19.02 degrees
Max temperature: 37.9 degrees
Min temperature: -6.0 degrees

## Monthly analysis:

According to the bar chart, July was the hottest month with an average of 32.32 degrees, while December was the coldest month with an average of 5.42 degrees.

## Seasonal analysis:

In the pie chart, it can be seen the summer has highest share of the year's heat (average 31.26 degrees), while winter has the lowest (average 7.15 degrees).

## Result:

This analysis shows that Tehran has high temperature fluctions throughout the year. These insights can be used for energy, argicultural, or tourism planning.

## Linear Regression Results

MAE = 7.764
RMSE = 8.555
R² = -3.729
The linear regression model was trained on an 80/20 time‑based split (no shuffling) to preserve temporal order. The evaluation on the test set produced:

        MAE = 7.764°C: On average, predictions are off by about 7.8 degrees.

        RMSE = 8.555°C: Larger errors are penalized; the spread is wide.

        R² = -3.729: This negative value means the model performs worse than simply predicting the mean temperature – a sign that the current features (day of year, year, city) are insufficient to capture the actual temperature patterns, especially when the test data comes from a later period.

    These results serve as a baseline. Future work (by Karwan) will focus on feature engineering (e.g., lag variables, seasonal decomposition, weather factors) and possibly more advanced models to improve predictive power.
