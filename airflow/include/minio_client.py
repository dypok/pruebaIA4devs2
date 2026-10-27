import os
import json
import logging
from typing import Any, Dict, List, Optional
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin2026!")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
DEFAULT_BUCKET = os.getenv("MINIO_BUCKET_NAME", "sismowatch-lake")


def get_s3_client():
    """Retorna un cliente boto3 configurado para MinIO."""
    try:
        return boto3.client(
            "s3",
            endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
    except Exception as e:
        logger.error(f"Error inicializando cliente S3 MinIO: {e}", exc_info=True)
        raise


def ensure_bucket(bucket_name: str = DEFAULT_BUCKET) -> bool:
    """Asegura que el bucket exista en MinIO; si no existe, lo crea."""
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=bucket_name)
        return True
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code in ("404", "NoSuchBucket"):
            try:
                s3.create_bucket(Bucket=bucket_name)
                logger.info(f"Bucket '{bucket_name}' creado exitosamente en MinIO.")
                return True
            except Exception as create_err:
                logger.error(f"Error creando bucket '{bucket_name}': {create_err}")
                return False
        logger.error(f"Error verificando bucket '{bucket_name}': {e}")
        return False
    except Exception as e:
        logger.error(f"Excepción general en ensure_bucket: {e}")
        return False


def upload_json(bucket: str, key: str, data: Any) -> bool:
    """Sube un objeto o diccionario serializado en JSON a MinIO con try/catch."""
    s3 = get_s3_client()
    try:
        ensure_bucket(bucket)
        if isinstance(data, (dict, list)):
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        elif isinstance(data, str):
            body = data.encode("utf-8")
        else:
            body = str(data).encode("utf-8")

        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/json"
        )
        logger.info(f"Objeto JSON subido a s3://{bucket}/{key}")
        return True
    except Exception as e:
        logger.error(f"Error subiendo JSON a s3://{bucket}/{key}: {e}", exc_info=True)
        return False


def download_json(bucket: str, key: str) -> Optional[Dict[str, Any]]:
    """Descarga y parsea un archivo JSON desde MinIO."""
    s3 = get_s3_client()
    try:
        resp = s3.get_object(Bucket=bucket, Key=key)
        content = resp["Body"].read().decode("utf-8")
        return json.loads(content)
    except Exception as e:
        logger.error(f"Error descargando JSON de s3://{bucket}/{key}: {e}", exc_info=True)
        return None


def list_objects(bucket: str, prefix: str = "") -> List[str]:
    """Lista las claves de objetos en un bucket con un prefijo específico."""
    s3 = get_s3_client()
    keys = []
    try:
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                keys.append(obj["Key"])
        return keys
    except Exception as e:
        logger.error(f"Error listando objetos en s3://{bucket}/{prefix}: {e}", exc_info=True)
        return []
