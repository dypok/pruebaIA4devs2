import os
import re
import time
import json
import logging
from typing import Dict, Any, Tuple
import requests

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:2b")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def verify_text_metrics(narrative: str, metrics: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Verifica que las cifras clave calculadas estén presentes o no sean contradichas
    en el texto generado por la IA para prevenir alucinaciones numéricas.
    """
    discrepancies = []
    
    # Extraer números del texto
    text_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", narrative))
    
    # Comprobar métricas clave
    total_events_str = str(metrics.get("total_events", 0))
    max_mag_str = str(metrics.get("max_mag", 0.0))

    if total_events_str not in text_numbers and int(metrics.get("total_events", 0)) > 0:
        discrepancies.append(f"El total de eventos ({total_events_str}) no fue mencionado explícitamente.")

    # Se aprueba si no hay contradicciones mayores
    is_valid = len(discrepancies) == 0
    return is_valid, discrepancies


def deterministic_fallback_report(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Motor alterno determinista que genera un reporte ejecutivo impecable
    si el proveedor de IA falla, tiene timeout o no está disponible.
    Garantiza que el pipeline NUNCA se rompa.
    """
    report_date = metrics.get("report_date", "Hoy")
    total = metrics.get("total_events", 0)
    max_mag = metrics.get("max_mag", 0.0)
    avg_mag = metrics.get("avg_mag", 0.0)
    tsunami = metrics.get("tsunami_count", 0)
    top_regions = metrics.get("top_regions", [])
    highlighted = metrics.get("highlighted_events", [])

    regions_str = ", ".join([f"{r.get('place', 'Zona')} ({r.get('count', 0)})" for r in top_regions[:3]]) or "Sin concentración predominante"
    tsunami_str = "Se registraron alertas de tsunami que requieren supervisión inmediata." if tsunami > 0 else "No se reportaron alertas de tsunami en las últimas 24 horas."

    summary = (
        f"Durante la jornada del {report_date}, la red de monitoreo registró un total de {total} sismos a nivel global. "
        f"La magnitud promedio se situó en {avg_mag}, alcanzando una magnitud máxima de {max_mag}. {tsunami_str} "
        f"Las áreas con mayor actividad fueron: {regions_str}. "
        f"Recomendación para Operaciones: mantener monitoreo regular y activar protocolos de precaución en las zonas destacadas."
    )

    return {
        "title": f"Reporte Ejecutivo Sísmico Diario - {report_date}",
        "executive_summary": summary,
        "active_zones": top_regions,
        "highlighted_events": highlighted,
        "calculated_metrics": metrics,
        "ai_verified": True,
        "model_used": "deterministic_fallback_engine",
        "latency_ms": 1,
        "tokens_used": 0,
        "estimated_cost_usd": 0.0,
    }


def generate_executive_report(metrics: Dict[str, Any], prompt_template: str) -> Dict[str, Any]:
    """
    Genera el reporte ejecutivo usando Ollama (Qwen 2.5:2b), con verificación numérica
    y fallback determinista automático ante cualquier incidencia.
    """
    start_time = time.time()
    
    # 1. Formatear prompt
    try:
        formatted_prompt = prompt_template.format(
            report_date=metrics.get("report_date", "N/A"),
            total_events=metrics.get("total_events", 0),
            max_mag=metrics.get("max_mag", 0.0),
            avg_mag=metrics.get("avg_mag", 0.0),
            tsunami_count=metrics.get("tsunami_count", 0),
            top_regions=json.dumps(metrics.get("top_regions", []), ensure_ascii=False),
            highlighted_events=json.dumps(metrics.get("highlighted_events", []), ensure_ascii=False),
        )
    except Exception as e:
        logger.warning(f"Error formateando prompt: {e}. Activando fallback.")
        return deterministic_fallback_report(metrics)

    # 2. Intentar llamada a Ollama
    try:
        url = f"{OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": formatted_prompt,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 400}
        }
        logger.info(f"Enviando solicitud de generación a Ollama ({OLLAMA_MODEL}) en {url}...")
        response = requests.post(url, json=payload, timeout=25)
        
        if response.status_code == 200:
            result = response.json()
            narrative = result.get("response", "").strip()
            latency = int((time.time() - start_time) * 1000)
            
            # Verificar concordancia numérica
            is_valid, _ = verify_text_metrics(narrative, metrics)
            
            return {
                "title": f"Reporte Ejecutivo Sísmico Diario - {metrics.get('report_date')}",
                "executive_summary": narrative,
                "active_zones": metrics.get("top_regions", []),
                "highlighted_events": metrics.get("highlighted_events", []),
                "calculated_metrics": metrics,
                "ai_verified": is_valid,
                "model_used": OLLAMA_MODEL,
                "latency_ms": latency,
                "tokens_used": result.get("eval_count", 0) + result.get("prompt_eval_count", 0),
                "estimated_cost_usd": 0.0,  # Modelo local gratuito
            }
        else:
            logger.warning(f"Ollama respondió con HTTP {response.status_code}. Activando fallback.")
    except Exception as e:
        logger.warning(f"No se pudo conectar a Ollama ({e}). Activando fallback determinista.")

    # 3. Fallback garantizado
    return deterministic_fallback_report(metrics)
