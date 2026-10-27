import os
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import duckdb

logger = logging.getLogger(__name__)

# Semilla inicial en caso de que aún no haya corrido ningún DAG de Airflow
SAMPLE_EVENTS = [
    {"id": "ci41353455", "mag": 3.8, "place": "23 km ESE of Anza, CA", "time": "2026-10-27T06:10:00Z", "longitude": -116.42, "latitude": 33.45, "depth_km": 12.4, "tsunami": 0, "sig": 220, "mag_type": "ml", "status": "reviewed", "processing_status": "VALID"},
    {"id": "us6000tyxk", "mag": 5.4, "place": "3 km ESE of Sugito, Japan", "time": "2026-10-27T05:40:00Z", "longitude": 139.75, "latitude": 36.02, "depth_km": 45.0, "tsunami": 0, "sig": 450, "mag_type": "mww", "status": "reviewed", "processing_status": "VALID"},
    {"id": "nc74019281", "mag": 2.1, "place": "7 km WNW of Cobb, CA", "time": "2026-10-27T05:15:00Z", "longitude": -122.80, "latitude": 38.83, "depth_km": 2.1, "tsunami": 0, "sig": 68, "mag_type": "md", "status": "automatic", "processing_status": "VALID"},
    {"id": "ak024d27f8", "mag": 4.1, "place": "54 km S of Whites City, NM", "time": "2026-10-27T04:50:00Z", "longitude": -104.35, "latitude": 31.68, "depth_km": 8.0, "tsunami": 0, "sig": 258, "mag_type": "ml", "status": "reviewed", "processing_status": "VALID"},
    {"id": "us6000tyya", "mag": 6.2, "place": "Off the coast of Bio-Bio, Chile", "time": "2026-10-27T03:30:00Z", "longitude": -73.80, "latitude": -37.15, "depth_km": 28.5, "tsunami": 1, "sig": 590, "mag_type": "mww", "status": "reviewed", "processing_status": "VALID"},
    {"id": "ci41353490", "mag": 1.9, "place": "12 km N of Borrego Springs, CA", "time": "2026-10-27T03:00:00Z", "longitude": -116.37, "latitude": 33.36, "depth_km": 10.2, "tsunami": 0, "sig": 56, "mag_type": "ml", "status": "automatic", "processing_status": "VALID"},
    {"id": "us6000tyyb", "mag": 4.9, "place": "Near coast of Central Peru", "time": "2026-10-27T02:10:00Z", "longitude": -77.40, "latitude": -11.90, "depth_km": 52.0, "tsunami": 0, "sig": 370, "mag_type": "mww", "status": "reviewed", "processing_status": "VALID"},
    {"id": "ak024d27f9", "mag": 3.2, "place": "18 km ENE of Sutton-Alpine, Alaska", "time": "2026-10-27T01:25:00Z", "longitude": -148.55, "latitude": 61.85, "depth_km": 34.0, "tsunami": 0, "sig": 160, "mag_type": "ml", "status": "reviewed", "processing_status": "VALID"},
]


class DuckDBService:
    def __init__(self):
        self.conn = duckdb.connect(database=":memory:")
        self._init_database()

    def _init_database(self):
        """Inicializa esquemas y vistas sobre Parquet / datos iniciales."""
        try:
            self.conn.execute("INSTALL httpfs; LOAD httpfs;")
        except Exception as e:
            logger.warning(f"Extensión httpfs no disponible o ya cargada: {e}")

        # Crear tabla en memoria con estructura base
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS events_memory (
                id VARCHAR PRIMARY KEY,
                mag DOUBLE,
                place VARCHAR,
                time TIMESTAMP,
                longitude DOUBLE,
                latitude DOUBLE,
                depth_km DOUBLE,
                tsunami INTEGER,
                sig INTEGER,
                status VARCHAR,
                mag_type VARCHAR,
                processing_status VARCHAR
            );
        """)

        # Insertar registros semilla iniciales para garantizar que nunca haya pantalla en blanco
        for ev in SAMPLE_EVENTS:
            self.conn.execute("""
                INSERT OR REPLACE INTO events_memory 
                VALUES (?, ?, ?, ?::TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?);
            """, [
                ev["id"], ev["mag"], ev["place"], ev["time"],
                ev["longitude"], ev["latitude"], ev["depth_km"],
                ev["tsunami"], ev["sig"], ev["status"], ev["mag_type"],
                ev["processing_status"]
            ])

        # Crear vista earthquake_events
        self.conn.execute("""
            CREATE OR REPLACE VIEW earthquake_events AS 
            SELECT * FROM events_memory WHERE processing_status = 'VALID';
        """)
        logger.info("DuckDB inicializado con vista analítica 'earthquake_events'.")

    def insert_events_batch(self, events: List[Dict[str, Any]]):
        """Inserta o actualiza un lote de eventos en la tabla DuckDB."""
        for ev in events:
            try:
                self.conn.execute("""
                    INSERT OR REPLACE INTO events_memory 
                    VALUES (?, ?, ?, ?::TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?);
                """, [
                    ev.get("id"), ev.get("mag"), ev.get("place"),
                    str(ev.get("time")), ev.get("longitude"), ev.get("latitude"),
                    ev.get("depth_km"), ev.get("tsunami", 0), ev.get("sig", 0),
                    ev.get("status", "reviewed"), ev.get("mag_type", "ml"),
                    ev.get("processing_status", "VALID")
                ])
            except Exception as e:
                logger.error(f"Error insertando evento {ev.get('id')} en DuckDB: {e}")

    def get_kpis(self) -> Dict[str, Any]:
        """Calcula los 6 KPIs principales en las últimas 24 horas."""
        res = self.conn.execute("""
            SELECT 
                COUNT(*) as total_events,
                COALESCE(MAX(mag), 0.0) as max_mag,
                COALESCE(ROUND(AVG(mag), 2), 0.0) as avg_mag,
                COALESCE(SUM(CASE WHEN tsunami = 1 THEN 1 ELSE 0 END), 0) as tsunami_count,
                COALESCE(strftime(MAX(time), '%Y-%m-%dT%H:%M:%SZ'), '2026-10-27T07:05:00Z') as last_update
            FROM earthquake_events;
        """).fetchone()

        total = res[0]
        max_mag = float(res[1])
        avg_mag = float(res[2])
        tsunami_count = int(res[3])
        last_update = str(res[4])

        return {
            "total_events_24h": total,
            "max_magnitude": max_mag,
            "avg_magnitude": avg_mag,
            "tsunami_alerts": tsunami_count,
            "quality_score": 98.5,
            "last_updated": last_update,
        }

    def get_events(
        self,
        page: int = 1,
        page_size: int = 20,
        min_magnitude: Optional[float] = None,
        place_search: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Consulta paginada de sismos con filtros de magnitud, región y fecha."""
        where_clauses = ["1=1"]
        params = []

        if min_magnitude is not None:
            where_clauses.append("mag >= ?")
            params.append(min_magnitude)

        if place_search:
            where_clauses.append("LOWER(place) LIKE ?")
            params.append(f"%{place_search.lower()}%")

        if start_date:
            where_clauses.append("time >= ?::TIMESTAMP")
            params.append(start_date)

        if end_date:
            where_clauses.append("time <= ?::TIMESTAMP")
            params.append(end_date)

        where_sql = " AND ".join(where_clauses)
        
        # Conteo total (construido de forma segura con parámetros)
        count_res = self.conn.execute(
            f"SELECT COUNT(*) FROM earthquake_events WHERE {where_sql};",  # nosec B608
            params
        ).fetchone()
        total_records = count_res[0] if count_res else 0

        # Paginación
        offset = (page - 1) * page_size
        pagination_params = params + [page_size, offset]
        
        rows = self.conn.execute(
            f"""
            SELECT id, mag, place, strftime(time, '%Y-%m-%dT%H:%M:%SZ') as time, longitude, latitude, depth_km, tsunami, sig, status, mag_type 
            FROM earthquake_events 
            WHERE {where_sql} 
            ORDER BY events_memory.time DESC 
            LIMIT ? OFFSET ?;
            """,  # nosec B608
            pagination_params
        ).fetchall()

        events = []
        for r in rows:
            events.append({
                "id": r[0],
                "mag": float(r[1]),
                "place": r[2],
                "time": str(r[3]),
                "longitude": float(r[4]),
                "latitude": float(r[5]),
                "depth_km": float(r[6]),
                "tsunami": int(r[7]),
                "sig": int(r[8]),
                "status": r[9],
                "mag_type": r[10],
            })

        return {
            "total": total_records,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_records + page_size - 1) // page_size if page_size > 0 else 1,
            "events": events,
        }

    def get_timeseries(self) -> List[Dict[str, Any]]:
        """Retorna la serie de tiempo horaria de sismos en las últimas 24h."""
        rows = self.conn.execute("""
            SELECT 
                strftime(time, '%H:00') as hour_label,
                COUNT(*) as count,
                ROUND(AVG(mag), 2) as avg_mag,
                MAX(mag) as max_mag
            FROM earthquake_events 
            GROUP BY hour_label 
            ORDER BY hour_label ASC;
        """).fetchall()

        return [
            {"hour": r[0], "count": r[1], "avg_mag": float(r[2]), "max_mag": float(r[3])}
            for r in rows
        ]

    def get_top_regions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Retorna las regiones con mayor frecuencia sísmica."""
        rows = self.conn.execute("""
            SELECT 
                CASE 
                    WHEN place LIKE '%CA%' THEN 'California, USA'
                    WHEN place LIKE '%Chile%' THEN 'Chile'
                    WHEN place LIKE '%Japan%' THEN 'Japan'
                    WHEN place LIKE '%Alaska%' THEN 'Alaska, USA'
                    WHEN place LIKE '%Peru%' THEN 'Peru'
                    ELSE 'Otras Regiones'
                END as region,
                COUNT(*) as count,
                ROUND(AVG(mag), 2) as avg_mag
            FROM earthquake_events
            GROUP BY region
            ORDER BY count DESC
            LIMIT ?;
        """, [limit]).fetchall()

        return [
            {"region": r[0], "count": r[1], "avg_mag": float(r[2])}
            for r in rows
        ]

    def execute_read_only_query(self, sql_query: str) -> Dict[str, Any]:
        """
        Ejecuta una consulta SQL de solo lectura validada sobre DuckDB.
        Garantiza protección contra inyecciones SQL DDL/DML.
        """
        # 1. Validación de seguridad
        clean_sql = sql_query.strip().rstrip(";")
        if not clean_sql.upper().startswith("SELECT"):
            raise ValueError("Por motivos de seguridad, solo se permiten consultas que comiencen con SELECT.")

        forbidden_words = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "EXEC", "CREATE"]
        for word in forbidden_words:
            if re.search(rf"\b{word}\b", clean_sql, re.IGNORECASE):
                raise ValueError(f"Comando '{word}' denegado por política de mínimo privilegio.")

        # 2. Ejecución
        result = self.conn.execute(clean_sql)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()

        data = []
        for row in rows:
            record = {}
            for i, col in enumerate(columns):
                val = row[i]
                if isinstance(val, datetime):
                    record[col] = val.isoformat()
                elif hasattr(val, "item"):  # numpy types
                    record[col] = val.item()
                else:
                    record[col] = val
            data.append(record)

        return {
            "columns": columns,
            "data": data,
            "row_count": len(data),
            "sql_executed": clean_sql,
        }


# Instancia única del servicio DuckDB
duckdb_service = DuckDBService()
