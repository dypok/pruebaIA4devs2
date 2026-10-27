import os
import logging
from typing import Dict, Any, List
import requests

logger = logging.getLogger(__name__)

ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")


def notify_invalid_records(invalid_records: List[Dict[str, Any]], run_id: str = "manual"):
    """
    Emite una alerta inmediata en la interfaz y logs de Airflow cuando se detectan registros
    con estado INVALID en la capa Silver para que los operadores actúen rápidamente.
    """
    count = len(invalid_records)
    if count == 0:
        logger.info("Control de calidad conforme: 0 registros inválidos.")
        return

    msg = f"⚠️ [ALERTA INMEDIATA DE CALIDAD EN AIRFLOW]: Se detectaron {count} registros con estado INVALID en run '{run_id}'."
    logger.error("=" * 80)
    logger.error(msg)
    
    # Detallar los primeros 5 errores
    for i, rec in enumerate(invalid_records[:5]):
        logger.error(f"  [{i+1}] ID: {rec.get('id')} | Motivo: {rec.get('validation_error')}")
    if count > 5:
        logger.error(f"  ... y {count - 5} registros inválidos adicionales.")
    logger.error("=" * 80)

    # Si hay webhook configurado, enviar alerta
    if ALERT_WEBHOOK_URL:
        try:
            payload = {
                "text": msg,
                "invalid_count": count,
                "run_id": run_id,
                "sample_errors": [r.get("validation_error") for r in invalid_records[:3]],
            }
            requests.post(ALERT_WEBHOOK_URL, json=payload, timeout=5)
            logger.info("Notificación de alerta enviada al webhook configurado.")
        except Exception as e:
            logger.warning(f"No se pudo enviar notificación webhook: {e}")


def on_failure_callback(context: Dict[str, Any]):
    """
    Callback ejecutado automáticamente por Airflow ante fallos no recuperables en tareas.
    """
    ti = context.get("task_instance")
    task_id = ti.task_id if ti else "unknown_task"
    dag_id = ti.dag_id if ti else "unknown_dag"
    exception = context.get("exception", "Sin detalle de excepción")

    logger.error(f"🚨 [AIRFLOW TASK FAILURE]: Falló tarea '{task_id}' en DAG '{dag_id}'. Error: {exception}")
    
    if ALERT_WEBHOOK_URL:
        try:
            requests.post(
                ALERT_WEBHOOK_URL,
                json={"alert": "TASK_FAILURE", "dag_id": dag_id, "task_id": task_id, "error": str(exception)},
                timeout=5
            )
        except Exception:
            pass
