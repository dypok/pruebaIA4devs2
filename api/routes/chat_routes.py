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

    # 1. Ranking de eventos / magnitudes por lugar (Barras categóricas)
    if any("place" in c.lower() for c in categorical_cols) and "mag" in numeric_cols:
        for row in data:
            if "place" in row and isinstance(row["place"], str):
                p_val = row["place"]
                if " of " in p_val:
                    p_val = p_val.split(" of ", 1)[1]
                row["place_short"] = p_val[:22]
        return ChartSuggestion(
            type="bar",
            title="Ranking de Magnitud (Mw) por Epicentro",
            x_key="place_short" if "place_short" in data[0] else "place",
            y_key="mag",
        )

    # 2. Serie de tiempo cronológica (Eje X temporal + Métrica numérica)
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

    # 3. Barras categóricas estándar (Eje X categoría + Métrica numérica)
    if categorical_cols and numeric_cols:
        return ChartSuggestion(
            type="bar",
            title=f"Distribución de {numeric_cols[0].replace('_', ' ').title()} por {categorical_cols[0].replace('_', ' ').title()}",
            x_key=categorical_cols[0],
            y_key=numeric_cols[0],
            secondary_y_key=numeric_cols[1] if len(numeric_cols) > 1 else None,
        )

    # 4. Dos columnas numéricas (ej. mag vs depth)
    if len(numeric_cols) >= 2:
        return ChartSuggestion(
            type="bar",
            title=f"Comparativa de {numeric_cols[0]} vs {numeric_cols[1]}",
            x_key=numeric_cols[0],
            y_key=numeric_cols[1],
        )

    return None


from cognitive_agent import cognitive_agent


@router.post("", response_model=ChatResponse)
def chat_with_data_agent(
    request: ChatRequest,
    user: dict = Depends(require_viewer),
):
    """
    Agente conversacional y analítico con inferencia cognitiva adaptativa (Qwen 2.5:2b).
    Distingue entre conversación, ciencia sísmica, telemetría y consultas cuantitativas.
    """
    raw_prompt = request.prompt or request.query or ""
    clean_prompt = raw_prompt.strip()
    if not clean_prompt:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío.")

    result = cognitive_agent.process_message(clean_prompt)

    # Restricción RBAC: En la vista de cliente (viewer), se ocultan consultas SQL internas y auditoría técnica
    user_role = user.get("role", "viewer") if isinstance(user, dict) else getattr(user, "role", "viewer")
    if user_role != "admin":
        result["sql"] = None
        result["catalog"] = None

    return ChatResponse(**result)
