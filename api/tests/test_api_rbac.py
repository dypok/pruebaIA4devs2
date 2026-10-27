import sys
import os
import pytest
from fastapi.testclient import TestClient

# Asegurar importación de api
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from auth import create_access_token

client = TestClient(app)


def test_healthcheck():
    """Verifica que el endpoint /health responda 200."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "HEALTHY"


def test_unauthenticated_request_returns_401():
    """Verifica que cualquier solicitud a un endpoint protegido sin token retorne 401."""
    response = client.get("/api/kpis")
    assert response.status_code == 401
    assert "detail" in response.json()

    response_quarantine = client.get("/api/quality/quarantine")
    assert response_quarantine.status_code == 401


def test_viewer_access_to_viewer_endpoints():
    """Verifica que un usuario con rol 'viewer' acceda con éxito a los endpoints analíticos."""
    viewer_token = create_access_token({"sub": "viewer", "role": "viewer"})
    headers = {"Authorization": f"Bearer {viewer_token}"}

    response = client.get("/api/kpis", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_events_24h" in data
    assert "max_magnitude" in data


def test_viewer_attempting_admin_endpoint_returns_403():
    """
    Verifica que un usuario con rol 'viewer' reciba 403 Forbidden al intentar acceder
    a la vista de cuarentena o a acciones administrativas.
    """
    viewer_token = create_access_token({"sub": "viewer", "role": "viewer"})
    headers = {"Authorization": f"Bearer {viewer_token}"}

    # Intentar ver cuarentena de calidad
    resp_quarantine = client.get("/api/quality/quarantine", headers=headers)
    assert resp_quarantine.status_code == 403
    assert "restringida" in resp_quarantine.json()["detail"].lower() or "insuficientes" in resp_quarantine.json()["detail"].lower()

    # Intentar lanzar backfill administrativo
    resp_backfill = client.post("/api/admin/backfill", headers=headers)
    assert resp_backfill.status_code == 403


def test_admin_access_to_admin_endpoints():
    """Verifica que un usuario con rol 'admin' tenga acceso total a los endpoints administrativos."""
    admin_token = create_access_token({"sub": "admin", "role": "admin"})
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp_quarantine = client.get("/api/quality/quarantine", headers=headers)
    assert resp_quarantine.status_code == 200
    assert isinstance(resp_quarantine.json(), list)

    resp_backfill = client.post("/api/admin/backfill", headers=headers)
    assert resp_backfill.status_code == 200
    assert resp_backfill.json()["status"] == "BACKFILL_QUEUED"
