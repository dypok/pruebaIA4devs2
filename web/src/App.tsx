import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { MetricRibbon } from './components/MetricRibbon';
import { SeismicMap } from './components/SeismicMap';
import { PinnedChartsGrid } from './components/PinnedChartsGrid';
import { SeismicCharts } from './components/SeismicCharts';
import { EventsTable } from './components/EventsTable';
import { ReportsViewer } from './components/ReportsViewer';
import { PipelineStatus } from './components/PipelineStatus';
import { ChatbotDrawer } from './components/ChatbotDrawer';
import { LoginPage } from './components/LoginPage';
import { useAuth } from './context/AuthContext';
import {
  KpiData,
  SeismicEvent,
  TimeseriesPoint,
  TopRegionItem,
  AiReport,
  PinnedChart,
} from './types';
import {
  fetchKpis,
  fetchEvents,
  fetchTimeseries,
  fetchTopRegions,
  fetchReports,
} from './services/api';

export const AppContent: React.FC = () => {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  const [activeTab, setActiveTab] = useState<'dashboard' | 'reports' | 'pipeline'>('dashboard');
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [isLive, setIsLive] = useState(false);

  // Estados de datos
  const [kpis, setKpis] = useState<KpiData | null>(null);
  const [events, setEvents] = useState<SeismicEvent[]>([]);
  const [totalEvents, setTotalEvents] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [minMagnitude, setMinMagnitude] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [timeseries, setTimeseries] = useState<TimeseriesPoint[]>([]);
  const [topRegions, setTopRegions] = useState<TopRegionItem[]>([]);
  const [reports, setReports] = useState<AiReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [dataError, setDataError] = useState<string | null>(null);

  // Gráficos fijados desde el Chatbot (persistidos en localStorage)
  const [pinnedCharts, setPinnedCharts] = useState<PinnedChart[]>(() => {
    try {
      const saved = localStorage.getItem('sismowatch_pinned_charts');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Guardar gráficos fijados en localStorage
  useEffect(() => {
    localStorage.setItem('sismowatch_pinned_charts', JSON.stringify(pinnedCharts));
  }, [pinnedCharts]);

  const handlePinChart = (chart: PinnedChart) => {
    setPinnedCharts((prev) => [chart, ...prev]);
  };

  const handleUnpinChart = (id: string) => {
    setPinnedCharts((prev) => prev.filter((c) => c.id !== id));
  };

  // Carga inicial de datos reales
  const loadInitialData = async () => {
    setDataError(null);
    try {
      const [kpisData, eventsData, timeseriesData, regionsData, reportsData] = await Promise.all([
        fetchKpis(),
        fetchEvents({ page, page_size: pageSize, min_magnitude: minMagnitude, region: searchQuery }),
        fetchTimeseries(),
        fetchTopRegions(),
        fetchReports(),
      ]);

      if (kpisData) setKpis(kpisData);
      if (eventsData) {
        setEvents(eventsData.events || []);
        setTotalEvents(eventsData.total || 0);
      }
      if (timeseriesData) setTimeseries(timeseriesData);
      if (regionsData) setTopRegions(regionsData);
      if (reportsData) setReports(reportsData);
    } catch (e: any) {
      console.error('Error cargando datos reales:', e);
      setDataError(e.message || 'Error consultando datos del Lakehouse');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      loadInitialData();
    }
  }, [isAuthenticated, page, minMagnitude, searchQuery]);

  // Conexión Server-Sent Events (SSE) para tiempo real
  useEffect(() => {
    if (!isAuthenticated) return;
    const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const token = localStorage.getItem('sismowatch_token');
    if (!token) return;
    const sseUrl = `${API_BASE}/api/stream?token=${encodeURIComponent(token)}`;

    let eventSource: EventSource | null = null;
    try {
      eventSource = new EventSource(sseUrl);

      eventSource.onopen = () => {
        setIsLive(true);
      };

      eventSource.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === 'SEISMIC_UPDATE' && payload.latest_events) {
            setEvents((prev) => {
              const newItems = payload.latest_events.filter(
                (item: SeismicEvent) => !prev.some((p) => p.id === item.id)
              );
              return [...newItems, ...prev].slice(0, 50);
            });
            // Refrescar KPIs
            fetchKpis().then((k) => k && setKpis(k)).catch(() => {});
          }
        } catch (err) {
          // Heartbeat ping o mensaje no json
        }
      };

      eventSource.onerror = () => {
        setIsLive(false);
      };
    } catch (e) {
      setIsLive(false);
    }

    return () => {
      if (eventSource) eventSource.close();
    };
  }, [isAuthenticated]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isChatOpen={isChatOpen}
        setIsChatOpen={setIsChatOpen}
        isLive={isLive}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Banner de Error Literal si falla alguna consulta */}
        {dataError && (
          <div className="p-3 bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-mono rounded flex items-center justify-between">
            <span><b>Error de Datos:</b> {dataError}</span>
            <button onClick={() => setDataError(null)} className="text-slate-400 hover:text-white">&times;</button>
          </div>
        )}

        {/* Ribbon de Métricas (Siempre visible en Dashboard) */}
        {activeTab === 'dashboard' && (
          <MetricRibbon kpis={kpis} loading={loading} />
        )}

        {/* Tab 1: Dashboard Principal */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Mapa Sísmico Interactivo */}
            <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2 px-1">
                <span className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">
                  Cartografía Sísmica Global (Leaflet Dark Matter)
                </span>
                <span className="text-[11px] font-mono text-slate-400">
                  {events.length} sismos proyectados
                </span>
              </div>
              <SeismicMap events={events} />
            </div>

            {/* Sección de Gráficos Fijados desde el Chatbot IA (Requisito clave) */}
            <PinnedChartsGrid
              pinnedCharts={pinnedCharts}
              onUnpin={handleUnpinChart}
              onRefreshAll={loadInitialData}
            />

            {/* Gráficos de Serie Temporal y Regiones Reales */}
            <SeismicCharts
              timeseries={timeseries}
              topRegions={topRegions}
            />

            {/* Tabla de Eventos Paginada con Filtros */}
            <EventsTable
              events={events}
              total={totalEvents}
              page={page}
              pageSize={pageSize}
              onPageChange={setPage}
              minMagnitude={minMagnitude}
              onMinMagChange={setMinMagnitude}
              searchQuery={searchQuery}
              onSearchChange={setSearchQuery}
            />
          </div>
        )}

        {/* Tab 2: Reportes de IA */}
        {activeTab === 'reports' && (
          <ReportsViewer reports={reports} loading={loading} />
        )}

        {/* Tab 3: Pipeline y Gobernanza */}
        {activeTab === 'pipeline' && (
          <PipelineStatus />
        )}
      </main>

      {/* Drawer Deslizable del Chatbot con Qwen 2.5:2b */}
      <ChatbotDrawer
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        onPinChart={handlePinChart}
      />
    </div>
  );
};

export const App: React.FC = () => {
  return <AppContent />;
};

export default App;
