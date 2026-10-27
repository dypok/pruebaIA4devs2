import re
import json
import logging
from typing import Dict, Any, Optional
import requests
from fastapi import APIRouter, Depends, HTTPException
from schemas import ChatRequest, ChatResponse, ChartSuggestion
from auth import require_viewer
from config import OLLAMA_BASE_URL, OLLAMA_MODEL
from duckdb_service import duckdb_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Chatbot Inteligente (Qwen 2.5:2b)"])


def infer_chart_type(data: list, columns: list) -> Optional[ChartSuggestion]:
    """
    Infiere el tipo de gráfico idóneo a partir de la estructura del conjunto de datos retornado.
    """
    if not data or len(data) == 0 or not columns:
        return None

    # Detectar columna numérica y columna de categoría
    numeric_cols = []
    categorical_cols = []
    time_cols = []

    first_row = data[0]
    for col in columns:
        val = first_row.get(col)
        if isinstance(val, (int, float)):
            numeric_cols.append(col)
        elif isinstance(val, str) and ("time" in col.lower() or "hour" in col.lower() or "date" in col.lower()):
            time_cols.append(col)
        else:
            categorical_cols.append(col)

    # 1. Serie de tiempo (Eje X temporal + Métrica numérica)
    if time_cols and numeric_cols:
        return ChartSuggestion(
            type="line",
            title=f"Evolución Temporal de {numeric_cols[0].replace('_', ' ').title()}",
            x_key=time_cols[0],
            y_key=numeric_cols[0],
        )

    # 2. Barras categóricas (Eje X categoría + Métrica numérica)
    if categorical_cols and numeric_cols:
        return ChartSuggestion(
            type="bar",
            title=f"Distribución de {numeric_cols[0].replace('_', ' ').title()} por {categorical_cols[0].replace('_', ' ').title()}",
            x_key=categorical_cols[0],
            y_key=numeric_cols[0],
            secondary_y_key=numeric_cols[1] if len(numeric_cols) > 1 else None,
        )

    # 3. Dos columnas numéricas (ej. mag vs depth)
    if len(numeric_cols) >= 2:
        return ChartSuggestion(
            type="bar",
            title=f"Comparativa de {numeric_cols[0]} vs {numeric_cols[1]}",
            x_key=numeric_cols[0],
            y_key=numeric_cols[1],
        )

    return None


def generate_fallback_sql_and_answer(prompt: str) -> Dict[str, Any]:
    """
    Motor determinista de respaldo para Text-to-SQL y redacción en caso de que
    Ollama esté ocupado, iniciando o descargando el modelo.
    """
    p_lower = prompt.lower()

    if "fuerte" in p_lower or "mayor" in p_lower or "max" in p_lower:
        sql = "SELECT place, mag, depth_km, time FROM earthquake_events ORDER BY mag DESC LIMIT 5"
        res = duckdb_service.execute_read_only_query(sql)
        reply = (
            f"He consultado los sismos de mayor magnitud registrados en la base de datos. "
            f"El evento más intenso fue de magnitud {res['data'][0]['mag']} en '{res['data'][0]['place']}'."
        )
        return {"sql": sql, "reply": reply, "res": res}

    elif "region" in p_lower or "zona" in p_lower or "donde" in p_lower:
        sql = "SELECT place, COUNT(*) as count, ROUND(AVG(mag), 2) as avg_mag FROM earthquake_events GROUP BY place ORDER BY count DESC LIMIT 5"
        res = duckdb_service.execute_read_only_query(sql)
        top = res['data'][0] if res['data'] else {"place": "General", "count": 0}
        reply = (
            f"El análisis de concentración geográfica sitúa a '{top['place']}' "
            f"como la zona con mayor número de sismos ({top['count']} eventos registrados)."
        )
        return {"sql": sql, "reply": reply, "res": res}

    elif "tsunami" in p_lower:
        sql = "SELECT place, mag, tsunami, time FROM earthquake_events WHERE tsunami = 1 ORDER BY time DESC LIMIT 5"
        res = duckdb_service.execute_read_only_query(sql)
        tsunami_count = len(res['data'])
        reply = (
            f"Se identificaron {tsunami_count} sismos con advertencia de tsunami activa en los registros analizados."
            if tsunami_count > 0 else "No se detectaron eventos con alerta de tsunami activa en la base de datos."
        )
        return {"sql": sql, "reply": reply, "res": res}

    else:
        sql = "SELECT place, mag, depth_km, time FROM earthquake_events ORDER BY time DESC LIMIT 8"
        res = duckdb_service.execute_read_only_query(sql)
        reply = f"He consultado los {len(res['data'])} eventos sísmicos más recientes registrados en la plataforma."
        return {"sql": sql, "reply": reply, "res": res}


@router.post("", response_model=ChatResponse)
def chat_with_data_agent(
    request: ChatRequest,
    user: dict = Depends(require_viewer),
):
    """
    Agente conversacional Text-to-SQL con Qwen 2.5:2b y generación automática de gráficos.
    Traduce la pregunta en lenguaje natural a DuckDB SQL, ejecuta sobre Parquets y entrega respuesta.
    """
    clean_prompt = request.prompt.strip()
    if not clean_prompt:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    # 1. Intentar Text-to-SQL con Ollama (Qwen 2.5:2b)
    sql_to_execute = None
    try:
        sys_prompt = (
            "Genera ÚNICAMENTE una consulta SQL válida para DuckDB sobre la vista `earthquake_events` "
            "(columnas: id, mag, place, time, longitude, latitude, depth_km, tsunami, sig). "
            "Responde estrictamente con la consulta SQL pura comenzando con SELECT. Sin explicaciones ni markdown."
        )
        ollama_url = f"{OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": f"{sys_prompt}\nPregunta: {clean_prompt}\nSQL:",
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 120}
        }
        resp = requests.post(ollama_url, json=payload, timeout=6)
        if resp.status_code == 200:
            raw_sql = resp.json().get("response", "").strip()
            # Extraer SQL si viene envuelto en markdown
            sql_match = re.search(r"SELECT\s+.*", raw_sql, re.IGNORECASE | re.DOTALL)
            if sql_match:
                extracted = sql_match.group(0).split(";")[0].strip()
                if extracted.upper().startswith("SELECT"):
                    sql_to_execute = extracted
    except Exception as e:
        logger.warning(f"Ollama no disponible para Text-to-SQL ({e}); activando motor determinista.")

    # 2. Ejecución con Fallback Seguro si Ollama falló o no dio SQL válido
    if not sql_to_execute:
        fb = generate_fallback_sql_and_answer(clean_prompt)
        res = fb["res"]
        reply = fb["reply"]
        sql_to_execute = fb["sql"]
    else:
        try:
            res = duckdb_service.execute_read_only_query(sql_to_execute)
            reply = f"He ejecutado la consulta SQL sobre los eventos en DuckDB y recuperé {res['row_count']} registros."
        except Exception as query_err:
            logger.warning(f"Error ejecutando SQL generado por IA ({query_err}); usando fallback.")
            fb = generate_fallback_sql_and_answer(clean_prompt)
            res = fb["res"]
            reply = fb["reply"]
            sql_to_execute = fb["sql"]

    # 3. Inferencia de tipo de gráfico
    chart_sug = infer_chart_type(res["data"], res["columns"])

    return ChatResponse(
        reply=reply,
        sql=sql_to_execute,
        data=res["data"],
        chart_suggestion=chart_sug,
        row_count=res["row_count"],
    )
