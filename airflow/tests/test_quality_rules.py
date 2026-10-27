import sys
import os
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from airflow.include.quality import validate_records_batch


def test_quality_rules_valid_records():
    """Verifica que registros conformes sean marcados como VALID con score 100%."""
    valid_batch = [
        {
            "id": "ci41353455",
            "mag": 2.4,
            "place": "Anza, CA",
            "time": datetime.now(timezone.utc),
            "longitude": -116.45,
            "latitude": 33.55,
            "depth_km": 11.2,
        },
        {
            "id": "us6000tyxk",
            "mag": 6.1,
            "place": "Japan Region",
            "time": datetime.now(timezone.utc),
            "longitude": 140.2,
            "latitude": 35.8,
            "depth_km": 40.0,
        },
    ]

    valid, invalid, score, summary = validate_records_batch(valid_batch)
    assert len(valid) == 2
    assert len(invalid) == 0
    assert score == 100.0
    assert valid[0]["processing_status"] == "VALID"


def test_quality_rules_invalid_records_separation():
    """
    Verifica que registros que violan límites geográficos o de magnitud sean marcados como INVALID,
    con detalle del motivo y sin romper la ejecución del lote.
    """
    mixed_batch = [
        # Conforme
        {
            "id": "good_event_01",
            "mag": 3.0,
            "place": "Valid Zone",
            "time": datetime.now(timezone.utc),
            "longitude": -70.0,
            "latitude": -33.0,
            "depth_km": 25.0,
        },
        # No conforme: Latitud > 90, Magnitud absurda, Profundidad negativa extrema
        {
            "id": "bad_event_02",
            "mag": 15.0,  # fuera de [-2, 10]
            "place": "Corrupt Zone",
            "time": datetime.now(timezone.utc),
            "longitude": 210.0,  # fuera de [-180, 180]
            "latitude": 115.0,  # fuera de [-90, 90]
            "depth_km": -50.0,  # fuera de [-10, 1000]
        },
    ]

    valid, invalid, score, summary = validate_records_batch(mixed_batch)
    assert len(valid) == 1
    assert len(invalid) == 1
    assert score == 50.0

    bad_rec = invalid[0]
    assert bad_rec["processing_status"] == "INVALID"
    assert "fuera del rango" in bad_rec["validation_error"].lower() or "fuera de rango" in bad_rec["validation_error"].lower()
    assert len(bad_rec["failed_rules"]) >= 2
