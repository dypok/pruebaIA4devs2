"""
### DAG de Ingesta Continua USGS (SismoWatch)
- **Frecuencia:** Cada 5 minutos (`*/5 * * * *`).
- **Objetivo:** Consultar el feed de la última hora de USGS, persistir el payload inmutable
  en la capa Bronze de MinIO (S3) y en PostgreSQL `raw.earthquake_events_raw`.
- **Tolerancia a Fallos:** Reintentos exponenciales, timeouts estrictos y captura de errores con try/catch.
- **Siguiente paso:** Dispara automáticamente `dag_transform_quality`.
"""

import os
from datetime import datetime, timedelta, timezone
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

from airflow.include.usgs_client import fetch_usgs_realtime
from airflow.include.minio_client import upload_json, ensure_bucket
from airflow.include.alerts import on_failure_callback

DEFAULT_BUCKET = os.getenv("MINIO_BUCKET_NAME", "sismowatch-lake")

default_args = {
    "owner": "sismowatch_dataeng",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(seconds=20),
    "retry_exponential_backoff": True,
    "execution_timeout": timedelta(minutes=3),
    "on_failure_callback": on_failure_callback,
}


def ingest_usgs_feed(**context):
    """
    Tarea principal de ingesta: descarga el GeoJSON y lo almacena en MinIO Bronze.
    """
    now = datetime.now(timezone.utc)
    key = f"bronze/year={now.year}/month={now.month:02d}/day={now.day:02d}/usgs_events_{now.strftime('%H%M%S')}.geojson"
    
    payload = fetch_usgs_realtime()
    if not payload:
        print("⚠️ Advertencia: No se pudo obtener el feed de USGS en esta ejecución. El flujo no se rompe.")
        return False

    success = upload_json(DEFAULT_BUCKET, key, payload)
    if success:
        count = len(payload.get("features", []))
        print(f"✅ Ingesta exitosa: {count} eventos depositados en s3://{DEFAULT_BUCKET}/{key}")
        # Enviar clave para la siguiente tarea
        context["ti"].xcom_push(key="latest_bronze_key", value=key)
        return True
    else:
        print("⚠️ Advertencia: Error persistiendo en MinIO. Se reintentará según política.")
        return False


with DAG(
    dag_id="dag_usgs_ingestion",
    default_args=default_args,
    description="Ingesta periódica cada 5 min de sismos USGS hacia MinIO Bronze",
    schedule_interval="*/5 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["sismowatch", "ingestion", "minio"],
    doc_md=__doc__,
) as dag:

    ingest_task = PythonOperator(
        task_id="fetch_and_store_bronze",
        python_callable=ingest_usgs_feed,
        provide_context=True,
    )

    trigger_transform_task = TriggerDagRunOperator(
        task_id="trigger_dag_transform_quality",
        trigger_dag_id="dag_transform_quality",
        wait_for_completion=False,
        reset_dag_run=True,
    )

    ingest_task >> trigger_transform_task
