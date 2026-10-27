import React, { useEffect, useRef } from 'react';
import L from 'leaflet';
import { SeismicEvent } from '../types';

interface SeismicMapProps {
  events: SeismicEvent[];
  selectedEventId?: string;
  onSelectEvent?: (event: SeismicEvent) => void;
}

export const SeismicMap: React.FC<SeismicMapProps> = ({ events, onSelectEvent }) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    // Inicializar mapa centrado globalmente con estilo CartoDB Dark Matter
    const map = L.map(mapContainerRef.current, {
      center: [20, 0],
      zoom: 2,
      minZoom: 2,
      maxZoom: 12,
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; USGS',
      maxZoom: 19,
    }).addTo(map);

    markersLayerRef.current = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Actualizar marcadores cuando cambien los eventos
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current) return;

    markersLayerRef.current.clearLayers();

    events.forEach((ev) => {
      if (typeof ev.latitude !== 'number' || typeof ev.longitude !== 'number') return;

      // Color y radio según magnitud
      let color = '#10b981'; // verde < 3.0
      let radius = 6;
      if (ev.mag >= 6.0) {
        color = '#f43f5e'; // rojo >= 6.0
        radius = 16;
      } else if (ev.mag >= 4.5) {
        color = '#f97316'; // naranja >= 4.5
        radius = 12;
      } else if (ev.mag >= 3.0) {
        color = '#f59e0b'; // amarillo >= 3.0
        radius = 8;
      }

      const marker = L.circleMarker([ev.latitude, ev.longitude], {
        radius: radius,
        fillColor: color,
        color: '#0f172a',
        weight: 1.5,
        opacity: 0.9,
        fillOpacity: 0.7,
      });

      const popupContent = `
        <div style="font-family: inherit; font-size: 12px; color: #0f172a; line-height: 1.4;">
          <div style="font-weight: 700; font-size: 13px; margin-bottom: 4px;">${ev.place}</div>
          <div><b>Magnitud:</b> <span style="color: ${color}; font-weight: 800;">${ev.mag.toFixed(1)} ${ev.mag_type}</span></div>
          <div><b>Profundidad:</b> ${ev.depth_km} km</div>
          <div><b>Fecha UTC:</b> ${ev.time.slice(0, 19).replace('T', ' ')}</div>
          ${ev.tsunami === 1 ? '<div style="color: #e11d48; font-weight: bold; margin-top: 4px;">⚠️ ALERTA TSUNAMI ACTIVA</div>' : ''}
        </div>
      `;

      marker.bindPopup(popupContent);
      marker.on('click', () => {
        if (onSelectEvent) onSelectEvent(ev);
      });

      marker.addTo(markersLayerRef.current!);
    });
  }, [events, onSelectEvent]);

  return (
    <div className="relative w-full h-[460px] rounded-lg overflow-hidden border border-slate-800">
      <div ref={mapContainerRef} className="w-full h-full z-0 bg-slate-950" />
      
      {/* Leyenda sismológica sutil (sin badges) */}
      <div className="absolute bottom-3 left-3 z-10 bg-slate-900/90 backdrop-blur border border-slate-800 rounded px-3 py-2 text-[11px] font-mono text-slate-300 flex items-center space-x-4">
        <span className="text-slate-400 font-sans font-semibold">Magnitud:</span>
        <div className="flex items-center space-x-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" />
          <span>&lt; 3.0</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" />
          <span>3.0 - 4.4</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-orange-500 inline-block" />
          <span>4.5 - 5.9</span>
        </div>
        <div className="flex items-center space-x-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500 inline-block" />
          <span>&ge; 6.0</span>
        </div>
      </div>
    </div>
  );
};
