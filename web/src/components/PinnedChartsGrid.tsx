import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { PinOff, RefreshCw, Sparkles } from 'lucide-react';
import { PinnedChart } from '../types';

interface PinnedChartsGridProps {
  pinnedCharts: PinnedChart[];
  onUnpin: (id: string) => void;
  onRefreshAll?: () => void;
}

export const PinnedChartsGrid: React.FC<PinnedChartsGridProps> = ({
  pinnedCharts,
  onUnpin,
  onRefreshAll,
}) => {
  if (pinnedCharts.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-sky-400" />
          <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
            Visualizaciones Personalizadas (Fijadas desde Chatbot IA)
          </h3>
          <span className="text-[11px] font-mono text-slate-400">({pinnedCharts.length})</span>
        </div>
        {onRefreshAll && (
          <button
            onClick={onRefreshAll}
            className="flex items-center space-x-1 text-[11px] font-mono text-slate-400 hover:text-sky-400 transition-colors"
            title="Sincronizar con datos en vivo"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Actualizar Todo</span>
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {pinnedCharts.map((chart) => (
          <div
            key={chart.id}
            className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 flex flex-col justify-between"
          >
            {/* Header del gráfico */}
            <div className="flex items-start justify-between mb-3">
              <div>
                <h4 className="text-sm font-semibold text-slate-200">{chart.title}</h4>
                <p className="text-[10px] font-mono text-slate-400 mt-0.5 truncate max-w-sm" title={chart.sql}>
                  SQL: {chart.sql}
                </p>
              </div>
              <button
                onClick={() => onUnpin(chart.id)}
                className="text-slate-400 hover:text-rose-400 p-1 rounded hover:bg-slate-800 transition-colors"
                title="Desfijar del Dashboard"
              >
                <PinOff className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Renderizado dinámico del gráfico */}
            <div className="h-56 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                {chart.type === 'line' ? (
                  <LineChart data={chart.data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey={chart.x_key} stroke="#64748b" fontSize={11} tickLine={false} />
                    <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '6px' }}
                      itemStyle={{ color: '#38bdf8' }}
                    />
                    <Line type="monotone" dataKey={chart.y_key} stroke="#38bdf8" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                ) : (
                  <BarChart data={chart.data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey={chart.x_key} stroke="#64748b" fontSize={11} tickLine={false} />
                    <YAxis stroke="#64748b" fontSize={11} tickLine={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '6px' }}
                      itemStyle={{ color: '#38bdf8' }}
                    />
                    <Bar dataKey={chart.y_key} fill="#0284c7" radius={[4, 4, 0, 0]} />
                  </BarChart>
                )}
              </ResponsiveContainer>
            </div>

            {/* Footer con timestamp */}
            <div className="mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] font-mono text-slate-400">
              <span>Tipo: {chart.type.toUpperCase()}</span>
              <span>Fijado: {new Date(chart.pinnedAt).toLocaleTimeString()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
