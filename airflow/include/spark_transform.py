import os
import json
import logging
import tempfile
from typing import Dict, Any, List, Tuple
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

try:
    from include.transforms import transform_geojson_feature
    from include.quality import validate_records_batch
    from include.minio_client import get_s3_client, ensure_bucket, upload_json, list_objects
except ImportError:
    from airflow.include.transforms import transform_geojson_feature
    from airflow.include.quality import validate_records_batch
    from airflow.include.minio_client import get_s3_client, ensure_bucket, upload_json, list_objects

logger = logging.getLogger(__name__)

BUCKET_NAME = os.getenv("MINIO_BUCKET_NAME", "sismowatch-lake")


def process_features_to_layers(
    features: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], float, Dict[str, Any]]:
    """
    Procesa una lista de features GeoJSON:
    1. Transforma y sanitiza cada registro.
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
    Convierte una lista de diccionarios a formato Parquet (Snappy) y la sube a MinIO.
    """
    if not records:
        logger.info(f"Sin registros para escribir en s3://{bucket}/{prefix}")
        return True

    try:
        ensure_bucket(bucket)
        df = pd.DataFrame(records)
        
        # Asegurar tipos datetime
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"], utc=True)
        if "updated" in df.columns:
            df["updated"] = pd.to_datetime(df["updated"], utc=True)

        table = pa.Table.from_pandas(df)

        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            pq.write_table(table, tmp_path, compression="SNAPPY")

        s3 = get_s3_client()
        with open(tmp_path, "rb") as f:
            s3.put_object(
                Bucket=bucket,
                Key=prefix,
                Body=f.read(),
                ContentType="application/x-parquet"
            )

        os.remove(tmp_path)
        logger.info(f"Parquet escrito exitosamente en s3://{bucket}/{prefix} ({len(records)} filas).")
        return True
    except Exception as e:
        logger.error(f"Error escribiendo Parquet en s3://{bucket}/{prefix}: {e}", exc_info=True)
        return False
