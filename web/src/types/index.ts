export interface SeismicEvent {
  id: string;
  mag: number;
  place: string;
  time: string;
  longitude: number;
  latitude: number;
  depth_km: number;
  tsunami: number;
  sig: number;
  status: string;
  mag_type: string;
}

export interface KpiData {
  total_events_24h: number;
  max_magnitude: number;
  avg_magnitude: number;
  tsunami_alerts: number;
  quality_score: number;
  last_updated: string;
}

export interface TimeseriesPoint {
  hour: string;
  count: number;
  avg_mag: number;
  max_mag: number;
}

export interface TopRegionItem {
  region: string;
  count: number;
  avg_mag: number;
  max_mag?: number;
}

export interface ChartSuggestion {
  type: 'bar' | 'line' | 'area' | 'pie' | 'metric';
  title: string;
  x_key: string;
  y_key: string;
  secondary_y_key?: string;
}

export interface IntentCatalogMetadata {
  intent: 'conversational' | 'knowledge' | 'status' | 'analytics';
  subtype: string;
  confidence: number;
  target_location?: string;
  time_frame?: string;
  reasoning?: string;
  step1_latency_ms: number;
  total_latency_ms: number;
}

export interface ChatResponse {
  intent?: 'conversational' | 'knowledge' | 'status' | 'analytics';
  reply: string;
  sql?: string;
  data?: any[];
  chart_suggestion?: ChartSuggestion;
  row_count?: number;
  catalog?: IntentCatalogMetadata;
}

export interface PinnedChart {
  id: string;
  title: string;
  type: 'bar' | 'line' | 'area' | 'pie' | 'metric';
  x_key: string;
  y_key: string;
  sql: string;
  data: any[];
  pinnedAt: string;
}

export interface AiReport {
  id: number;
  report_date: string;
  title: string;
  executive_summary: string;
  active_zones: { place: string; count: number }[];
  highlighted_events: { place: string; mag: number; depth_km: number }[];
  ai_verified: boolean;
  generated_at: string;
}

export interface PipelineTelemetry {
  overall_health: string;
  data_freshness_status: string;
  last_sync_utc: string;
  quality_score_avg: number;
  dags: Record<string, {
    dag_id: string;
    last_run: string;
    state: string;
    schedule: string;
    freshness_minutes?: number;
    quality_score?: number;
    ai_status?: string;
  }>;
  admin_telemetry?: {
    total_invalid_events_intercepted: number;
    minio_bucket_status: string;
    duckdb_memory_status: string;
    ollama_agent_status: string;
  };
}

export interface UserSession {
  username: string;
  role: 'viewer' | 'admin';
  token: string;
}
