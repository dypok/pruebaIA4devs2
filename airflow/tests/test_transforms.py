import sys
import os
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from airflow.include.transforms import transform_geojson_feature, sanitize_text


def test_sanitize_text():
    """Valida la sanitización de textos contra caracteres de control e inyección."""
    raw = "23 km ESE of Anza, CA `<script>alert(1)</script>`\n\t"
    cleaned = sanitize_text(raw)
    assert "<" not in cleaned
    assert ">" not in cleaned
    assert "`" not in cleaned
    assert "Anza, CA" in cleaned


def test_transform_geojson_feature_structure():
    """Valida la transformación pura de un Feature de GeoJSON a formato columnar."""
    sample_feature = {
        "type": "Feature",
        "properties": {
            "mag": 3.75,
            "place": "15 km SSW of Volcano, Hawaii",
            "time": 1793099398000,
            "updated": 1793099600000,
            "tsunami": 0,
            "sig": 215,
            "status": "reviewed",
            "magType": "ml",
        },
        "geometry": {
            "type": "Point",
            "coordinates": [-155.28, 19.31, 8.5],
        },
        "id": "hv74019200",
    }

    result = transform_geojson_feature(sample_feature)

    assert result["id"] == "hv74019200"
    assert result["mag"] == 3.75
    assert result["longitude"] == -155.28
    assert result["latitude"] == 19.31
    assert result["depth_km"] == 8.5
    assert result["place"] == "15 km SSW of Volcano, Hawaii"
    assert isinstance(result["time"], datetime)
    assert result["year"] == result["time"].year
    assert result["month"] == result["time"].month
