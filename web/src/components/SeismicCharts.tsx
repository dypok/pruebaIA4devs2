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
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      
      {/* Gráfico 1: Actividad Sísmica por Hora */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3 border-b border-slate-800/80 pb-2">
          <div>
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
              Actividad Sísmica por Hora (24h)
            </h3>
            <p className="text-[11px] text-slate-400">Frecuencia y magnitud promedio por ventana</p>
          </div>
          <span className="text-[10px] font-mono text-slate-400">DuckDB Agg</span>
        </div>

        <div className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={timeseries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0284c7" stopOpacity={0.4}/>
                  <stop offset="95%" stopColor="#0284c7" stopOpacity={0.0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="hour" stroke="#64748b" fontSize={10} tickLine={false} />
              <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '4px' }}
                itemStyle={{ color: '#38bdf8' }}
              />
              <Area type="monotone" dataKey="count" stroke="#0284c7" strokeWidth={2} fillOpacity={1} fill="url(#colorCount)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Gráfico 2: Top Regiones Activas */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3 border-b border-slate-800/80 pb-2">
          <div>
            <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
              Regiones de Mayor Concentración
            </h3>
            <p className="text-[11px] text-slate-400">Conteo total de sismos por territorio</p>
          </div>
          <span className="text-[10px] font-mono text-slate-400">Top 5</span>
        </div>

        <div className="h-48 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={topRegions} layout="vertical" margin={{ top: 5, right: 15, left: 35, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
              <XAxis type="number" stroke="#64748b" fontSize={10} tickLine={false} />
              <YAxis type="category" dataKey="region" stroke="#94a3b8" fontSize={10} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '4px' }}
                itemStyle={{ color: '#38bdf8' }}
              />
              <Bar dataKey="count" fill="#38bdf8" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  );
};
