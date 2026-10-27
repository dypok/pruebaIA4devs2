import json
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query, Response, HTTPException
from auth import require_viewer
from duckdb_service import duckdb_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reports", tags=["Reportes"])


def parse_json_field(val):
    if val is None:
        return []
    if isinstance(val, (list, dict)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return []
    return []


@router.get("", response_model=List[Dict[str, Any]])
def get_reports_history(user: dict = Depends(require_viewer)):
    """Retorna el historial de reportes diarios generados por IA desde la base de datos PostgreSQL."""
    try:
        rows = duckdb_service.conn.execute("""
            SELECT id, report_date, title, executive_summary, active_zones, highlighted_events, ai_verified, generated_at
            FROM pg.curated.ai_reports
            ORDER BY generated_at DESC;
        """).fetchall()
        reports = []
        for r in rows:
            reports.append({
                "id": r[0],
                "report_date": str(r[1]),
                "title": r[2],
                "executive_summary": r[3],
                "active_zones": parse_json_field(r[4]),
                "highlighted_events": parse_json_field(r[5]),
                "ai_verified": bool(r[6]),
                "generated_at": r[7].isoformat() if hasattr(r[7], 'isoformat') else str(r[7]),
            })
        return reports
    except Exception as e:
        logger.error(f"Error consultando curated.ai_reports en Postgres: {e}")
        raise HTTPException(status_code=500, detail=f"Error consultando reportes en base de datos: {e}")


@router.get("/export")
def export_reports_or_events(
    format: str = Query("csv", regex="^(csv|html|pdf)$", description="Formato de exportación"),
    user: dict = Depends(require_viewer),
):
    """
    Exportación de eventos reales del Lakehouse en formato CSV o HTML descargable.
    """
    events_data = duckdb_service.get_events(page=1, page_size=1000)["events"]
    if not events_data:
        raise HTTPException(status_code=404, detail="No hay eventos sísmicos registrados para exportar.")

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

    # Exportación HTML formateada con datos reales
    rows_html = "".join([
        f"<tr><td>{e['id']}</td><td>{e['place']}</td><td><b>{e['mag']}</b></td><td>{e['depth_km']} km</td><td>{e['time']}</td></tr>"
        for e in events_data[:100]
    ])

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reporte SismoWatch - Exportación Certificada</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; color: #1e293b; background: #f8fafc; }}
        h1 {{ color: #0284c7; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: white; }}
        th, td {{ padding: 10px; border: 1px solid #cbd5e1; text-align: left; font-size: 13px; }}
        th {{ background: #0f172a; color: white; }}
    </style>
</head>
<body>
    <h1>SismoWatch - Exportación de Eventos Certificados (DuckDB Lakehouse)</h1>
    <p>Total de registros exportados: {len(events_data)}</p>
    <table>
        <thead>
            <tr><th>ID</th><th>Lugar</th><th>Magnitud</th><th>Profundidad</th><th>Fecha UTC</th></tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
</body>
</html>"""

    return Response(content=html_content, media_type="text/html")
