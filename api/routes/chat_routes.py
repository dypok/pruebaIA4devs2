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
        if len(data) > 40:
            return None  # Evitar gráficos saturados con demasiados puntos individuales

        # Formatear timestamps para que los labels de los ejes sean limpios (YYYY-MM-DD HH:mm)
        for row in data:
            for t_col in time_cols:
                val = row.get(t_col)
                if isinstance(val, str) and len(val) >= 16 and "T" in val:
                    row[t_col] = val.replace("T", " ")[:16]

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
    raw_prompt = request.prompt or request.query or ""
    clean_prompt = raw_prompt.strip()
    if not clean_prompt:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    # 0. Interceptación inteligente de mensajes conversacionales, saludos y ayuda
    normalized = clean_prompt.lower().strip("?!.,;: ")
    greetings = {"hola", "buenas", "buen dia", "buenos dias", "buenas tardes", "buenas noches", "hey", "hello", "hi", "saludos"}
    help_queries = {"que puedes hacer", "que haces", "ayuda", "help", "como funciona", "opciones", "quien eres"}
    thanks_queries = {"gracias", "muchas gracias", "ok", "vale", "listo", "perfecto", "adios", "chao", "hasta luego"}

    if normalized in greetings or any(normalized.startswith(g + " ") for g in greetings):
        return ChatResponse(
            reply=(
                "¡Hola! 👋 Soy tu asistente analítico de SismoWatch impulsado por IA local (Qwen 2.5:2b).\n\n"
                "Puedo responder preguntas en lenguaje natural sobre sismos, regiones de mayor concentración, "
                "alertas de tsunami o tendencias temporales, generando consultas SQL y gráficos interactivos que puedes fijar al dashboard.\n\n"
                "💡 **Prueba preguntándome:**\n"
                "• *¿Cuáles son los 5 sismos más fuertes de este mes?*\n"
                "• *¿Qué zonas tienen mayor concentración de sismos?*\n"
                "• *¿Hubo sismos con alerta de tsunami?*\n"
                "• *¿Cuál fue el sismo más reciente?*"
            ),
            sql=None,
            data=[],
            chart_suggestion=None,
            row_count=0,
        )

    if normalized in help_queries or "puedes hacer" in normalized or "como te uso" in normalized:
        return ChatResponse(
            reply=(
                "Estoy conectado en tiempo real al Lakehouse en MinIO y a DuckDB.\n\n"
                "Traduzco tus preguntas a consultas SQL optimizadas sobre la vista `earthquake_events` y genero gráficos interactivos para tu dashboard.\n\n"
                "📌 **Consultas sugeridas:**\n"
                "• *'Los 5 sismos más fuertes'*\n"
                "• *'Top 5 regiones con más sismos'*\n"
                "• *'Sismos con alerta de tsunami'*\n"
                "• *'Sismos de magnitud mayor a 6'*"
            ),
            sql=None,
            data=[],
            chart_suggestion=None,
            row_count=0,
        )

    if normalized in thanks_queries:
        return ChatResponse(
            reply="¡Con gusto! Quedo a tu disposición si necesitas analizar algún otro evento sísmico o métrica.",
            sql=None,
            data=[],
            chart_suggestion=None,
            row_count=0,
        )

    # 1. Intentar Text-to-SQL con Ollama (Qwen 2.5:2b)
    sql_to_execute = None
    try:
        sys_prompt = (
            "Eres un asistente de datos SQL para DuckDB sobre la vista `earthquake_events` "
            "(columnas: id, mag, place, time, longitude, latitude, depth_km, tsunami, sig).\n"
            "Reglas estrictas:\n"
            "1. Genera ÚNICAMENTE una consulta SQL válida comenzando con SELECT. Sin explicaciones ni bloques de markdown.\n"
            "2. SIEMPRE incluye 'LIMIT 5' o 'LIMIT 10' si la consulta no tiene GROUP BY ni COUNT.\n"
            "3. NUNCA devuelvas 'SELECT * FROM earthquake_events' sin LIMIT ni filtros.\n"
            "4. Si piden los más fuertes o intensos, usa 'ORDER BY mag DESC LIMIT 5'.\n"
            "5. Si piden los más recientes, usa 'ORDER BY time DESC LIMIT 8'."
        )
        ollama_url = f"{OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": f"{sys_prompt}\nPregunta del usuario: {clean_prompt}\nSQL:",
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
        # Salvaguarda: Si la consulta no tiene LIMIT ni agregaciones (GROUP BY / COUNT), limitar a 10
        upper_sql = sql_to_execute.upper()
        if "LIMIT" not in upper_sql and "GROUP BY" not in upper_sql and "COUNT(" not in upper_sql:
            sql_to_execute = f"{sql_to_execute.rstrip(';')} LIMIT 10"

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
