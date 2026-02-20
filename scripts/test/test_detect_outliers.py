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



def test_iqr_no_outlier():
    df = pd.DataFrame({
        "Temprature_C": [10,11,12,13,14,15]
    })

    detector = OutlierDetector(df)
    outliers = detector._iqr(df , "temprature_c")

    assert outliers.empty


def test_iqr_with_outlier():
    df = pd.DataFrame({
        "Temprature_C": [10,11,12,13,14,100]
    })

    detector = OutlierDetector(df)
    outliers = detector._iqr(df, "temprature_c")

    assert len(outliers) == 1
    assert outliers.iloc[0]["temprature_c"] == 100


def test_zscore_no_outliers():
    df = pd.DataFrame({
        "Temprature_C": [10,11,12,13,14]
    })

    detector = OutlierDetector(df)
    outliers = detector._zscore(df, "temprature_c")

    assert outliers.empty


def test_zscore_with_outliers():
    df = pd.DataFrame({
        "Temprature_C": [10,11,12,13,14,200]
    })

    detector = OutlierDetector(df, threshold=2)
    outliers = detector._zscore(df, "temprature_c")

    assert len(outliers) == 1
    assert outliers.iloc[0]["temprature_c"] == 200


def test_detect_per_city():
    df = pd.DataFrame({
        "City": ["Sanadaj", "Sanadaj", "Mashhad", "Mashhad", "Sanadaj", "Sanadaj", "Sanadaj"],
        "Temprature_C": [10, 100, 20, 21, 11, 12, 13]
    })

    detector = OutlierDetector(df, threshold=2)
    result = detector.detect_per_city("temprature_c", method="IQR")

    assert "Sanadaj" in result
    assert "Mashhad" in result
    assert len(result["Sanadaj"]) == 1
    assert result["Sanadaj"].iloc[0]["temprature_c"] == 100


def test_detect_per_city_without_city_column():
    df = pd.DataFrame({
        "Temprature_C": [10, 20, 30]
    })

    detector = OutlierDetector(df)
    result = detector.detect_per_city("temprature_c")

    assert result == {}


def test_detect_per_city_invalid_method():
    df = pd.DataFrame({
        "City": ["Sanandaj", "Mashhad"],
        "Temprature_C": [10,20]
    })

    detector= OutlierDetector(df)

    with pytest.raises(ValueError):
        detector.detect_per_city("temprature_c", method = "unknown")