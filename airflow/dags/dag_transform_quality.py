"""
### DAG de Transformación y Calidad (Polars + Pandera + MinIO)
- **Activación:** Disparado automáticamente al finalizar la ingesta.
- **Procesamiento:** Lee el dato crudo de MinIO Bronze, desanida y normaliza mediante Polars.
- **Control de Calidad:** Aplica validaciones bloqueantes con Pandera.
- **Capa Silver:** Guarda todos los registros con su estado (`VALID` o `INVALID` con motivo).
- **Alerta Inmediata en Airflow:** Si existen registros `INVALID`, notifica de inmediato al operador.
- **Capa Gold:** Promueve exclusivamente registros certificados `VALID` a Parquet particionado.
- **Analítica:** Ejecuta detección de anomalías y persiste métricas de calidad.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from airflow import DAG
from airflow.operators.python import PythonOperator

sys.path.insert(0, "/opt/airflow")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from include.minio_client import download_json, list_objects
    from include.polars_transform import process_features_to_layers, write_parquet_to_minio
    from include.anomaly import detect_seismic_anomalies
    from include.alerts import notify_invalid_records, on_failure_callback
except ImportError:
    from airflow.include.minio_client import download_json, list_objects
    from airflow.include.polars_transform import process_features_to_layers, write_parquet_to_minio
    from airflow.include.anomaly import detect_seismic_anomalies
    from airflow.include.alerts import notify_invalid_records, on_failure_callback

DEFAULT_BUCKET = os.getenv("MINIO_BUCKET_NAME", "sismowatch-lake")

default_args = {
    "owner": "sismowatch_dataeng",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(seconds=15),
    "execution_timeout": timedelta(minutes=5),
    "on_failure_callback": on_failure_callback,
}


def transform_and_validate_task(**context):
    """
    Descarga el archivo GeoJSON más reciente de Bronze, transforma y clasifica en Silver y Gold.
    """
    ti = context["ti"]
    run_id = context.get("run_id", "manual")
    now = datetime.now(timezone.utc)
    
    # 1. Obtener última clave procesada o listar el objeto más reciente en Bronze
    bronze_key = ti.xcom_pull(dag_id="dag_usgs_ingestion", key="latest_bronze_key")
    if not bronze_key:
        keys = list_objects(DEFAULT_BUCKET, prefix="bronze/")
        if keys:
            bronze_key = sorted(keys)[-1]
        else:
            print("ℹ️ No hay objetos en MinIO Bronze para transformar.")
            return

    print(f"📖 Leyendo feed crudo desde s3://{DEFAULT_BUCKET}/{bronze_key}")
    payload = download_json(DEFAULT_BUCKET, bronze_key)
    if not payload:
        print("⚠️ Advertencia: No se pudo leer el payload de Bronze. Se aborta sin romper.")
        return

    features = payload.get("features", [])
    print(f"⚙️ Procesando {len(features)} eventos sísmicos con Polars y Pandera...")

    valid_records, invalid_records, score, summary = process_features_to_layers(features)
    all_records = valid_records + invalid_records

    # 2. Escribir a Capa SILVER (todos los registros con su estado)
    silver_key = f"silver/earthquake_events/year={now.year}/month={now.month:02d}/events_{now.strftime('%H%M%S')}.snappy.parquet"
    write_parquet_to_minio(all_records, silver_key, DEFAULT_BUCKET)

    # 3. Control y Alerta Inmediata en Airflow si hay registros inválidos
    if invalid_records:
        notify_invalid_records(invalid_records, run_id=run_id)

    # 4. Escribir a Capa GOLD (solo registros conformes con VALID)
    if valid_records:
        gold_key = f"gold/earthquake_events/year={now.year}/month={now.month:02d}/events_{now.strftime('%H%M%S')}.snappy.parquet"
        write_parquet_to_minio(valid_records, gold_key, DEFAULT_BUCKET)
        
        # 5. Detección de anomalías en datos certificados
        anomalies = detect_seismic_anomalies(valid_records)
        print(f"🔍 Análisis analítico completado: {len(anomalies)} anomalías identificadas.")

    print(f"🎉 Pipeline de calidad finalizado: {len(valid_records)} válidos promovidos a Gold. Calidad: {score}%.")


with DAG(
    dag_id="dag_transform_quality",
    default_args=default_args,
    description="Transformación con Polars, validación con Pandera y particionado Parquet en MinIO",
    schedule_interval=None,  # Disparado por dag_usgs_ingestion
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["sismowatch", "polars", "quality", "parquet", "minio"],
    doc_md=__doc__,
) as dag:

    process_task = PythonOperator(
        task_id="polars_transform_and_quality_check",
        python_callable=transform_and_validate_task,
        provide_context=True,
    )
