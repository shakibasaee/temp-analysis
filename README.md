# Temperature Analysis Platform

A modular data analysis toolkit for exploring, visualizing, and forecasting temperature data across multiple cities and years.  

Use it to upload CSV datasets, detect anomalies, run machine learning–based forecasts, and explore results in an interactive Streamlit dashboard. You can also export reports as PDFs for sharing.

---

## 🚀 Features

- Dynamic CSV dataset upload
- Multi-city and multi-year support
- Date range filtering
- Temperature forecasting (Linear Regression)
- Outlier detection for anomaly identification
- Interactive Streamlit dashboard
- PDF report generation
- Optional integration with live weather data via API
- Configurable settings via `config.yaml`
- Modular code structure for scalability
- Unit testing with PyTest

---

## 🔧 Tech Stack

- **Language:** Python  
- **Data Processing:** pandas, NumPy, scikit-learn  
- **Visualization:** Matplotlib, Seaborn  
- **UI / Frontend:** Streamlit  
- **Reporting:** ReportLab (PDF generation)  
- **API Integration (optional):** OpenWeather API  
- **Database (optional):** SQLite / PostgreSQL  
- **Testing:** PyTest  

---

## 📂 Project Structure

```bash
project/
project/
├── README.md
├── requirements.txt
├── data/
├── scripts/
│   ├── app.py
│   ├── main.py
│   ├── processing_data/
│   └── visualization/
└── plots/


📊 Dashboard Overview
The Streamlit dashboard lets you:

Upload CSV datasets

Configure filters by date range and city

Explore interactive charts of temperature trends

Detect anomalies and outliers

Generate forecasts using a Linear Regression model

Compare historical CSV data with live weather data (optional API integration)

Export the current analysis and plots as a PDF report

📁 Data Format
The platform expects CSV files with at least the following columns:

date – date or datetime (e.g. YYYY-MM-DD)

city – city name (string)

temperature – numeric temperature value (°C or °F; see config)

Example:

csv
Copy code
date,city,temperature
2023-01-01,Berlin,3.5
2023-01-02,Berlin,2.1
2023-01-01,Paris,5.2
You can extend this with additional features (e.g. humidity, wind_speed); just ensure they are handled in preprocess.py.

⚙️ Configuration (config.yaml)
Key settings are managed in config.yaml, for example:

Default unit (C / F)

Forecast horizon (e.g. days ahead)

Outlier detection thresholds

Paths for data and output

API configuration (OpenWeather API key, base URL)

Database connection settings (if using SQLite/PostgreSQL)

Example snippet:

yaml
Copy code
units: "C"
forecast_horizon_days: 7
outlier:
  zscore_threshold: 3.0
api:
  enabled: false
  provider: "openweather"
  api_key: "YOUR_API_KEY_HERE"
database:
  enabled: false
  uri: "sqlite:///data/temperature.db"
🔑 API Integration (Optional)
To use live weather data:

Create an account on OpenWeather and generate an API key.

Set the API key in config.yaml or as an environment variable, e.g.:

bash
Copy code
export OPENWEATHER_API_KEY="your_real_key_here"
Enable API integration in config.yaml:

yaml
Copy code
api:
  enabled: true
When enabled, the dashboard can fetch and compare live weather data against your CSV historical data.

📦 Installation & Setup
1️⃣ Clone the repository
bash
Copy code
git clone https://github.com/shakibasaee/temp-analysis.git
cd temp-analysis
2️⃣ Create and activate a virtual environment (recommended)
bash
Copy code
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
3️⃣ Install dependencies
bash
Copy code
pip install -r requirements.txt
4️⃣ Run the dashboard
bash
Copy code
streamlit run app.py
Then open the URL that Streamlit prints in your terminal (usually http://localhost:8501).

🚀 Quickstart Workflow
Once the dashboard is running:

Upload a CSV with temperature data.

Select city/cities and a date range.

Explore charts showing trends and seasonality.

Run anomaly detection to highlight outliers.

Generate a forecast for the next N days (configurable).

Export results as PDF, including plots and key metrics.

🧠 Methodology
The system is designed with modularity and testability in mind:

Each component (data loading, preprocessing, forecasting, visualization, reporting) lives in its own module.

Forecasting currently uses a Linear Regression model as a baseline for temperature prediction.

Outlier detection uses statistical methods (e.g. z-scores or IQR-based rules; see outliers.py).

Configuration is centralized in config.yaml so behavior can be tuned without changing code.

Automated tests (PyTest) help ensure reliability of core data and model logic.

You can easily swap out the forecasting backend (e.g. replace Linear Regression with Prophet or an LSTM model) while reusing the existing data and visualization pipeline.

✅ Running Tests
Use PyTest to run the test suite:

bash
Copy code
pytest
You can also run tests for a specific module:

bash
Copy code
pytest tests/test_forecasting.py
✨ Roadmap / Future Improvements
Planned / potential enhancements:

Advanced forecasting models (e.g. LSTM, Prophet)

Deployment to Streamlit Community Cloud or other hosting platforms

Full CI/CD pipeline (linting, tests, deployment)

Real-time caching and rate limiting for API calls

More advanced dashboards (e.g. correlations, climatology metrics)

Role-based access and multi-user workspaces

👨‍💻 Contributing
Contributions are welcome!

Fork the repository.

Create a feature branch:

bash
Copy code
git checkout -b feature/my-new-thing
Make your changes and add tests where appropriate.

Commit with clear messages:

bash
Copy code
git commit -m "Add XYZ feature"
Open a pull request describing what you changed and why.

📜 License
This project is licensed under the MIT License.
You’re free to use it for personal and commercial projects.

🎯 Authors
Team of 2:

    Shakiba

    Kasra