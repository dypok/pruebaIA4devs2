import React from 'react';
import { Search, ChevronLeft, ChevronRight, Download } from 'lucide-react';
import { SeismicEvent } from '../types';

interface EventsTableProps {
  events: SeismicEvent[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (p: number) => void;
  minMagnitude: number;
  onMinMagChange: (m: number) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
}

export const EventsTable: React.FC<EventsTableProps> = ({
  events,
  total,
  page,
  pageSize,
  onPageChange,
  minMagnitude,
  onMinMagChange,
  searchQuery,
  onSearchChange,
}) => {
  const totalPages = Math.ceil(total / pageSize) || 1;

  const handleExport = (format: 'csv' | 'html') => {
    const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const token = localStorage.getItem('sismowatch_token');
    const url = `${API_BASE}/api/reports/export?format=${format}`;
    window.open(url, '_blank');
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-lg overflow-hidden">
      {/* Barra de Filtros */}
      <div className="p-3 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3 bg-slate-950/40">
        <div className="flex items-center space-x-3 flex-1 min-w-[280px]">
          {/* Buscador de región */}
          <div className="relative flex-1 max-w-sm">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Filtrar por región (ej. California, Chile, Japan)..."
              className="w-full pl-9 pr-3 py-1.5 bg-slate-900 border border-slate-700/80 rounded text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:border-sky-500 font-sans"
            />
          </div>

          {/* Selector de Magnitud Mínima */}
          <div className="flex items-center space-x-2 text-xs font-mono text-slate-300">
            <span className="text-slate-400">Min Mag:</span>
            <select
              value={minMagnitude}
              onChange={(e) => onMinMagChange(parseFloat(e.target.value))}
              className="bg-slate-900 border border-slate-700/80 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-sky-500"
            >
              <option value="0">Todos (&ge; 0.0)</option>
              <option value="2.5">&ge; 2.5</option>
              <option value="4.0">&ge; 4.0</option>
              <option value="5.0">&ge; 5.0</option>
              <option value="6.0">&ge; 6.0</option>
            </select>
          </div>
        </div>

        {/* Botones de Exportación */}
        <div className="flex items-center space-x-2 text-xs font-mono">
          <button
            onClick={() => handleExport('csv')}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition-colors"
            title="Exportar a CSV"
          >
            <Download className="w-3.5 h-3.5 text-slate-400" />
            <span>CSV</span>
          </button>
          <button
            onClick={() => handleExport('html')}
            className="flex items-center space-x-1.5 px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded transition-colors"
            title="Exportar a Reporte HTML/PDF"
          >
            <Download className="w-3.5 h-3.5 text-slate-400" />
            <span>HTML</span>
          </button>
        </div>
      </div>

      {/* Tabla de Datos (con status dots, sin badges) */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="border-b border-slate-800 text-[11px] font-mono uppercase text-slate-400 bg-slate-950/60">
              <th className="py-2.5 px-4 font-semibold">Magnitud</th>
              <th className="py-2.5 px-4 font-semibold">Ubicación / Epicentro</th>
              <th className="py-2.5 px-4 font-semibold">Profundidad</th>
              <th className="py-2.5 px-4 font-semibold">Fecha (UTC)</th>
              <th className="py-2.5 px-4 font-semibold text-center">Tsunami</th>
              <th className="py-2.5 px-4 font-semibold text-right">Estado</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-sans">
            {events.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-400 font-mono text-xs">
                  No se encontraron eventos sísmicos con los filtros aplicados.
                </td>
              </tr>
            ) : (
              events.map((ev) => (
                <tr key={ev.id} className="hover:bg-slate-800/40 transition-colors">
                  {/* Magnitud con tipografía destacada */}
                  <td className="py-2.5 px-4 font-mono font-bold text-sm">
                    <span className={
                      ev.mag >= 6.0 ? 'text-rose-400' : ev.mag >= 4.5 ? 'text-orange-400' : ev.mag >= 3.0 ? 'text-amber-400' : 'text-emerald-400'
                    }>
                      {ev.mag.toFixed(1)}
                    </span>
                    <span className="text-[10px] text-slate-400 ml-1 font-normal font-sans">{ev.mag_type}</span>
                  </td>

                  {/* Ubicación */}
                  <td className="py-2.5 px-4 text-slate-200 font-medium">{ev.place}</td>

                  {/* Profundidad */}
                  <td className="py-2.5 px-4 font-mono text-slate-300">{ev.depth_km} km</td>

                  {/* Fecha */}
                  <td className="py-2.5 px-4 font-mono text-slate-400">
                    {ev.time.slice(0, 19).replace('T', ' ')}
                  </td>

                  {/* Tsunami (status dot discreto) */}
                  <td className="py-2.5 px-4 text-center">
                    {ev.tsunami === 1 ? (
                      <span className="inline-flex items-center space-x-1 font-mono text-[11px] text-rose-400 font-semibold">
                        <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping inline-block" />
                        <span>Alerta</span>
                      </span>
                    ) : (
                      <span className="text-slate-400 font-mono text-[11px]">-</span>
                    )}
                  </td>

                  {/* Estado (status dot verde/gris) */}
                  <td className="py-2.5 px-4 text-right">
                    <span className="inline-flex items-center space-x-1.5 font-mono text-[11px] text-slate-300">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
                      <span className="capitalize">{ev.status}</span>
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Paginación */}
      <div className="p-3 border-t border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400 bg-slate-950/40">
        <div>
          Mostrando {events.length} de {total} registros
        </div>
        <div className="flex items-center space-x-2">
          <span>Página {page} de {totalPages}</span>
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:pointer-events-none transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="p-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:pointer-events-none transition-colors"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
