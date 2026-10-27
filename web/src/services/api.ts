import { KpiData, SeismicEvent, TimeseriesPoint, TopRegionItem, AiReport, PipelineTelemetry, ChartSuggestion, ChatResponse } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('sismowatch_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function loginApi(username: string, password: string) {
  const resp = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ detail: 'Error de autenticación' }));
    throw new Error(error.detail || 'Fallo al iniciar sesión');
  }
  return resp.json();
}

export async function fetchKpis(): Promise<KpiData> {
  const resp = await fetch(`${API_BASE}/api/kpis`, { headers: getAuthHeaders() });
  if (!resp.ok) throw new Error('Error obteniendo KPIs');
  return resp.json();
}

export async function fetchEvents(params: {
  page?: number;
  page_size?: number;
  min_magnitude?: number;
  region?: string;
}): Promise<{ total: number; page: number; events: SeismicEvent[] }> {
  const query = new URLSearchParams();
  if (params.page) query.append('page', params.page.toString());
  if (params.page_size) query.append('page_size', params.page_size.toString());
  if (params.min_magnitude) query.append('min_magnitude', params.min_magnitude.toString());
  if (params.region) query.append('region', params.region);

  const resp = await fetch(`${API_BASE}/api/events?${query.toString()}`, { headers: getAuthHeaders() });
  if (!resp.ok) throw new Error('Error obteniendo eventos');
  return resp.json();
}

export async function fetchMapEvents(limit: number = 500): Promise<SeismicEvent[]> {
  const resp = await fetch(`${API_BASE}/api/events/map?limit=${limit}`, { headers: getAuthHeaders() });
  if (!resp.ok) throw new Error('Error obteniendo eventos del mapa');
  return resp.json();
}

export async function fetchTimeseries(): Promise<TimeseriesPoint[]> {
  const resp = await fetch(`${API_BASE}/api/stats/timeseries`, { headers: getAuthHeaders() });
  if (!resp.ok) throw new Error('Error obteniendo serie temporal');
  return resp.json();
}

export async function fetchTopRegions(): Promise<TopRegionItem[]> {
  const resp = await fetch(`${API_BASE}/api/stats/regions`, { headers: getAuthHeaders() });
  if (!resp.ok) throw new Error('Error obteniendo regiones');
  return resp.json();
}

export async function fetchReports(): Promise<AiReport[]> {
  const resp = await fetch(`${API_BASE}/api/reports`, { headers: getAuthHeaders() });
  if (!resp.ok) throw new Error('Error obteniendo reportes');
  return resp.json();
}

export async function fetchPipelineStatus(): Promise<PipelineTelemetry> {
  const resp = await fetch(`${API_BASE}/api/pipeline/status`, { headers: getAuthHeaders() });
  if (!resp.ok) throw new Error('Error obteniendo estado del pipeline');
  return resp.json();
}

export async function fetchQuarantineRecords(): Promise<any[]> {
  const resp = await fetch(`${API_BASE}/api/quality/quarantine`, { headers: getAuthHeaders() });
  if (!resp.ok) throw new Error('Acceso denegado o error de cuarentena');
  return resp.json();
}

export async function triggerBackfillApi(): Promise<any> {
  const resp = await fetch(`${API_BASE}/api/admin/backfill`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!resp.ok) throw new Error('Error lanzando backfill');
  return resp.json();
}

export async function triggerAiRegenerateApi(): Promise<any> {
  const resp = await fetch(`${API_BASE}/api/admin/reports/regenerate`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!resp.ok) throw new Error('Error regenerando reporte');
  return resp.json();
}

export async function sendChatMessage(prompt: string): Promise<ChatResponse> {
  const resp = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ prompt }),
  });
  if (!resp.ok) throw new Error('Error en el servicio de chat');
  return resp.json();
}
