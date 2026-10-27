import React from 'react';
import { KpiData } from '../types';

interface MetricRibbonProps {
  kpis: KpiData | null;
  loading: boolean;
}

export const MetricRibbon: React.FC<MetricRibbonProps> = ({ kpis, loading }) => {
  if (loading || !kpis) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-lg p-4 animate-pulse">
        <div className="h-10 bg-slate-800/50 rounded w-full"></div>
      </div>
    );
  }

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-lg overflow-hidden">
      <div className="grid grid-cols-2 md:grid-cols-6 divide-y md:divide-y-0 md:divide-x divide-slate-800/80">
        
        {/* KPI 1: Total Eventos */}
        <div className="p-4 flex flex-col justify-between">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Eventos (24h)</span>
          <div className="mt-1 flex items-baseline space-x-2">
            <span className="text-2xl font-semibold tracking-tight text-slate-100">{kpis.total_events_24h}</span>
            <span className="text-[11px] text-slate-400 font-mono">sismos</span>
          </div>
        </div>

        {/* KPI 2: Magnitud Máxima */}
        <div className="p-4 flex flex-col justify-between">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Magnitud Máx</span>
          <div className="mt-1 flex items-baseline space-x-2">
            <span className={`text-2xl font-semibold tracking-tight ${
              kpis.max_magnitude >= 6.0 ? 'text-rose-400' : kpis.max_magnitude >= 4.5 ? 'text-amber-400' : 'text-emerald-400'
            }`}>
              {kpis.max_magnitude.toFixed(1)}
            </span>
            <span className="text-[11px] text-slate-400 font-mono">Mw/ml</span>
          </div>
        </div>

        {/* KPI 3: Magnitud Promedio */}
        <div className="p-4 flex flex-col justify-between">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Magnitud Media</span>
          <div className="mt-1 flex items-baseline space-x-2">
            <span className="text-2xl font-semibold tracking-tight text-slate-100">{kpis.avg_magnitude.toFixed(2)}</span>
            <span className="text-[11px] text-slate-400 font-mono">promedio</span>
          </div>
        </div>

        {/* KPI 4: Alertas de Tsunami */}
        <div className="p-4 flex flex-col justify-between">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Alertas Tsunami</span>
          <div className="mt-1 flex items-center space-x-2">
            <span className={`w-2 h-2 rounded-full ${kpis.tsunami_alerts > 0 ? 'bg-rose-500 animate-ping' : 'bg-slate-600'}`} />
            <span className={`text-2xl font-semibold tracking-tight ${kpis.tsunami_alerts > 0 ? 'text-rose-400' : 'text-slate-300'}`}>
              {kpis.tsunami_alerts}
            </span>
            <span className="text-[11px] text-slate-400 font-mono">activas</span>
          </div>
        </div>

        {/* KPI 5: Calidad de Datos */}
        <div className="p-4 flex flex-col justify-between">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Calidad (Pandera)</span>
          <div className="mt-1 flex items-baseline space-x-2">
            <span className="text-2xl font-semibold tracking-tight text-emerald-400">{kpis.quality_score}%</span>
            <span className="text-[11px] text-slate-400 font-mono">conforme</span>
          </div>
        </div>

        {/* KPI 6: Sincronización */}
        <div className="p-4 flex flex-col justify-between">
          <span className="text-[11px] font-mono uppercase tracking-wider text-slate-400">Última Carga</span>
          <div className="mt-1 flex items-baseline space-x-2">
            <span className="text-xs font-mono text-slate-300">
              {kpis.last_updated.slice(11, 19) || '07:05:00'} UTC
            </span>
            <span className="text-[10px] text-slate-500 font-mono">Airflow</span>
          </div>
        </div>

      </div>
    </div>
  );
};
