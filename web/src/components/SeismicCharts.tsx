import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { TimeseriesPoint } from '../types';

interface SeismicChartsProps {
  timeseries: TimeseriesPoint[];
  topRegions: { region: string; count: number; avg_mag: number }[];
}

export const SeismicCharts: React.FC<SeismicChartsProps> = ({ timeseries, topRegions }) => {
  const total24h = timeseries.reduce((acc, curr) => acc + (curr.count || 0), 0);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      
      {/* Gráfico 1: Actividad Sísmica por Hora */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 min-w-0 flex flex-col justify-between">
        <div className="flex items-center justify-between mb-3 border-b border-slate-800/80 pb-2">
          <div>
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
              Actividad Sísmica por Hora (24h)
            </h3>
            <p className="text-[11px] text-slate-400">Frecuencia y magnitud promedio por ventana</p>
          </div>
          <div className="text-right">
            <span className="text-[10px] font-mono text-sky-400 bg-sky-500/10 px-2 py-0.5 rounded border border-sky-500/20">
              {total24h} eventos
            </span>
          </div>
        </div>

        {timeseries.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-slate-500 font-mono text-xs text-center p-4">
            Sin datos de actividad temporal disponibles en DuckDB.
          </div>
        ) : (
          <div className="h-48 w-full" style={{ minHeight: '192px', minWidth: 0 }}>
            <ResponsiveContainer width="100%" height={192}>
              <AreaChart data={timeseries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#0284c7" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="#0284c7" stopOpacity={0.0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="hour" stroke="#64748b" fontSize={10} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={10} tickLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '4px' }}
                  itemStyle={{ color: '#38bdf8' }}
                  formatter={(value: any, name: string) => [
                    name === 'count' ? `${value} sismos` : value,
                    name === 'count' ? 'Frecuencia' : name
                  ]}
                  labelFormatter={(label) => `Hora UTC: ${label}`}
                />
                <Area type="monotone" dataKey="count" stroke="#0284c7" strokeWidth={2} fillOpacity={1} fill="url(#colorCount)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Gráfico 2: Top Regiones Activas */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 min-w-0 flex flex-col justify-between">
        <div className="flex items-center justify-between mb-3 border-b border-slate-800/80 pb-2">
          <div>
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
              Regiones de Mayor Concentración
            </h3>
            <p className="text-[11px] text-slate-400">Conteo total de sismos por territorio</p>
          </div>
          <span className="text-[10px] font-mono text-slate-400">Top 5</span>
        </div>

        {topRegions.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-slate-500 font-mono text-xs text-center p-4">
            Sin datos de concentración regional registrados en DuckDB.
          </div>
        ) : (
          <div className="h-48 w-full" style={{ minHeight: '192px', minWidth: 0 }}>
            <ResponsiveContainer width="100%" height={192}>
              <BarChart data={topRegions} layout="vertical" margin={{ top: 5, right: 15, left: 35, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                <XAxis type="number" stroke="#64748b" fontSize={10} tickLine={false} allowDecimals={false} />
                <YAxis type="category" dataKey="region" stroke="#94a3b8" fontSize={10} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '4px' }}
                  itemStyle={{ color: '#38bdf8' }}
                  formatter={(value: any) => [`${value} sismos`, 'Total']}
                />
                <Bar dataKey="count" fill="#38bdf8" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

    </div>
  );
};
