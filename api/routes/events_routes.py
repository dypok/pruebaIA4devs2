from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from schemas import KpiResponse, PaginatedEventsResponse, TimeseriesItem, TopRegionItem, EventItem
from auth import require_viewer
from duckdb_service import duckdb_service

router = APIRouter(prefix="/api", tags=["Eventos y Analítica"])


@router.get("/events/map", response_model=List[EventItem])
def get_map_events(
    hours: int = Query(24, ge=1, le=720, description="Ventana temporal en horas (por defecto 24h)"),
    limit: int = Query(500, ge=50, le=1000, description="Cantidad máxima de eventos para el mapa"),
    user: dict = Depends(require_viewer),
):
    """
    Retorna eventos prioritarios para la visualización en el mapa cartográfico global
    filtrados estrictamente por las últimas N horas (por defecto 24 horas).
    """
    return duckdb_service.get_map_events(hours=hours, limit=limit)


@router.get("/kpis", response_model=KpiResponse)
def get_dashboard_kpis(user: dict = Depends(require_viewer)):
    """Retorna los indicadores clave de rendimiento (KPIs) en las últimas 24 horas."""
    return duckdb_service.get_kpis()


@router.get("/events", response_model=PaginatedEventsResponse)
def get_paginated_events(
    page: int = Query(1, ge=1, description="Número de página"),
    page_size: int = Query(20, ge=1, le=100, description="Registros por página"),
    min_magnitude: Optional[float] = Query(None, description="Filtrar por magnitud mínima"),
    region: Optional[str] = Query(None, description="Búsqueda por texto de región"),
    start_date: Optional[str] = Query(None, description="Fecha de inicio (ISO)"),
    end_date: Optional[str] = Query(None, description="Fecha de fin (ISO)"),
    user: dict = Depends(require_viewer),
):
    """Retorna eventos sísmicos paginados con filtros dinámicos."""
    return duckdb_service.get_events(
        page=page,
        page_size=page_size,
        min_magnitude=min_magnitude,
        place_search=region,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/stats/timeseries", response_model=List[TimeseriesItem])
def get_timeseries_stats(user: dict = Depends(require_viewer)):
    """Retorna serie temporal por hora para gráficos de evolución sísmica."""
    return duckdb_service.get_timeseries()


@router.get("/stats/regions", response_model=List[TopRegionItem])
def get_top_regions_stats(
    limit: int = Query(6, ge=1, le=20, description="Cantidad máxima de regiones"),
    hours: Optional[int] = Query(None, ge=1, le=720, description="Ventana de tiempo en horas (opcional)"),
    user: dict = Depends(require_viewer),
):
    """Retorna las regiones con mayor concentración de actividad sísmica."""
    return duckdb_service.get_top_regions(limit=limit, hours=hours)
