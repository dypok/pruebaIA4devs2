import React, { useState, useEffect } from 'react';
import { Database, CheckCircle, AlertTriangle, Play, RefreshCw, Lock } from 'lucide-react';
import { PipelineTelemetry } from '../types';
import { fetchPipelineStatus, fetchQuarantineRecords, triggerBackfillApi, triggerAiRegenerateApi } from '../services/api';
import { useAuth } from '../context/AuthContext';

export const PipelineStatus: React.FC = () => {
  const { isAdmin } = useAuth();
  const [telemetry, setTelemetry] = useState<PipelineTelemetry | null>(null);
  const [quarantine, setQuarantine] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const tel = await fetchPipelineStatus();
      setTelemetry(tel);
      if (isAdmin) {
        const quar = await fetchQuarantineRecords().catch(() => []);
        setQuarantine(quar);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [isAdmin]);

  const handleBackfill = async () => {
    try {
      const res = await triggerBackfillApi();
      setActionMsg(res.message || 'Backfill iniciado en Airflow.');
      setTimeout(() => setActionMsg(null), 5000);
    } catch (e: any) {
      alert(e.message);
    }
  };

  const handleRegenerateAi = async () => {
    try {
      const res = await triggerAiRegenerateApi();
      setActionMsg(res.message || 'Regeneración iniciada.');
      setTimeout(() => setActionMsg(null), 5000);
    } catch (e: any) {
      alert(e.message);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-slate-400 font-mono text-xs">Cargando telemetría del pipeline...</div>;
  }

  return (
    <div className="space-y-6">
      
      {/* Alerta de acción administrativa */}
      {actionMsg && (
        <div className="p-3 bg-sky-500/10 border border-sky-500/20 text-sky-400 text-xs font-mono rounded flex items-center justify-between">
          <span>{actionMsg}</span>
          <button onClick={() => setActionMsg(null)} className="text-slate-400 hover:text-white">&times;</button>
        </div>
      )}

      {/* Panel Superior: Estado de los DAGs y Calidad */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-5">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-3 mb-4">
          <div>
            <h3 className="text-sm font-semibold text-slate-100 flex items-center space-x-2">
              <Database className="w-4 h-4 text-sky-400" />
              <span>Orquestación Apache Airflow & Ecosistema de Datos</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Estado en tiempo real de los DAGs, MinIO S3 y DuckDB</p>
          </div>

          {/* Acciones de Administrador (Ocultas para Viewer) */}
          {isAdmin ? (
            <div className="flex items-center space-x-2 text-xs font-mono">
              <button
                onClick={handleBackfill}
                className="flex items-center space-x-1.5 px-3 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded transition-colors"
                title="Lanzar Backfill Histórico de 30 días"
              >
                <Play className="w-3.5 h-3.5" />
                <span>Lanzar Backfill (30d)</span>
              </button>
              <button
                onClick={handleRegenerateAi}
                className="flex items-center space-x-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded transition-colors"
                title="Regenerar Reporte Diario de IA"
              >
                <RefreshCw className="w-3.5 h-3.5 text-sky-400" />
                <span>Regenerar IA</span>
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-1.5 text-[11px] font-mono text-slate-500">
              <Lock className="w-3.5 h-3.5" />
              <span>Acciones administrativas restringidas (Requiere Admin)</span>
            </div>
          )}
        </div>

        {/* Lista de DAGs */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {telemetry?.dags && Object.entries(telemetry.dags).map(([key, dag]) => (
            <div key={key} className="bg-slate-950/60 border border-slate-800/80 rounded p-4">
              <div className="flex items-center justify-between text-xs font-mono">
                <span className="font-semibold text-slate-200 truncate">{dag.dag_id}</span>
                <span className="flex items-center space-x-1 text-emerald-400">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block" />
                  <span className="uppercase">{dag.state}</span>
                </span>
              </div>
              <div className="mt-3 space-y-1 text-[11px] font-mono text-slate-400">
                <div>Programación: <span className="text-slate-200">{dag.schedule}</span></div>
                <div>Última corrida: <span className="text-slate-200">{dag.last_run.slice(0, 19).replace('T', ' ')}</span></div>
                {dag.freshness_minutes && (
                  <div>Frescura: <span className="text-emerald-400">{dag.freshness_minutes} min</span></div>
                )}
                {dag.quality_score && (
                  <div>Score de Calidad: <span className="text-emerald-400">{dag.quality_score}%</span></div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Panel Inferior: Explorador de Registros con Fallos de Calidad (Solo Admin) */}
      {isAdmin ? (
        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-semibold text-slate-100">
                Auditoría de Calidad: Registros en Estado INVALID
              </h3>
            </div>
            <span className="text-xs font-mono text-slate-400">
              {quarantine.length} registro(s) interceptados
            </span>
          </div>

          <p className="text-xs text-slate-400 mb-4">
            Los siguientes registros violaron reglas de Pandera durante la transformación en Polars (Motor Vectorizado en Rust).
            Se preservaron en la capa Silver con motivo de rechazo y activaron la alerta en Airflow para corrección del operador.
          </p>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse font-sans">
              <thead>
                <tr className="border-b border-slate-800 text-[11px] font-mono uppercase text-slate-400 bg-slate-950/60">
                  <th className="py-2 px-3">ID Evento</th>
                  <th className="py-2 px-3">Coordenadas</th>
                  <th className="py-2 px-3">Magnitud</th>
                  <th className="py-2 px-3">Motivo de Rechazo (Validation Error)</th>
                  <th className="py-2 px-3 text-right">Capturado (UTC)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {quarantine.map((item, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30">
                    <td className="py-2.5 px-3 font-mono font-semibold text-amber-400">{item.id}</td>
                    <td className="py-2.5 px-3 font-mono text-slate-300">[{item.latitude}, {item.longitude}]</td>
                    <td className="py-2.5 px-3 font-mono font-bold text-rose-400">{item.mag}</td>
                    <td className="py-2.5 px-3 text-rose-300 font-mono text-[11px]">{item.validation_error}</td>
                    <td className="py-2.5 px-3 font-mono text-slate-400 text-right">{item.quarantined_at?.slice(0, 19).replace('T', ' ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="bg-slate-900/40 border border-amber-500/30 rounded-lg p-5">
          <div className="flex items-start space-x-3">
            <Lock className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-semibold text-slate-200">
                Auditoría de Calidad y Cuarentena Restringida (Rol Viewer)
              </h4>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                Estás visualizando la plataforma con rol <b>Viewer (Solo Lectura)</b>. El acceso a los registros en estado INVALID interceptados por el motor de calidad Pandera y las acciones de mutación de Airflow requieren rol <b>Admin</b> (política RBAC HTTP 403 Forbidden).
              </p>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
