from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., example="admin")
    password: str = Field(..., example="AdminSismoWatch2026!")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str
    expires_in_minutes: int


class KpiResponse(BaseModel):
    total_events_24h: int
    max_magnitude: float
    avg_magnitude: float
    tsunami_alerts: int
    quality_score: float
    last_updated: str


class EventItem(BaseModel):
    id: str
    mag: float
    place: str
    time: str
    longitude: float
    latitude: float
    depth_km: float
    tsunami: int
    sig: int
    status: str
    mag_type: str


class PaginatedEventsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    events: List[EventItem]


class TimeseriesItem(BaseModel):
    hour: str
    count: int
    avg_mag: float
    max_mag: float


class TopRegionItem(BaseModel):
    region: str
    count: int
    avg_mag: float
    max_mag: Optional[float] = None


class ChartSuggestion(BaseModel):
    type: str = Field(..., description="bar, line, area, pie, or metric")
    title: str
    x_key: str
    y_key: str
    secondary_y_key: Optional[str] = None


class IntentCatalogMetadata(BaseModel):
    intent: str
    subtype: str
    confidence: float
    target_location: Optional[str] = None
    time_frame: Optional[str] = None
    reasoning: Optional[str] = None
    step1_latency_ms: float = 0.0
    total_latency_ms: float = 0.0


class ChatRequest(BaseModel):
    prompt: Optional[str] = None
    query: Optional[str] = None


class ChatResponse(BaseModel):
    intent: str = Field("analytics", description="conversational | knowledge | status | analytics")
    reply: str
    sql: Optional[str] = None
    data: List[Dict[str, Any]] = []
    chart_suggestion: Optional[ChartSuggestion] = None
    row_count: int = 0
    catalog: Optional[IntentCatalogMetadata] = None
