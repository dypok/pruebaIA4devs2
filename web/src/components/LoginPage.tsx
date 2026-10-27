import React, { useState } from 'react';
import { Shield, KeyRound, User, ArrowRight, Database, Eye, CheckCircle2, Lock } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('AdminSismoWatch2026!');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(username, password);
    } catch (err: any) {
      setError(err.message || 'Credenciales incorrectas');
    } finally {
      setLoading(false);
    }
  };

  const selectRole = (role: 'admin' | 'viewer') => {
    if (role === 'admin') {
      setUsername('admin');
      setPassword('AdminSismoWatch2026!');
    } else {
      setUsername('viewer');
      setPassword('ViewerSismoWatch2026!');
    }
    setError(null);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-center items-center p-4 selection:bg-sky-500 selection:text-white">
      
      {/* Brand Header */}
      <div className="text-center mb-8 max-w-lg">
        <div className="inline-flex items-center space-x-2 px-3 py-1 bg-sky-500/10 border border-sky-500/20 rounded-full text-sky-400 text-xs font-mono mb-3">
          <Shield className="w-3.5 h-3.5" />
          <span>Control de Acceso Basado en Roles (RBAC)</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
          SismoWatch <span className="text-sky-400">Lakehouse</span>
        </h1>
        <p className="text-slate-400 text-xs sm:text-sm mt-2">
          Monitoreo Sísmico Global en Tiempo Real • MinIO S3 • Polars • DuckDB • Qwen 2.5:2b
        </p>
      </div>

      <div className="max-w-4xl w-full grid grid-cols-1 md:grid-cols-5 gap-6 items-start">
        
        {/* Formulario de Login */}
        <div className="md:col-span-3 bg-slate-900 border border-slate-800 rounded-xl p-6 sm:p-8 shadow-2xl space-y-6">
          <div>
            <h2 className="text-lg font-bold text-slate-100">Iniciar Sesión</h2>
            <p className="text-xs text-slate-400 mt-0.5">Ingresa tus credenciales o selecciona un perfil de prueba</p>
          </div>

          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded font-mono">
              {error}
            </div>
          )}

          {/* Tarjetas selectoras rápidas de Roles */}
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => selectRole('admin')}
              className={`p-3 rounded-lg border text-left transition-all ${
                username === 'admin'
                  ? 'bg-sky-500/10 border-sky-500/50 shadow-sm'
                  : 'bg-slate-950/40 border-slate-800 hover:bg-slate-800/40'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold font-mono text-sky-400">ADMIN</span>
                <Database className="w-3.5 h-3.5 text-sky-400" />
              </div>
              <p className="text-[11px] text-slate-400 mt-1">Control Total: Backfill, Cuarentena, Reportes IA</p>
            </button>

            <button
              type="button"
              onClick={() => selectRole('viewer')}
              className={`p-3 rounded-lg border text-left transition-all ${
                username === 'viewer'
                  ? 'bg-amber-500/10 border-amber-500/50 shadow-sm'
                  : 'bg-slate-950/40 border-slate-800 hover:bg-slate-800/40'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold font-mono text-amber-400">VIEWER</span>
                <Eye className="w-3.5 h-3.5 text-amber-400" />
              </div>
              <p className="text-[11px] text-slate-400 mt-1">Solo Lectura: Dashboard, Mapa, Asistente Chat</p>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">Usuario</label>
              <div className="relative">
                <User className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-700 rounded text-xs text-slate-100 focus:outline-none focus:border-sky-500 font-mono"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-mono text-slate-300 mb-1">Contraseña</label>
              <div className="relative">
                <KeyRound className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 bg-slate-950 border border-slate-700 rounded text-xs text-slate-100 focus:outline-none focus:border-sky-500 font-mono"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-sky-600 hover:bg-sky-500 text-white font-medium text-xs rounded-lg flex items-center justify-center space-x-2 transition-colors shadow-lg shadow-sky-600/20"
            >
              <span>{loading ? 'Autenticando...' : `Ingresar como ${username.toUpperCase()}`}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </form>
        </div>

        {/* Matriz Explicativa de Permisos RBAC */}
        <div className="md:col-span-2 bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4 text-xs font-sans">
          <div className="flex items-center space-x-2 border-b border-slate-800 pb-2.5">
            <Shield className="w-4 h-4 text-slate-400" />
            <h3 className="font-semibold text-slate-200">Matriz de Acceso por Rol</h3>
          </div>

          <div className="space-y-3">
            <div className="p-3 bg-slate-950/40 rounded border border-slate-800/80">
              <div className="font-mono font-bold text-sky-400 text-[11px] mb-1 flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>ROL ADMIN (Privilegios Totales)</span>
              </div>
              <ul className="space-y-1 text-slate-400 text-[11px] pl-1 font-mono">
                <li>• Dashboard & Mapa global interactivo</li>
                <li>• Chatbot analítico Text-to-SQL</li>
                <li>• Lanzar Backfill histórico (Airflow)</li>
                <li>• Regenerar Reporte Diario IA</li>
                <li>• Auditoría de registros en Cuarentena</li>
              </ul>
            </div>

            <div className="p-3 bg-slate-950/40 rounded border border-slate-800/80">
              <div className="font-mono font-bold text-amber-400 text-[11px] mb-1 flex items-center space-x-1">
                <Lock className="w-3.5 h-3.5" />
                <span>ROL VIEWER (Solo Lectura)</span>
              </div>
              <ul className="space-y-1 text-slate-400 text-[11px] pl-1 font-mono">
                <li>• Dashboard & Mapa global interactivo</li>
                <li>• Chatbot analítico Text-to-SQL</li>
                <li>• Lectura de reportes diarios de IA</li>
                <li>• ❌ Acciones de mutación bloqueadas (403)</li>
                <li>• ❌ Registros en cuarentena ocultos (403)</li>
              </ul>
            </div>
          </div>
        </div>

      </div>

      <div className="mt-8 text-center text-slate-500 font-mono text-[11px]">
        SismoWatch Platform • Seguridad Criptográfica JWT (HS256) • Mínimo Privilegio PostgreSQL
      </div>
    </div>
  );
};
