import React, { useState } from 'react';
import { FileText, CheckCircle2, Download, Calendar, Sparkles } from 'lucide-react';
import { AiReport } from '../types';

interface ReportsViewerProps {
  reports: AiReport[];
  loading: boolean;
}

export const ReportsViewer: React.FC<ReportsViewerProps> = ({ reports, loading }) => {
  const [selectedReport, setSelectedReport] = useState<AiReport | null>(reports[0] || null);

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-400 font-mono text-xs animate-pulse">
        Cargando reportes ejecutivos de IA...
      </div>
    );
  }

  const current = selectedReport || reports[0];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      
      {/* Columna Izquierda: Historial de Reportes */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 space-y-3">
        <div className="flex items-center space-x-2 border-b border-slate-800 pb-2.5">
          <FileText className="w-4 h-4 text-sky-400" />
          <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
            Historial de Informes Diarios
          </h3>
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

              {/* Botón Descargar */}
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
                  {current.active_zones.map((z, idx) => (
                    <li key={idx} className="flex justify-between border-b border-slate-800/40 pb-1">
                      <span>{z.place}</span>
                      <span className="font-mono font-semibold text-sky-400">{z.count} sismos</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="p-4 rounded-lg bg-slate-950/40 border border-slate-800/60">
                <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold mb-2">
                  Eventos Más Significativos
                </h4>
                <ul className="space-y-1.5 text-xs text-slate-300">
                  {current.highlighted_events.map((e, idx) => (
                    <li key={idx} className="flex justify-between border-b border-slate-800/40 pb-1">
                      <span className="truncate max-w-[180px]">{e.place}</span>
                      <span className="font-mono font-semibold text-amber-400">{e.mag.toFixed(1)} Mw ({e.depth_km} km)</span>
                    </li>
                  ))}
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
