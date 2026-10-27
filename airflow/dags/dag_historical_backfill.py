"""
### DAG de Backfill Histórico Parametrizado (30 Días)
- **Ejecución:** Manual / Parametrizada por el Administrador.
- **Parámetros:** `start_date`, `end_date`, `min_magnitude`.
- **Propósito:** Descargar histórico de USGS, procesar con Polars y consolidar en MinIO Gold Parquet
  de forma idempotente (sin duplicar datos ya existentes).
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from airflow import DAG
from airflow.models.param import Param
from airflow.operators.python import PythonOperator

sys.path.insert(0, "/opt/airflow")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from include.usgs_client import fetch_usgs_query, fetch_usgs_month_feed
    from include.minio_client import upload_json
    from include.polars_transform import process_features_to_layers, write_parquet_to_minio
    from include.alerts import on_failure_callback
except ImportError:
    from airflow.include.usgs_client import fetch_usgs_query, fetch_usgs_month_feed
    from airflow.include.minio_client import upload_json
    from airflow.include.polars_transform import process_features_to_layers, write_parquet_to_minio
    from airflow.include.alerts import on_failure_callback

DEFAULT_BUCKET = os.getenv("MINIO_BUCKET_NAME", "sismowatch-lake")

default_args = {
    "owner": "sismowatch_admin",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(seconds=30),
    "execution_timeout": timedelta(minutes=15),
    "on_failure_callback": on_failure_callback,
}


def run_historical_backfill(**context):
    """
    Ejecuta la ingesta y transformación histórica con parámetros de ejecución.
    Si no se especifican fechas, descarga el feed oficial mensual completo (~10,000 sismos).
    """
    params = context.get("params", {})
    now = datetime.now(timezone.utc)
    
    start_date = (params.get("start_date") or "").strip()
    end_date = (params.get("end_date") or "").strip()
    min_mag = float(params.get("min_magnitude") or 2.5)

    if not start_date and not end_date:
        start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")
        print(f"🚀 Iniciando Backfill Mensual Completo (all_month.geojson de USGS)...")
        payload = fetch_usgs_month_feed()
    else:
        if not start_date:
            start_date = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = now.strftime("%Y-%m-%d")
        print(f"🚀 Iniciando Backfill Parametrizado: {start_date} a {end_date} (minMag={min_mag})...")
        payload = fetch_usgs_query(start_time=start_date, end_time=end_date, min_magnitude=min_mag)

    if not payload:
        print("⚠️ Advertencia: No se obtuvieron datos históricos de USGS.")
        return

    features = payload.get("features", [])
    print(f"📦 Total de eventos históricos recuperados: {len(features)}")

    # 2. Guardar payload crudo en MinIO Bronze
    bronze_key = f"bronze/backfill/backfill_{start_date}_to_{end_date}.geojson"
    upload_json(DEFAULT_BUCKET, bronze_key, payload)

    # 3. Transformación y validación de calidad con Polars
    valid, invalid, score, summary = process_features_to_layers(features)
    all_records = valid + invalid
    
    # 4. Escritura en Capas Silver y Gold Parquet
    silver_key = f"silver/earthquake_events/backfill/backfill_{start_date}_to_{end_date}.snappy.parquet"
    write_parquet_to_minio(all_records, silver_key, DEFAULT_BUCKET)

    if valid:
        gold_key = f"gold/earthquake_events/backfill/backfill_{start_date}_to_{end_date}.snappy.parquet"
        write_parquet_to_minio(valid, gold_key, DEFAULT_BUCKET)
        print(f"✅ Backfill consolidado en MinIO Gold: {len(valid)} eventos validados (Score: {score}%).")


with DAG(
    dag_id="dag_historical_backfill",
    default_args=default_args,
    description="Carga histórica parametrizada de 30 días desde API USGS hacia MinIO Gold Parquet",
    schedule_interval=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    params={
        "start_date": Param("", type="string", description="Fecha de inicio (YYYY-MM-DD), vacío para 30 días atrás"),
        "end_date": Param("", type="string", description="Fecha de fin (YYYY-MM-DD), vacío para hoy"),
        "min_magnitude": Param(2.5, type="number", description="Magnitud mínima del filtro USGS"),
    },
    tags=["sismowatch", "admin", "backfill", "polars", "minio"],
    doc_md=__doc__,
) as dag:

    backfill_task = PythonOperator(
        task_id="execute_usgs_backfill",
        python_callable=run_historical_backfill,
        provide_context=True,
    )
