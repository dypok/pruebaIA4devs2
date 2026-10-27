import io
import os
import logging
from typing import Dict, Any, List, Tuple
import polars as pl

try:
    from include.transforms import transform_geojson_feature
    from include.quality import validate_records_batch
    from include.minio_client import get_s3_client, ensure_bucket
except ImportError:
    from airflow.include.transforms import transform_geojson_feature
    from airflow.include.quality import validate_records_batch
    from airflow.include.minio_client import get_s3_client, ensure_bucket

logger = logging.getLogger(__name__)

BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "sismowatch-lake")


def process_features_to_layers(
    features: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], float, Dict[str, Any]]:
    """
    Procesa una lista de features GeoJSON:
    1. Desanida y sanitiza cada registro.
    2. Aplica validación declarativa de calidad (Pandera).
    3. Retorna: (valid_records, invalid_records, quality_score, summary)
    """
    if not features:
        return [], [], 100.0, {}

    transformed_records = []
    for feat in features:
        try:
            record = transform_geojson_feature(feat)
            transformed_records.append(record)
        except Exception as e:
            logger.error(f"Error transformando feature {feat.get('id')}: {e}")

    valid, invalid, score, summary = validate_records_batch(transformed_records)
    return valid, invalid, score, summary


def write_parquet_to_minio(
    records: List[Dict[str, Any]],
    prefix: str,
    bucket: str = BUCKET_NAME
) -> bool:
    """
    Convierte una lista de diccionarios a formato Parquet (Snappy) mediante Polars
    y la sube a MinIO S3 usando un búfer en memoria (cero escrituras intermedias a disco).
    """
    if not records:
        logger.info(f"Sin registros para escribir en s3://{bucket}/{prefix}")
        return True

    try:
        ensure_bucket(bucket)

        # Crear DataFrame de Polars
        df = pl.DataFrame(records)

        # Normalizar columnas temporales si están presentes
        if "time" in df.columns:
            df = df.with_columns(pl.col("time").cast(pl.Utf8))
        if "updated" in df.columns:
            df = df.with_columns(pl.col("updated").cast(pl.Utf8))

        # Serialización directa a Parquet Snappy en búfer en memoria
        buffer = io.BytesIO()
        df.write_parquet(buffer, compression="snappy")
        buffer.seek(0)

        s3 = get_s3_client()
        s3.put_object(
            Bucket=bucket,
            Key=prefix,
            Body=buffer.getvalue(),
            ContentType="application/x-parquet",
        )

        logger.info(f"Escrito exitosamente con Polars: s3://{bucket}/{prefix} ({len(records)} filas)")
        return True
    except Exception as e:
        logger.error(f"Error escribiendo Parquet con Polars en s3://{bucket}/{prefix}: {e}", exc_info=True)
        return False
