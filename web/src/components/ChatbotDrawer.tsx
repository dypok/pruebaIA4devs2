import React, { useState } from 'react';
import {
  X,
  Send,
  Bot,
  Pin,
  Check,
  Code2,
  Sparkles,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import { sendChatMessage } from '../services/api';
import { ChartSuggestion, PinnedChart } from '../types';

interface Message {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  sql?: string;
  data?: any[];
  chart?: ChartSuggestion;
  timestamp: string;
}

interface ChatbotDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onPinChart: (chart: PinnedChart) => void;
}

export const ChatbotDrawer: React.FC<ChatbotDrawerProps> = ({
  isOpen,
  onClose,
  onPinChart,
}) => {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [pinnedIds, setPinnedIds] = useState<Set<string>>(new Set());
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      sender: 'bot',
      text: '¡Hola! Soy el asistente analítico de SismoWatch impulsado por Qwen 2.5:2b. Puedes hacerme preguntas en lenguaje natural sobre sismos, zonas activas o tendencias y te generaré consultas SQL sobre DuckDB y gráficos interactivos.',
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);

  if (!isOpen) return null;

  const handleSend = async (textToSend?: string) => {
    const query = textToSend || input;
    if (!query.trim() || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const resp = await sendChatMessage(query);
      const botMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'bot',
        text: resp.reply,
        sql: resp.sql,
        data: resp.data,
        chart: resp.chart_suggestion,
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, botMsg]);
    } catch (err: any) {
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        sender: 'bot',
        text: err?.message?.includes('Token') || err?.message?.includes('Autenticación')
          ? 'Tu sesión ha expirado o requiere autenticación. Por favor inicia sesión nuevamente.'
          : 'Ocurrió un error al procesar tu consulta. Inténtalo nuevamente o prueba con otra pregunta.',
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handlePin = (msg: Message) => {
    if (!msg.chart || !msg.data || !msg.sql) return;

    const pinned: PinnedChart = {
      id: `pinned-${Date.now()}`,
      title: msg.chart.title,
      type: msg.chart.type,
      x_key: msg.chart.x_key,
      y_key: msg.chart.y_key,
      sql: msg.sql,
      data: msg.data,
      pinnedAt: new Date().toISOString(),
    };

    onPinChart(pinned);
    setPinnedIds((prev) => new Set(prev).add(msg.id));
  };

  return (
    <div className="fixed inset-y-0 right-0 w-full sm:w-[480px] bg-slate-900 border-l border-slate-800 shadow-2xl z-50 flex flex-col">
      {/* Header */}
      <div className="px-4 py-3.5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
        <div className="flex items-center space-x-2.5">
          <div className="w-7 h-7 rounded-md bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-400">
            <Bot className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100 flex items-center space-x-1.5">
              <span>SismoWatch AI Assistant</span>
              <span className="text-[10px] font-mono text-sky-400">Qwen 2.5:2b</span>
            </h3>
            <p className="text-[10px] font-mono text-slate-400">Consultas Text-to-SQL sobre DuckDB</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-slate-400 hover:text-slate-200 rounded hover:bg-slate-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Preguntas sugeridas */}
      <div className="px-4 py-2 border-b border-slate-800/60 bg-slate-950/30 flex items-center space-x-2 overflow-x-auto text-[11px] font-mono">
        <button
          onClick={() => handleSend('¿Cuáles son los 5 sismos más fuertes hoy?')}
          className="whitespace-nowrap px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
        >
          ⚡ Sismos más fuertes
        </button>
        <button
          onClick={() => handleSend('¿Cómo se distribuyen los sismos por región?')}
          className="whitespace-nowrap px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
        >
          📍 Top regiones
        </button>
        <button
          onClick={() => handleSend('¿Hubo alertas de tsunami activas?')}
          className="whitespace-nowrap px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
        >
          🌊 Alertas tsunami
        </button>
      </div>

      {/* Mensajes del chat */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex flex-col ${m.sender === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`max-w-[90%] rounded-lg p-3 text-xs leading-relaxed ${
                m.sender === 'user'
                  ? 'bg-sky-600 text-white'
                  : 'bg-slate-800/90 text-slate-200 border border-slate-700/60'
              }`}
            >
              <p>{m.text}</p>

              {/* Consulta SQL generada */}
              {m.sql && (
                <div className="mt-2.5 pt-2 border-t border-slate-700/60">
                  <div className="flex items-center space-x-1 text-[10px] font-mono text-sky-400 mb-1">
                    <Code2 className="w-3 h-3" />
                    <span>DuckDB SQL Ejecutado:</span>
                  </div>
                  <pre className="bg-slate-950 p-2 rounded text-[10px] font-mono text-slate-300 overflow-x-auto">
                    {m.sql}
                  </pre>
                </div>
              )}

              {/* Gráfico interactivo Auto-Chart renderizado dentro del chat */}
              {m.chart && m.data && m.data.length > 0 && (
                <div className="mt-3 p-2 bg-slate-950/80 rounded border border-slate-800">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-semibold text-slate-200">{m.chart.title}</span>
                    <button
                      onClick={() => handlePin(m)}
                      disabled={pinnedIds.has(m.id)}
                      className={`flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                        pinnedIds.has(m.id)
                          ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                          : 'bg-sky-500/20 text-sky-400 hover:bg-sky-500/30 border border-sky-500/30'
                      }`}
                    >
                      {pinnedIds.has(m.id) ? (
                        <>
                          <Check className="w-3 h-3" />
                          <span>Fijado al Dashboard</span>
                        </>
                      ) : (
                        <>
                          <Pin className="w-3 h-3" />
                          <span>📌 Fijar al Dashboard</span>
                        </>
                      )}
                    </button>
                  </div>

                  <div className="h-44 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      {m.chart.type === 'line' ? (
                        <LineChart data={m.data} margin={{ top: 5, right: 10, left: -25, bottom: 0 }}>
                          <XAxis
                            dataKey={m.chart.x_key}
                            stroke="#64748b"
                            fontSize={10}
                            tickLine={false}
                            tickFormatter={(val) => {
                              if (typeof val === 'string' && val.length > 10) {
                                return val.includes(' ') ? val.split(' ')[0] : val.substring(0, 10);
                              }
                              return val;
                            }}
                          />
                          <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
                          <Tooltip
                            contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '4px' }}
                            itemStyle={{ color: '#38bdf8' }}
                          />
                          <Line
                            type="monotone"
                            dataKey={m.chart.y_key}
                            stroke="#38bdf8"
                            strokeWidth={2}
                            dot={{ r: 3, fill: '#38bdf8' }}
                            activeDot={{ r: 5 }}
                          />
                        </LineChart>
                      ) : (
                        <BarChart data={m.data} margin={{ top: 5, right: 10, left: -25, bottom: 0 }}>
                          <XAxis dataKey={m.chart.x_key} stroke="#64748b" fontSize={10} tickLine={false} />
                          <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
                          <Tooltip
                            contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '4px' }}
                            itemStyle={{ color: '#38bdf8' }}
                          />
                          <Bar dataKey={m.chart.y_key} fill="#0284c7" radius={[2, 2, 0, 0]} />
                        </BarChart>
                      )}
                    </ResponsiveContainer>
                  </div>
                </div>
              )}
            </div>
            <span className="text-[10px] font-mono text-slate-400 mt-1 px-1">{m.timestamp}</span>
          </div>
        ))}

        {loading && (
          <div className="flex items-center space-x-2 text-slate-400 text-xs font-mono py-2">
            <Sparkles className="w-4 h-4 animate-spin text-sky-400" />
            <span>Consultando DuckDB con Qwen 2.5:2b...</span>
          </div>
        )}
      </div>

      {/* Input de consulta */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/80">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center space-x-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Pregúntale al chatbot sobre sismos, zonas, magnitudes..."
            className="flex-1 bg-slate-900 border border-slate-700/80 rounded px-3 py-2 text-xs text-slate-100 placeholder-slate-400 focus:outline-none focus:border-sky-500 font-sans"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="p-2 bg-sky-600 hover:bg-sky-500 disabled:opacity-40 text-white rounded transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
