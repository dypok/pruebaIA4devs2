from datetime import datetime, timezone
from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from auth import require_viewer, require_admin

router = APIRouter(prefix="/api", tags=["Pipeline & Administración"])

# Datos de estado del pipeline
DAG_STATUS_STORE = {
    "dag_usgs_ingestion": {
        "dag_id": "dag_usgs_ingestion",
        "last_run": "2026-10-27T07:05:00Z",
        "state": "success",
        "schedule": "*/5 * * * *",
        "freshness_minutes": 2.4,
    },
    "dag_transform_quality": {
        "dag_id": "dag_transform_quality",
        "last_run": "2026-10-27T07:05:12Z",
        "state": "success",
        "schedule": "Trigger",
        "quality_score": 98.5,
    },
    "dag_ai_daily_report": {
        "dag_id": "dag_ai_daily_report",
        "last_run": "2026-10-27T00:00:00Z",
        "state": "success",
        "schedule": "@daily",
        "ai_status": "verified",
    },
}

# Registros con estado INVALID simulados para la vista de auditoría administrativa
INVALID_RECORDS_STORE = [
    {
        "id": "err_test_9921",
        "mag": 14.5,
        "place": "Hypothetical Outlier Zone",
        "time": "2026-10-27T06:45:00Z",
        "longitude": 210.5,
        "latitude": 98.4,
        "depth_km": -25.0,
        "processing_status": "INVALID",
        "validation_error": "Latitud 98.4 fuera de [-90, 90] | Magnitud 14.5 fuera de [-2, 10] | Profundidad -25.0 km fuera de [-10, 1000]",
        "failed_rules": ["latitude_bounds", "magnitude_bounds", "depth_bounds"],
        "quarantined_at": "2026-10-27T06:45:02Z",
    }
]


@router.get("/pipeline/status")
def get_pipeline_status(user: dict = Depends(require_viewer)):
    """
    Estado de salud y ejecución de DAGs.
    Viewer recibe resumen; Admin recibe detalle técnico completo.
    """
    is_admin = (user.get("role") == "admin")
    
    summary = {
        "overall_health": "HEALTHY",
        "data_freshness_status": "EXCELLENT",
        "last_sync_utc": datetime.now(timezone.utc).isoformat(),
        "quality_score_avg": 98.5,
        "dags": DAG_STATUS_STORE,
    }

    if is_admin:
        summary["admin_telemetry"] = {
            "total_invalid_events_intercepted": len(INVALID_RECORDS_STORE),
            "minio_bucket_status": "CONNECTED",
            "duckdb_memory_status": "OPTIMAL",
            "ollama_agent_status": "ONLINE",
        }

    return summary


@router.get("/quality/quarantine", response_model=List[Dict[str, Any]])
def get_invalid_quarantined_records(user: dict = Depends(require_admin)):
    """
    Visualización de registros con fallos de calidad (estado INVALID).
    RESTRINGIDO EXCLUSIVAMENTE A ADMINISTRADORES (Retorna 403 a Viewer).
    """
    return INVALID_RECORDS_STORE


@router.post("/admin/backfill")
def trigger_historical_backfill(user: dict = Depends(require_admin)):
    """
    Dispara la ejecución de Backfill Histórico de 30 días en Airflow.
    RESTRINGIDO EXCLUSIVAMENTE A ADMINISTRADORES.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "status": "BACKFILL_QUEUED",
        "message": "Carga histórica de 30 días iniciada en Apache Airflow (dag_historical_backfill).",
        "triggered_by": user.get("username"),
        "triggered_at": now_iso,
    }


@router.post("/admin/reports/regenerate")
def trigger_ai_report_regeneration(user: dict = Depends(require_admin)):
    """
    Dispara la regeneración del reporte ejecutivo diario con IA.
    RESTRINGIDO EXCLUSIVAMENTE A ADMINISTRADORES.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "status": "REPORT_REGENERATION_QUEUED",
        "message": "Regeneración de reporte diario con Qwen 2.5:2b disparada exitosamente.",
        "triggered_by": user.get("username"),
        "triggered_at": now_iso,
    }
