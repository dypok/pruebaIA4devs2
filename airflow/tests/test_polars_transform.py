import io
import pytest
import polars as pl
from unittest.mock import MagicMock, patch

from airflow.include.polars_transform import process_features_to_layers, write_parquet_to_minio

SAMPLE_FEATURE = {
    "type": "Feature",
    "id": "test_polars_01",
    "properties": {
        "mag": 4.5,
        "place": "10 km S of Ridgecrest, CA",
        "time": 1729000000000,
        "updated": 1729001000000,
        "tsunami": 0,
        "sig": 312,
        "status": "reviewed",
        "magType": "mw",
    },
    "geometry": {
        "type": "Point",
        "coordinates": [-117.65, 35.62, 8.4],
    },
}


def test_polars_process_features_to_layers():
    """Verifica que process_features_to_layers con Polars procese correctamente features válidas."""
    features = [SAMPLE_FEATURE]
    valid, invalid, score, summary = process_features_to_layers(features)

    assert len(valid) == 1
    assert len(invalid) == 0
    assert score == 100.0
    assert valid[0]["id"] == "test_polars_01"
    assert valid[0]["mag"] == 4.5
    assert valid[0]["processing_status"] == "VALID"


def test_polars_write_parquet_buffer():
    """Verifica que Polars serialice registros a Parquet con compresión Snappy sin errores."""
    records = [
        {
            "id": "us100",
            "mag": 5.2,
            "place": "Off coast of Chile",
            "time": "2026-10-27T08:00:00Z",
            "longitude": -71.5,
            "latitude": -33.0,
            "depth_km": 25.0,
            "tsunami": 0,
            "sig": 415,
            "status": "reviewed",
            "mag_type": "mww",
            "processing_status": "VALID",
        }
    ]

    mock_s3 = MagicMock()
    with patch("airflow.include.polars_transform.get_s3_client", return_value=mock_s3), \
         patch("airflow.include.polars_transform.ensure_bucket", return_value=True):
        
        success = write_parquet_to_minio(records, "gold/test.snappy.parquet", "sismowatch-lake")
        assert success is True
        assert mock_s3.put_object.called

        # Inspeccionar el payload enviado a S3
        call_kwargs = mock_s3.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "sismowatch-lake"
        assert call_kwargs["Key"] == "gold/test.snappy.parquet"
        assert call_kwargs["ContentType"] == "application/x-parquet"

        # Verificar que el buffer es un archivo Parquet válido legible por Polars
        raw_bytes = call_kwargs["Body"]
        read_df = pl.read_parquet(io.BytesIO(raw_bytes))
        assert read_df.shape == (1, 12)
        assert read_df["id"][0] == "us100"
        assert read_df["mag"][0] == 5.2
