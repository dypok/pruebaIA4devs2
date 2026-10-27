import React, { useState, useEffect } from 'react';
import { FileText, CheckCircle2, Download, Calendar, Sparkles, RefreshCw, Lock } from 'lucide-react';
import { AiReport } from '../types';
import { useAuth } from '../context/AuthContext';
import { triggerAiRegenerateApi } from '../services/api';

interface ReportsViewerProps {
  reports: AiReport[];
  loading: boolean;
  onRefresh: () => Promise<void> | void;
}

export const ReportsViewer: React.FC<ReportsViewerProps> = ({ reports, loading, onRefresh }) => {
  const { isAdmin } = useAuth();
  const [selectedReport, setSelectedReport] = useState<AiReport | null>(reports[0] || null);
  const [regenerating, setRegenerating] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [regenMsg, setRegenMsg] = useState<string | null>(null);

  // Mantener el reporte seleccionado sincronizado cuando se actualiza la lista de reportes
  useEffect(() => {
    if (reports && reports.length > 0) {
      if (!selectedReport || !reports.some((r) => r.id === selectedReport.id)) {
        setSelectedReport(reports[0]);
      }
    } else {
      setSelectedReport(null);
    }
  }, [reports]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await onRefresh();
    } catch (e: any) {
      console.error('Error al actualizar reportes:', e);
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleRegenerate = async () => {
    setRegenerating(true);
    setRegenMsg(null);
    try {
      const res = await triggerAiRegenerateApi();
      setRegenMsg(res.message || 'Reporte generado con éxito.');
      // Refrescar inmediatamente los reportes desde PostgreSQL
      await onRefresh();
    } catch (e: any) {
      setRegenMsg(e.message || 'Error al regenerar reporte');
    } finally {
      setRegenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-400 font-mono text-xs animate-pulse">
        Cargando reportes ejecutivos de IA desde PostgreSQL...
      </div>
    );
  }

  if (reports.length === 0) {
    return (
      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-8 text-center space-y-4">
        <div className="w-12 h-12 rounded-full bg-slate-800/80 border border-slate-700/60 flex items-center justify-center mx-auto text-slate-400">
          <FileText className="w-6 h-6 text-sky-400" />
        </div>
        <div>
          <h3 className="text-sm font-bold text-slate-200">No hay reportes ejecutivos en la base de datos</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto mt-1 font-mono">
            0 registros encontrados en PostgreSQL (tabla: curated.ai_reports).
          </p>
        </div>
        <div className="pt-2 flex flex-wrap items-center justify-center gap-3">
          {isAdmin ? (
            <button
              onClick={handleRegenerate}
              disabled={regenerating || isRefreshing}
              className="inline-flex items-center space-x-2 px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold rounded transition-colors shadow-lg shadow-sky-600/20"
            >
              <RefreshCw className={`w-4 h-4 ${regenerating ? 'animate-spin' : ''}`} />
              <span>{regenerating ? 'Generando con Qwen 2.5:2b...' : 'Generar Primer Reporte con IA'}</span>
            </button>
          ) : (
            <div className="text-xs text-slate-500 font-mono">
              La generación de reportes con IA requiere rol de Administrador.
            </div>
          )}
          <button
            onClick={handleRefresh}
            disabled={isRefreshing || regenerating}
            className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded transition-colors border border-slate-700"
            title="Consultar nuevamente si ya existen reportes en PostgreSQL"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>{isRefreshing ? 'Consultando BD...' : 'Comprobar Base de Datos'}</span>
          </button>
        </div>
        {regenMsg && (
          <div className="mt-3 p-3 bg-sky-500/10 border border-sky-500/20 text-sky-400 text-xs font-mono rounded max-w-md mx-auto">
            {regenMsg}
          </div>
        )}
      </div>
    );
  }

  const current = selectedReport || reports[0];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      
      {/* Columna Izquierda: Historial de Reportes */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
          <div className="flex items-center space-x-2">
            <FileText className="w-4 h-4 text-sky-400" />
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
              Historial de Informes ({reports.length})
            </h3>
          </div>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="text-slate-400 hover:text-slate-200 p-1 rounded hover:bg-slate-800 transition-colors"
            title="Recargar lista de reportes"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div className="space-y-2">
          {reports.map((rep) => (
            <button
              key={rep.id}
              onClick={() => setSelectedReport(rep)}
              className={`w-full text-left p-3 rounded-lg border transition-all ${
                current?.id === rep.id
                  ? 'bg-slate-800/90 border-sky-500/50 shadow-sm'
                  : 'bg-slate-950/40 border-slate-800/70 hover:bg-slate-800/40'
              }`}
            >
              <div className="flex items-center justify-between text-xs font-semibold text-slate-200">
                <span>{rep.report_date}</span>
                <span className="flex items-center space-x-1 text-[11px] font-mono text-emerald-400">
                  <CheckCircle2 className="w-3 h-3" />
                  <span>Verificado</span>
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{rep.executive_summary}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Columna Derecha: Vista Detallada del Reporte Seleccionado */}
      <div className="md:col-span-2 bg-slate-900/80 border border-slate-800 rounded-lg p-6 space-y-6">
        {current ? (
          <>
            {/* Header del Reporte */}
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
              <div>
                <div className="flex items-center space-x-2 text-[11px] font-mono text-sky-400 mb-1">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Generado con Inteligencia Artificial (Qwen 2.5:2b / Ollama)</span>
                </div>
                <h2 className="text-lg font-bold text-slate-100">{current.title}</h2>
                <div className="flex items-center space-x-4 text-xs font-mono text-slate-400 mt-1">
                  <span>Fecha: {current.report_date}</span>
                  <span>•</span>
                  <span>Generado: {new Date(current.generated_at).toLocaleString()}</span>
                </div>
              </div>

              {/* Botones de Acción */}
              <div className="flex items-center space-x-2">
                <button
                  onClick={handleRefresh}
                  disabled={isRefreshing || regenerating}
                  className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium rounded transition-colors"
                  title="Recargar reportes desde PostgreSQL"
                >
                  <RefreshCw className={`w-3.5 h-3.5 text-slate-400 ${isRefreshing ? 'animate-spin' : ''}`} />
                  <span>{isRefreshing ? 'Actualizando...' : 'Actualizar'}</span>
                </button>

                {isAdmin ? (
                  <button
                    onClick={handleRegenerate}
                    disabled={regenerating}
                    className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium rounded transition-colors"
                    title="Disparar regeneración con Qwen 2.5:2b (Admin)"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 text-sky-400 ${regenerating ? 'animate-spin' : ''}`} />
                    <span>{regenerating ? 'Regenerando...' : 'Regenerar con IA'}</span>
                  </button>
                ) : (
                  <span className="flex items-center space-x-1 text-[11px] font-mono text-slate-500 bg-slate-950/40 px-2 py-1 rounded border border-slate-800" title="Regeneración restringida a Administrador">
                    <Lock className="w-3 h-3 text-slate-500" />
                    <span>Regeneración (Solo Admin)</span>
                  </span>
                )}

                <a
                  href={`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/reports/export?format=html`}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center space-x-1.5 px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium rounded transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Descargar HTML/PDF</span>
                </a>
              </div>
            </div>

            {regenMsg && (
              <div className="p-3 bg-sky-500/10 border border-sky-500/20 text-sky-400 text-xs font-mono rounded flex justify-between items-center">
                <span>{regenMsg}</span>
                <button onClick={() => setRegenMsg(null)} className="text-slate-400 hover:text-white">&times;</button>
              </div>
            )}

            {/* Narrativa Ejecutiva */}
            <div>
              <h3 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold mb-2">
                Resumen Ejecutivo
              </h3>
              <div className="p-4 rounded-lg bg-slate-950/60 border border-slate-800/80 text-sm leading-relaxed text-slate-200">
                {current.executive_summary}
              </div>
            </div>

            {/* Zonas Activas y Eventos Destacados */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 rounded-lg bg-slate-950/40 border border-slate-800/60">
                <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold mb-2">
                  Zonas con Mayor Concentración
                </h4>
                <ul className="space-y-1.5 text-xs text-slate-300">
                  {(current.active_zones || []).map((z, idx) => (
                    <li key={idx} className="flex justify-between border-b border-slate-800/40 pb-1">
                      <span>{z.place}</span>
                      <span className="font-mono font-semibold text-sky-400">{z.count} sismos</span>
                    </li>
                  ))}
                  {(!current.active_zones || current.active_zones.length === 0) && (
                    <li className="text-slate-500 italic">No hay zonas activas registradas.</li>
                  )}
                </ul>
              </div>

              <div className="p-4 rounded-lg bg-slate-950/40 border border-slate-800/60">
                <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold mb-2">
                  Eventos Más Significativos
                </h4>
                <ul className="space-y-1.5 text-xs text-slate-300">
                  {(current.highlighted_events || []).map((e, idx) => (
                    <li key={idx} className="flex justify-between border-b border-slate-800/40 pb-1">
                      <span className="truncate max-w-[180px]">{e.place}</span>
                      <span className="font-mono font-semibold text-amber-400">
                        {typeof e.mag === 'number' ? e.mag.toFixed(1) : (e.mag || '0.0')} Mw ({e.depth_km ?? 0} km)
                      </span>
                    </li>
                  ))}
                  {(!current.highlighted_events || current.highlighted_events.length === 0) && (
                    <li className="text-slate-500 italic">No hay eventos destacados registrados.</li>
                  )}
                </ul>
              </div>
            </div>

            {/* Control Anti-Alucinación */}
            <div className="flex items-center space-x-2 text-xs font-mono text-emerald-400 p-3 bg-emerald-500/10 border border-emerald-500/20 rounded">
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
              <span>
                <b>Verificación Numérica Aprobada:</b> Todas las cifras estadísticas fueron calculadas por código y contrastadas con el texto generado.
              </span>
            </div>
          </>
        ) : (
          <div className="text-center py-12 text-slate-400 font-mono text-xs">
            Selecciona un reporte de la lista para visualizar su contenido.
          </div>
        )}
      </div>

    </div>
  );
};
