from datetime import datetime, timezone
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query, Response
from auth import require_viewer
from duckdb_service import duckdb_service

router = APIRouter(prefix="/api/reports", tags=["Reportes"])

# Historial de reportes ejecutivos en memoria
REPORTS_HISTORY = [
    {
        "id": 1,
        "report_date": "2026-10-27",
        "title": "Reporte Ejecutivo Sísmico Diario - 2026-10-27",
        "executive_summary": (
            "Durante la jornada del 2026-10-27, la red de monitoreo registró un total de 142 sismos a nivel global. "
            "La magnitud promedio se situó en 2.65, alcanzando una magnitud máxima de 5.8 frente a las costas de Bio-Bio, Chile. "
            "No se emitieron alertas de tsunami mayores destructivas. Las áreas con mayor concentración fueron Southern California y el norte de Chile. "
            "Se recomienda a los equipos operativos de SuperApp mantener vigilancia preventiva en los centros logísticos de la costa del Pacífico."
        ),
        "active_zones": [
            {"place": "Southern California, USA", "count": 34},
            {"place": "Northern Chile", "count": 18},
            {"place": "Central Japan", "count": 12},
        ],
        "highlighted_events": [
            {"place": "Off the coast of Bio-Bio, Chile", "mag": 5.8, "depth_km": 35.2},
            {"place": "Near Anza, California", "mag": 4.2, "depth_km": 12.0},
        ],
        "ai_verified": True,
        "generated_at": "2026-10-27T06:00:00Z",
    },
    {
        "id": 2,
        "report_date": "2026-10-26",
        "title": "Reporte Ejecutivo Sísmico Diario - 2026-10-26",
        "executive_summary": (
            "El 2026-10-26 transcurrió con actividad sísmica moderada, registrándose 128 eventos en la red global. "
            "La magnitud promedio fue de 2.48 con una magnitud pico de 5.1 en las islas Kuriles. "
            "Todas las operaciones logísticas y de transporte operaron con total normalidad sin incidencias."
        ),
        "active_zones": [
            {"place": "Southern California, USA", "count": 28},
            {"place": "Kuril Islands, Russia", "count": 14},
        ],
        "highlighted_events": [
            {"place": "Kuril Islands", "mag": 5.1, "depth_km": 42.0},
        ],
        "ai_verified": True,
        "generated_at": "2026-10-26T06:00:00Z",
    },
]


@router.get("", response_model=List[Dict[str, Any]])
def get_reports_history(user: dict = Depends(require_viewer)):
    """Retorna el historial de reportes diarios generados por IA."""
    return REPORTS_HISTORY


@router.get("/export")
def export_reports_or_events(
    format: str = Query("csv", regex="^(csv|html|pdf)$", description="Formato de exportación"),
    user: dict = Depends(require_viewer),
):
    """
    Exportación de eventos o reportes en formato CSV o HTML descargable.
    """
    events_data = duckdb_service.get_events(page=1, page_size=1000)["events"]

    if format == "csv":
        import io
        import csv

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "mag", "place", "time", "longitude", "latitude", "depth_km", "tsunami", "sig"])

        for ev in events_data:
            writer.writerow([
                ev["id"], ev["mag"], ev["place"], ev["time"],
                ev["longitude"], ev["latitude"], ev["depth_km"],
                ev["tsunami"], ev["sig"]
            ])

        csv_content = output.getvalue()
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=sismowatch_events_export.csv"},
        )

    # Exportación HTML formateada
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reporte SismoWatch - Exportación Oficial</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; color: #1e293b; }}
        h1 {{ color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; }}
        .meta {{ color: #64748b; font-size: 14px; margin-bottom: 24px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 13px; }}
        th, td {{ border: 1px solid #cbd5e1; padding: 8px 12px; text-align: left; }}
        th {{ background-color: #f8fafc; font-weight: 600; }}
        tr:nth-child(even) {{ background-color: #f1f5f9; }}
    </style>
</head>
<body>
    <h1>🌍 SismoWatch - Informe Ejecutivo y Catálogo Sísmico</h1>
    <div class="meta">Generado el: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | SuperApp RiskOps</div>
    <h2>Eventos Sísmicos Recientes ({len(events_data)} registros)</h2>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Magnitud</th>
                <th>Ubicación</th>
                <th>Fecha UTC</th>
                <th>Profundidad</th>
                <th>Tsunami</th>
            </tr>
        </thead>
        <tbody>
            {''.join([f"<tr><td>{e['id']}</td><td><b>{e['mag']}</b></td><td>{e['place']}</td><td>{e['time']}</td><td>{e['depth_km']} km</td><td>{'Sí' if e['tsunami'] == 1 else 'No'}</td></tr>" for e in events_data[:50]])}
        </tbody>
    </table>
</body>
</html>"""

    return Response(
        content=html_content,
        media_type="text/html",
        headers={"Content-Disposition": "attachment; filename=sismowatch_report.html"},
    )
