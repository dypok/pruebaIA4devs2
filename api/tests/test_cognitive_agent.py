import sys
import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Asegurar importación de api
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from auth import create_access_token
from cognitive_agent import cognitive_agent, _normalize_text

client = TestClient(app)


def test_text_normalization():
    """Verifica que la normalización elimine acentos, signos de puntuación y mayúsculas."""
    assert _normalize_text("¿Cuántos sismos hay?") == "cuantos sismos hay"
    assert _normalize_text("¡Hola! ¿Qué tal?") == "hola que tal"
    assert _normalize_text("Falla de San Andrés") == "falla de san andres"
    assert _normalize_text("Cinturón de Fuego") == "cinturon de fuego"


def test_intent_classification():
    """Verifica la clasificación semántica en las 4 modalidades operativas."""
    # 1. CONVERSATIONAL
    assert cognitive_agent.classify_intent("hola") == "CONVERSATIONAL"
    assert cognitive_agent.classify_intent("Buenos días") == "CONVERSATIONAL"
    assert cognitive_agent.classify_intent("Muchas gracias") == "CONVERSATIONAL"
    assert cognitive_agent.classify_intent("¿Qué puedes hacer?") == "CONVERSATIONAL"
    assert cognitive_agent.classify_intent("ayuda") == "CONVERSATIONAL"

    # 2. KNOWLEDGE
    assert cognitive_agent.classify_intent("¿Qué es la falla de San Andrés?") == "KNOWLEDGE"
    assert cognitive_agent.classify_intent("¿Qué hacer durante un sismo?") == "KNOWLEDGE"
    assert cognitive_agent.classify_intent("Diferencia entre escala Richter y Magnitud de Momento") == "KNOWLEDGE"
    assert cognitive_agent.classify_intent("¿Por qué tiembla tanto en el Cinturón de Fuego?") == "KNOWLEDGE"
    assert cognitive_agent.classify_intent("¿Qué es el epicentro y el hipocentro?") == "KNOWLEDGE"

    # 3. STATUS
    assert cognitive_agent.classify_intent("¿Cuántos sismos hay registrados?") == "STATUS"
    assert cognitive_agent.classify_intent("Estado del sistema") == "STATUS"
    assert cognitive_agent.classify_intent("Salud de la plataforma") == "STATUS"
    assert cognitive_agent.classify_intent("¿De dónde vienen los datos?") == "STATUS"

    # 4. ANALYTICS
    assert cognitive_agent.classify_intent("¿Cuáles son los 5 sismos más fuertes?") == "ANALYTICS"
    assert cognitive_agent.classify_intent("Sismos agrupados por región") == "ANALYTICS"
    assert cognitive_agent.classify_intent("¿Hubo sismos con alerta de tsunami?") == "ANALYTICS"
    assert cognitive_agent.classify_intent("Terremotos recientes en Chile") == "ANALYTICS"


def test_handle_conversational():
    """Verifica que los mensajes conversacionales no generen SQL ni gráficos."""
    res = cognitive_agent.process_message("hola")
    assert res["intent"] == "conversational"
    assert res["sql"] is None
    assert res["data"] == []
    assert res["chart_suggestion"] is None
    assert res["row_count"] == 0
    assert "SismoWatch" in res["reply"]


def test_handle_knowledge():
    """Verifica que las consultas de divulgación y prevención retornen contenido científico en Markdown sin SQL."""
    res = cognitive_agent.process_message("¿Qué es la falla de San Andrés?")
    assert res["intent"] == "knowledge"
    assert res["sql"] is None
    assert res["data"] == []
    assert res["chart_suggestion"] is None
    assert "San Andrés" in res["reply"]
    assert "Placa del Pacífico" in res["reply"]

    res_prev = cognitive_agent.process_message("¿Qué hacer durante un sismo?")
    assert res_prev["intent"] == "knowledge"
    assert "Seguridad y Prevención" in res_prev["reply"]
    assert "Cúbrete" in res_prev["reply"]


def test_handle_status():
    """Verifica que la telemetría devuelva el estado de Lakehouse/DuckDB."""
    with patch("cognitive_agent.duckdb_service.get_kpis") as mock_kpis:
        mock_kpis.return_value = {
            "total_events_24h": 9870,
            "max_magnitude": 7.7,
            "last_updated": "2026-10-27 15:30",
        }
        res = cognitive_agent.process_message("¿Cuántos sismos hay registrados?")
        assert res["intent"] == "status"
        assert res["sql"] is None
        assert res["row_count"] == 9870
        assert "9,870 sismos" in res["reply"]
        assert "USGS" in res["reply"]


def test_handle_analytics_safety_limit():
    """Verifica que las consultas analíticas ejecuten SQL con salvaguarda de LIMIT obligatoria."""
    res = cognitive_agent.process_message("¿Cuáles son los 5 sismos más fuertes?")
    assert res["intent"] == "analytics"
    assert res["sql"] is not None
    assert "LIMIT" in res["sql"].upper()


def test_chat_api_endpoint_rbac_and_flow():
    """Verifica el endpoint HTTP /api/chat protegiendo con token y soportando múltiples intenciones."""
    # 1. Sin autenticación -> 401
    resp_unauth = client.post("/api/chat", json={"prompt": "hola"})
    assert resp_unauth.status_code == 401

    # 2. Con autenticación viewer
    token = create_access_token({"sub": "viewer", "role": "viewer"})
    headers = {"Authorization": f"Bearer {token}"}

    # Prompt conversacional
    resp_conv = client.post("/api/chat", json={"prompt": "hola"}, headers=headers)
    assert resp_conv.status_code == 200
    data_conv = resp_conv.json()
    assert data_conv["intent"] == "conversational"
    assert data_conv["sql"] is None
    assert data_conv["data"] == []

    # Prompt de conocimiento
    resp_know = client.post("/api/chat", json={"prompt": "¿Qué es la falla de San Andrés?"}, headers=headers)
    assert resp_know.status_code == 200
    data_know = resp_know.json()
    assert data_know["intent"] == "knowledge"
    assert "San Andrés" in data_know["reply"]
    assert data_know["sql"] is None

    # Prompt de estado
    resp_stat = client.post("/api/chat", json={"prompt": "Estado del sistema"}, headers=headers)
    assert resp_stat.status_code == 200
    data_stat = resp_stat.json()
    assert data_stat["intent"] == "status"
    assert data_stat["sql"] is None
