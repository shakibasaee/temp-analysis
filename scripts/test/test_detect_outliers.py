import pandas as pd
import pytest 
from processing_data.detect_outliers import OutlierDetector


def test__init__():
    df = pd.DataFrame({
        "City": ["Tehran", "Tehran"],
        "Temprature_C": [10, 20]
    })

    detector = OutlierDetector(df, threshold=2.5)

    assert detector.threshold == 2.5
    assert "city" in detector.df.columns
    assert "temprature_c" in detector.df.columns