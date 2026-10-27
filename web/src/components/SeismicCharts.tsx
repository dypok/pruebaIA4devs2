import React, { useState, useEffect } from 'react';
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
  Cell,
  LabelList,
} from 'recharts';
import { MapPin, Activity, Clock, Calendar, Filter } from 'lucide-react';
import { TimeseriesPoint, TopRegionItem } from '../types';
import { fetchTopRegions } from '../services/api';

interface SeismicChartsProps {
  timeseries: TimeseriesPoint[];
  topRegions?: TopRegionItem[];
  onSelectRegion?: (region: string) => void;
}

export const SeismicCharts: React.FC<SeismicChartsProps> = ({
  timeseries,
  topRegions: initialTopRegions = [],
  onSelectRegion,
}) => {
  const [timeWindow, setTimeWindow] = useState<'24h' | '30d'>('24h');
  const [regions, setRegions] = useState<TopRegionItem[]>(initialTopRegions);
  const [loadingRegions, setLoadingRegions] = useState(false);

  const total24h = timeseries.reduce((acc, curr) => acc + (curr.count || 0), 0);

  // Cargar datos de regiones según la ventana seleccionada
  useEffect(() => {
    let active = true;
    setLoadingRegions(true);
    fetchTopRegions(timeWindow === '24h' ? 24 : undefined, 6)
      .then((data) => {
        if (active && data) {
          setRegions(data);
        }
      })
      .catch((err) => {
        console.error('Error actualizando regiones:', err);
        if (active && initialTopRegions.length > 0) {
          setRegions(initialTopRegions);
        }
      })
      .finally(() => {
        if (active) setLoadingRegions(false);
      });

    return () => {
      active = false;
    };
  }, [timeWindow]);

  // Si cambian los datos iniciales y la lista está vacía, sincronizar
  useEffect(() => {
    if (initialTopRegions && initialTopRegions.length > 0 && regions.length === 0) {
      setRegions(initialTopRegions);
    }
  }, [initialTopRegions]);

  // Paleta cromática según intensidad sísmica promedio
  const getRegionColor = (avgMag: number) => {
    if (avgMag >= 4.0) return '#f43f5e'; // Rose-500 (Muy significativo / Fuerte)
    if (avgMag >= 2.5) return '#f97316'; // Orange-500 (Moderado)
    if (avgMag >= 1.5) return '#eab308'; // Amber-500 (Leve)
    return '#38bdf8'; // Sky-400 (Micro / Menor)
  };

  const handleRegionClick = (regionName: string) => {
    if (!onSelectRegion) return;
    // Extraer nombre base de búsqueda (ej. "California, USA" -> "California")
    const cleanTerm = regionName.split(',')[0].trim();
    onSelectRegion(cleanTerm);
  };

  // Tooltip enriquecido para Regiones
  const CustomRegionTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload as TopRegionItem;
      const color = getRegionColor(data.avg_mag);
      return (
        <div className="bg-slate-900/95 border border-slate-700/80 rounded-lg p-3 shadow-2xl backdrop-blur-md text-xs font-sans min-w-[210px] z-50">
          <div className="flex items-center gap-1.5 font-bold text-slate-100 mb-2 border-b border-slate-800 pb-1.5">
            <MapPin size={14} className="text-sky-400 flex-shrink-0" />
            <span className="truncate">{data.region}</span>
          </div>
          <div className="space-y-1.5 font-mono text-[11px]">
            <div className="flex items-center justify-between text-slate-300">
              <span className="text-slate-400">Total sismos:</span>
              <span className="font-bold text-white text-xs">{data.count.toLocaleString()}</span>
            </div>
            <div className="flex items-center justify-between text-slate-300">
              <span className="text-slate-400">Mag. promedio:</span>
              <span className="font-semibold px-1.5 py-0.5 rounded text-[10px]" style={{ color, backgroundColor: `${color}18` }}>
                {data.avg_mag.toFixed(2)} Mw
              </span>
            </div>
            {data.max_mag !== undefined && data.max_mag > 0 && (
              <div className="flex items-center justify-between text-slate-300">
                <span className="text-slate-400">Mag. máxima:</span>
                <span className="font-semibold text-rose-400">
                  {data.max_mag.toFixed(1)} Mw
                </span>
              </div>
            )}
          </div>
          <div className="mt-2.5 pt-1.5 border-t border-slate-800/80 text-[10px] text-sky-400 flex items-center gap-1">
            <Filter size={11} />
            <span>Clic para filtrar la tabla de eventos</span>
          </div>
        </div>
      );
    }
    return null;
  };

  // Tooltip enriquecido para Serie Temporal
  const CustomTimeseriesTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload as TimeseriesPoint;
      return (
        <div className="bg-slate-900/95 border border-slate-700/80 rounded-lg p-2.5 shadow-2xl backdrop-blur-md text-xs font-sans z-50">
          <div className="font-semibold text-slate-200 mb-1 border-b border-slate-800 pb-1 flex items-center gap-1">
            <Clock size={12} className="text-sky-400" />
            <span>Hora UTC: {label}</span>
          </div>
          <div className="flex items-center justify-between gap-4 text-sky-400 font-mono">
            <span>Frecuencia:</span>
            <span className="font-bold">{data.count} sismos</span>
          </div>
          {data.avg_mag > 0 && (
            <div className="flex items-center justify-between gap-4 text-amber-400 font-mono mt-0.5">
              <span>Mag. promedio:</span>
              <span>{data.avg_mag.toFixed(2)} Mw</span>
            </div>
          )}
          {data.max_mag > 0 && (
            <div className="flex items-center justify-between gap-4 text-rose-400 font-mono mt-0.5">
              <span>Mag. máxima:</span>
              <span>{data.max_mag.toFixed(1)} Mw</span>
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      
      {/* Gráfico 1: Actividad Sísmica por Hora */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 min-w-0 flex flex-col justify-between">
        <div className="flex items-center justify-between mb-3 border-b border-slate-800/80 pb-2">
          <div>
            <div className="flex items-center gap-1.5">
              <Activity size={14} className="text-sky-400" />
              <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
                Actividad Sísmica por Hora (24h)
              </h3>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">Frecuencia y magnitud promedio por ventana</p>
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
                <Tooltip content={<CustomTimeseriesTooltip />} />
                <Area type="monotone" dataKey="count" stroke="#0284c7" strokeWidth={2} fillOpacity={1} fill="url(#colorCount)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Gráfico 2: Top Regiones de Mayor Concentración */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-4 min-w-0 flex flex-col justify-between">
        <div className="flex items-center justify-between mb-3 border-b border-slate-800/80 pb-2">
          <div>
            <div className="flex items-center gap-1.5">
              <MapPin size={14} className="text-sky-400" />
              <h3 className="text-xs font-mono uppercase tracking-wider text-slate-300 font-semibold">
                Regiones de Mayor Concentración
              </h3>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">Top zonas por frecuencia e intensidad sísmica</p>
          </div>
          
          {/* Selector de ventana temporal para regiones */}
          <div className="flex items-center bg-slate-950/80 border border-slate-800 rounded p-0.5 text-[10px] font-mono">
            <button
              onClick={() => setTimeWindow('24h')}
              className={`flex items-center gap-1 px-2 py-0.5 rounded transition-colors ${
                timeWindow === '24h'
                  ? 'bg-sky-500/20 text-sky-300 font-semibold border border-sky-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Filtrar por eventos de las últimas 24 horas"
            >
              <Clock size={10} />
              <span>24 Horas</span>
            </button>
            <button
              onClick={() => setTimeWindow('30d')}
              className={`flex items-center gap-1 px-2 py-0.5 rounded transition-colors ${
                timeWindow === '30d'
                  ? 'bg-sky-500/20 text-sky-300 font-semibold border border-sky-500/30'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Filtrar por eventos del catálogo histórico (30 días)"
            >
              <Calendar size={10} />
              <span>30 Días</span>
            </button>
          </div>
        </div>

        {loadingRegions ? (
          <div className="h-52 flex items-center justify-center text-slate-400 font-mono text-xs">
            <span className="animate-pulse">Cargando distribución regional desde DuckDB...</span>
          </div>
        ) : regions.length === 0 ? (
          <div className="h-52 flex items-center justify-center text-slate-500 font-mono text-xs text-center p-4">
            Sin datos de concentración regional registrados en DuckDB.
          </div>
        ) : (
          <div className="h-48 w-full" style={{ minHeight: '192px', minWidth: 0 }}>
            <ResponsiveContainer width="100%" height={192}>
              <BarChart
                data={regions}
                layout="vertical"
                margin={{ top: 4, right: 35, left: 0, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                <XAxis
                  type="number"
                  stroke="#64748b"
                  fontSize={10}
                  tickLine={false}
                  axisLine={false}
                  allowDecimals={false}
                />
                <YAxis
                  type="category"
                  dataKey="region"
                  stroke="#94a3b8"
                  fontSize={11}
                  width={122}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: '#cbd5e1', fontSize: 11 }}
                />
                <Tooltip
                  content={<CustomRegionTooltip />}
                  cursor={{ fill: 'rgba(255, 255, 255, 0.04)' }}
                />
                <Bar
                  dataKey="count"
                  radius={[0, 4, 4, 0]}
                  onClick={(entry: any) => {
                    const reg = entry?.region || entry?.payload?.region;
                    if (reg) handleRegionClick(reg);
                  }}
                  className="cursor-pointer"
                >
                  {regions.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={getRegionColor(entry.avg_mag)}
                      onClick={() => handleRegionClick(entry.region)}
                      className="transition-opacity hover:opacity-80 cursor-pointer"
                    />
                  ))}
                  <LabelList
                    dataKey="count"
                    position="right"
                    fill="#94a3b8"
                    fontSize={10}
                    fontFamily="monospace"
                    formatter={(val: any) => `${val}`}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Leyenda de intensidades y guía de interacción */}
        <div className="flex items-center justify-between pt-2 mt-1 border-t border-slate-800/60 text-[10px] text-slate-400 font-mono">
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-[#38bdf8] inline-block"></span>
              &lt; 1.5 Mw
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-[#eab308] inline-block"></span>
              1.5 - 2.5 Mw
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-[#f97316] inline-block"></span>
              &ge; 2.5 Mw
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-[#f43f5e] inline-block"></span>
              &ge; 4.0 Mw
            </span>
          </div>
          <span className="text-slate-500 hidden sm:inline">Clic en barra para filtrar</span>
        </div>

      </div>

    </div>
  );
};
