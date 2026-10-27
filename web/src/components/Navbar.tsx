import React from 'react';
import { Activity, Shield, Bot, LogOut, Radio } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface NavbarProps {
  activeTab: 'dashboard' | 'reports' | 'pipeline';
  setActiveTab: (tab: 'dashboard' | 'reports' | 'pipeline') => void;
  isChatOpen: boolean;
  setIsChatOpen: (open: boolean) => void;
  isLive: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  isChatOpen,
  setIsChatOpen,
  isLive,
}) => {
  const { user, logout } = useAuth();

  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        
        {/* Logo & Marca */}
        <div className="flex items-center space-x-8">
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('dashboard')}>
            <div className="w-9 h-9 rounded-lg bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <div className="font-bold text-slate-100 tracking-tight text-base">SismoWatch</div>
              <div className="text-[10px] text-slate-400 uppercase tracking-widest font-mono">SuperApp RiskOps</div>
            </div>
          </div>

          {/* Navegación por pestañas */}
          <nav className="hidden md:flex space-x-1">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                activeTab === 'dashboard'
                  ? 'text-sky-400 bg-sky-500/10 border border-sky-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              Dashboard
            </button>
            <button
              onClick={() => setActiveTab('reports')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                activeTab === 'reports'
                  ? 'text-sky-400 bg-sky-500/10 border border-sky-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              Reportes IA
            </button>
            <button
              onClick={() => setActiveTab('pipeline')}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                activeTab === 'pipeline'
                  ? 'text-sky-400 bg-sky-500/10 border border-sky-500/20'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              Pipeline & Gobernanza
            </button>
          </nav>
        </div>

        {/* Acciones y Estado */}
        <div className="flex items-center space-x-5">
          {/* Indicador EN VIVO (con status dot sutil, CERO badges) */}
          <div className="flex items-center space-x-2 text-xs font-mono">
            <span className={`inline-block w-2 h-2 rounded-full ${isLive ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
            <span className="text-slate-300 font-medium">{isLive ? 'En vivo (SSE)' : 'Conectando'}</span>
          </div>

          {/* Botón Lanzador del Chatbot Qwen */}
          <button
            onClick={() => setIsChatOpen(!isChatOpen)}
            className="flex items-center space-x-2 px-3 py-1.5 text-xs font-medium rounded-md bg-slate-800 hover:bg-slate-700 text-sky-400 border border-slate-700 transition-colors"
            title="Abrir Asistente Sísmico IA (Qwen 2.5:2b)"
          >
            <Bot className="w-4 h-4 text-sky-400" />
            <span className="hidden sm:inline">SismoWatch AI</span>
          </button>

          {/* Perfil de Usuario */}
          <div className="flex items-center space-x-3 pl-2 border-l border-slate-800">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-medium text-slate-200">{user?.username || 'Usuario'}</div>
              <div className="text-[10px] font-mono text-slate-400 capitalize">{user?.role}</div>
            </div>
            <button
              onClick={logout}
              className="p-1.5 text-slate-400 hover:text-rose-400 rounded-md hover:bg-slate-800 transition-colors"
              title="Cerrar Sesión"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>

      </div>
    </header>
  );
};
