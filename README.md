# Temperature Analysis Platform

A modular data analysis toolkit for exploring, visualizing, and forecasting temperature data across multiple cities and years.

The platform focuses on **clarity, extensibility, and honest baselines**: upload CSV datasets, explore trends in an interactive Streamlit dashboard, detect anomalies, and generate short-horizon forecasts using a transparent baseline model. Results can be exported as shareable PDF reports.

---

## 🚀 Features

- Dynamic CSV dataset upload
- Multi-city and multi-year analysis
- Date-range filtering
- Temperature forecasting using **Linear Regression as a simple, interpretable baseline**
- Outlier / anomaly detection (statistical methods)
- Interactive Streamlit dashboard
- PDF report generation
- Optional live weather data integration (API-based)
- Centralized configuration via `config.yaml`
- Modular, scalable code structure
- Unit testing with PyTest

---

## 🔧 Tech Stack

- **Language:** Python
- **Data Processing:** pandas, NumPy, scikit-learn
- **Visualization:** Matplotlib, Seaborn
- **UI / Frontend:** Streamlit
- **Reporting:** ReportLab (PDF generation)
- **API Integration (optional):** OpenWeather API
- **Database (optional / planned):** SQLite, PostgreSQL
- **Testing:** PyTest

---

## 📂 Project Structure

```bash
project/
├── README.md
├── requirements.txt
├── config.yaml
├── data/
├── scripts/
│   ├── app.py            # Streamlit dashboard entry point
│   ├── main.py           # Core orchestration logic
│   ├── processing_data/  # Data loading & preprocessing
│   └── visualization/    # Plotting and chart utilities
├── plots/
└── tests/
```

---

## 📊 Dashboard Overview

The Streamlit dashboard allows you to:

- Upload CSV datasets
- Filter data by city and date range
- Explore interactive temperature trend visualizations
- Detect anomalies and outliers
- Generate short-term forecasts using a Linear Regression baseline
- Compare historical CSV data with live weather data (optional)
- Export the current analysis and plots as a PDF report

---

## 📁 Data Format

The platform expects CSV files with at least the following columns:

- `date` — date or datetime (e.g. `YYYY-MM-DD`)
- `city` — city name (string)
- `temperature` — numeric temperature value (°C or °F; configurable)

**Example:**

```csv
date,city,temperature
2023-01-01,Berlin,3.5
2023-01-02,Berlin,2.1
2023-01-01,Paris,5.2
```

Additional features (e.g. `humidity`, `wind_speed`) can be added as long as they are handled in the preprocessing pipeline.

---

## ⚙️ Configuration (`config.yaml`)

Key settings are centralized in `config.yaml`, allowing behavior changes without modifying code:

- Default temperature unit (C / F)
- Forecast horizon (days ahead)
- Outlier detection thresholds
- Data and output paths
- API configuration
- Database configuration (if enabled)

**Example:**

```yaml
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
```

---

## 🔑 API Integration (Optional)

Live weather data integration is **optional and disabled by default**.

When enabled, the dashboard can fetch and compare live weather data against historical CSV-based datasets.

**Steps:**

1. Create an account on OpenWeather and generate an API key.
2. Set the API key in `config.yaml` or as an environment variable:

```bash
export OPENWEATHER_API_KEY="your_real_key_here"
```

3. Enable API integration in `config.yaml`:

```yaml
api:
  enabled: true
```

---

## 📦 Installation & Setup

### 1️⃣ Clone the repository

```bash
git clone https://github.com/shakibasaee/temp-analysis.git
cd temp-analysis
```

### 2️⃣ Create and activate a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Run the dashboard

```bash
streamlit run scripts/app.py
```

Then open the URL printed by Streamlit (usually `http://localhost:8501`).

---

## 🚀 Quickstart Workflow

1. Upload a CSV file containing temperature data.
2. Select one or more cities and a date range.
3. Explore charts showing trends and seasonal patterns.
4. Run anomaly detection to highlight outliers.
5. Generate a forecast for the next _N_ days (configurable).
6. Export the analysis and visualizations as a PDF report.

---

## 🧠 Methodology

The system is designed with **modularity and testability** in mind:

- Each major responsibility (data loading, preprocessing, forecasting, visualization, reporting) lives in its own module.
- Forecasting currently relies on a **Linear Regression baseline**, chosen for its simplicity and interpretability.
- This baseline provides a clear reference point for evaluating more advanced models in future iterations.
- Outlier detection uses statistical techniques such as z-scores or IQR-based rules.
- Configuration is centralized in `config.yaml` to allow rapid experimentation.

The forecasting backend can be replaced (e.g. Prophet, LSTM) while reusing the existing data and visualization pipeline.

---

## ✅ Running Tests

Run the full test suite:

```bash
pytest
```

Run tests for a specific module:

```bash
pytest tests/test_forecasting.py
```

---

## ✨ Roadmap / Future Improvements

- Advanced forecasting models (e.g. Prophet, LSTM)
- Deployment to Streamlit Community Cloud or similar platforms
- CI/CD pipeline (linting, testing, automated deployment)
- Caching and rate limiting for API calls
- More advanced analytics dashboards (correlations, climatology metrics)
- Role-based access and multi-user workspaces

---

## 👨‍💻 Authors & Collaboration

This project was developed by a **two-person team with rotating roles** throughout different phases of development.
Both contributors participated in system design, implementation, experimentation, and review, with responsibilities shifting as the project evolved.

- **Shakiba**
  GitHub: [https://github.com/shakibasaee](https://github.com/shakibasaee)

- **Kasra**
  GitHub: [https://github.com/kasra-2004](https://github.com/kasra-2004)

This role-rotating workflow encouraged shared ownership of the codebase and a deeper understanding of the system as a whole.

---

## 📜 License

This project is licensed under the **MIT License**.
You are free to use, modify, and distribute it for personal or commercial purposes.
