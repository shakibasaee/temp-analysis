# Temp-Analysis

A clean and modular toolkit for analyzing and visualizing temperature data.

## Overview

Temp-Analysis started as an exploratory project for computing and visualizing monthly temperature statistics. It has since evolved into a structured and maintainable pipeline, designed with modularity and reusability in mind.

### This project allows you to:

- Calculate monthly temperature statistics (mean, min, max)
- Generate bar plots using a clean "ggplot" style
- Save plots automatically with proper directory handling
- Extend and maintain the codebase with ease

## Features

- Monthly descriptive statistics from raw CSV temperature data
- Visual output via bar plots of average monthly temperatures
- Automatic creation of output directories to prevent save errors
- Modular structure separating analysis, visualization, and cleaning logic
- Option to either save plots or display them interactively

## Project Structure

temp-analysis/
├── scripts/
│ ├── analysis.py # Statistical computations
│ ├── visualization/
│ │ └── plots.py # Plotting functions
│ │ └── figures/ # Output directory for saved plots
| ├── data_cleaning.py # Data cleaning functions
│ └── main.py # Script entry point
├── data/ # Input data files
├── requirements.txt # Python package dependencies
└── README.md

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/shakibasaee/temp-analysis.git
   cd temp-analysis

    (Optional) Create and activate a virtual environment:
   ```

python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate

Install the required packages:

    pip install -r requirements.txt

Usage

To run the program and generate the monthly temperature statistics and plots:

python scripts/main.py

This script will:

    Load and clean the temperature dataset

    Calculate monthly temperature averages

    Save a bar plot of the average monthly temperatures in the figures/ directory

You can also choose whether to save or display the plot by setting the save parameter in the months_plot() function.
Example Output

(Add plot image here if available)
Example plot path: figures/monthly_avg_temperature.png
Roadmap

    Support for additional plot types (line charts, heatmaps, etc.)

    More flexible data input handling (e.g., JSON, APIs)

    Automated summary reporting

    Improved documentation and unit tests

Contributing

Contributions are welcome. Please submit a pull request or open an issue to suggest improvements or report bugs. Make sure to follow the repository’s contribution guidelines.
Authors

    Shakiba

    Kasra

License

This project is licensed under the MIT License. See the LICENSE file for details
