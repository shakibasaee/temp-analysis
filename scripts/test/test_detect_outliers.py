import pandas as pd
import pytest

from processing_data.detect_outliers import OutlierDetector


def test_init_normalizes_columns_and_stores_threshold():
    source = pd.DataFrame(
        {
            "City": ["Tehran"],
            "Temperature_C": [10],
        }
    )

    detector = OutlierDetector(
        source,
        threshold=2.5,
    )

    assert detector.threshold == 2.5
    assert list(detector.df.columns) == [
        "city",
        "temperature_c",
    ]


def test_iqr_returns_empty_frame_when_there_are_no_outliers():
    source = pd.DataFrame(
        {
            "temperature_c": [
                10,
                11,
                12,
                13,
                14,
                15,
            ]
        }
    )

    detector = OutlierDetector(source)
    result = detector._iqr(
        source,
        "temperature_c",
    )

    assert result.empty


def test_iqr_returns_outlier():
    source = pd.DataFrame(
        {
            "temperature_c": [
                10,
                11,
                12,
                13,
                14,
                100,
            ]
        }
    )

    detector = OutlierDetector(source)
    result = detector._iqr(
        source,
        "temperature_c",
    )

    assert result["temperature_c"].tolist() == [100]


def test_zscore_returns_empty_frame_when_there_are_no_outliers():
    source = pd.DataFrame(
        {
            "temperature_c": [
                10,
                11,
                12,
                13,
                14,
            ]
        }
    )

    detector = OutlierDetector(source)
    result = detector._zscore(
        source,
        "temperature_c",
    )

    assert result.empty


def test_zscore_returns_outlier():
    source = pd.DataFrame(
        {
            "temperature_c": [
                10,
                11,
                12,
                13,
                14,
                200,
            ]
        }
    )

    detector = OutlierDetector(
        source,
        threshold=2,
    )
    result = detector._zscore(
        source,
        "temperature_c",
    )

    assert result["temperature_c"].tolist() == [200]


def test_detect_per_city_groups_results_by_city():
    source = pd.DataFrame(
        {
            "City": [
                "Sanandaj",
                "Sanandaj",
                "Sanandaj",
                "Sanandaj",
                "Sanandaj",
                "Mashhad",
                "Mashhad",
                "Mashhad",
                "Mashhad",
            ],
            "Temperature_C": [
                10,
                11,
                12,
                13,
                100,
                20,
                21,
                22,
                23,
            ],
        }
    )

    detector = OutlierDetector(source)
    result = detector.detect_per_city(
        "temperature_c",
        method="IQR",
    )

    assert set(result) == {
        "Sanandaj",
        "Mashhad",
    }
    assert result["Sanandaj"]["temperature_c"].tolist() == [100]
    assert result["Mashhad"].empty


def test_detect_per_city_returns_empty_dict_without_city_column():
    source = pd.DataFrame(
        {
            "Temperature_C": [
                10,
                20,
                30,
            ]
        }
    )

    detector = OutlierDetector(source)
    result = detector.detect_per_city("temperature_c")

    assert result == {}


def test_detect_per_city_rejects_unknown_method():
    source = pd.DataFrame(
        {
            "City": ["Sanandaj"],
            "Temperature_C": [10],
        }
    )

    detector = OutlierDetector(source)

    with pytest.raises(
        ValueError,
        match="Unknown method",
    ):
        detector.detect_per_city(
            "temperature_c",
            method="unknown",
        )


def test_save_plots_creates_two_files_per_city(tmp_path):
    source = pd.DataFrame(
        {
            "City": [
                "Sanandaj",
                "Sanandaj",
                "Mashhad",
                "Mashhad",
            ],
            "Temperature_C": [
                10,
                100,
                20,
                21,
            ],
        }
    )

    detector = OutlierDetector(source)
    detector.save_all_city_outlier_plots(
        column="temperature_c",
        output_dir=tmp_path,
    )

    created_files = {
        path.name
        for path in tmp_path.iterdir()
    }

    assert created_files == {
        "Mashhad_iqr.png",
        "Mashhad_zscore.png",
        "Sanandaj_iqr.png",
        "Sanandaj_zscore.png",
    }