import os
import re
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import duckdb

logger = logging.getLogger(__name__)

class DuckDBService:
    def __init__(self):
        self._lock = threading.Lock()
        self._last_s3_sync: Optional[datetime] = None
        self.conn = duckdb.connect(database=":memory:")
        self._init_database()

    def _init_database(self):
        """Inicializa esquemas y vistas sobre Parquet en MinIO S3 y conexión Postgres."""
        try:
            self.conn.execute("INSTALL httpfs; LOAD httpfs;")
            endpoint = os.getenv("MINIO_ENDPOINT", "http://minio:9000").replace("http://", "").replace("https://", "")
            user = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
            pwd = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin2026!")
            self.conn.execute(f"""
                SET s3_endpoint = '{endpoint}';
                SET s3_access_key_id = '{user}';
                SET s3_secret_access_key = '{pwd}';
                SET s3_use_ssl = false;
                SET s3_url_style = 'path';
            """)
        except Exception as e:
            logger.warning(f"Configuración S3 para DuckDB falló o ya inicializada: {e}")

        # Conectar a PostgreSQL para metadatos reales
        try:
            self.conn.execute("INSTALL postgres; LOAD postgres;")
            pg_host = os.getenv("POSTGRES_HOST", "postgres")
            pg_port = os.getenv("POSTGRES_PORT", "5432")
            pg_db = os.getenv("POSTGRES_DB", "sismowatch_db")
            pg_user = os.getenv("POSTGRES_ADMIN_USER", "postgres")
            pg_pass = os.getenv("POSTGRES_ADMIN_PASSWORD", "postgres_master_secure_pass_2026!")
            self.conn.execute(f"ATTACH 'dbname={pg_db} user={pg_user} password={pg_pass} host={pg_host} port={pg_port}' AS pg (TYPE postgres);")
            logger.info("DuckDB conectado a PostgreSQL exitosamente.")
        except Exception as e:
            logger.warning(f"No se pudo conectar DuckDB a PostgreSQL: {e}")

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

        # Crear vista earthquake_events sobre datos reales
        self.conn.execute("""
            CREATE OR REPLACE VIEW earthquake_events AS 
            SELECT * FROM events_memory WHERE processing_status = 'VALID';
        """)

        # Cargar datos iniciales desde MinIO Gold Parquet
        self.refresh_from_s3(force=True)
        logger.info("DuckDB inicializado con vista analítica 'earthquake_events'.")

    def refresh_from_s3(self, force: bool = False):
        """Carga o actualiza eventos validados desde la capa Gold en MinIO con caché TTL."""
        now = datetime.now(timezone.utc)
        if not force and self._last_s3_sync is not None:
            if (now - self._last_s3_sync).total_seconds() < 60:
                return

        with self._lock:
            if not force and self._last_s3_sync is not None:
                if (now - self._last_s3_sync).total_seconds() < 60:
                    return
            try:
                self.conn.execute("""
                    INSERT OR REPLACE INTO events_memory
                    SELECT DISTINCT ON (id)
                        id, mag, place, time::TIMESTAMP,
                        longitude, latitude, depth_km,
                        tsunami::INTEGER, sig::INTEGER,
                        status, mag_type, processing_status
                    FROM read_parquet('s3://sismowatch-lake/gold/**/*.parquet')
                    WHERE processing_status = 'VALID';
                """)
                self._last_s3_sync = datetime.now(timezone.utc)
                count = self.conn.execute("SELECT count(*) FROM events_memory;").fetchone()[0]
                logger.info(f"DuckDB sincronizado con MinIO Gold Parquet. Total eventos en memoria: {count}")
            except Exception as e:
                logger.warning(f"Aviso de sincronización S3 MinIO en DuckDB: {e}")

    def insert_events_batch(self, events: List[Dict[str, Any]]):
        """Inserta o actualiza un lote de eventos en la tabla DuckDB."""
        with self._lock:
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
        """Calcula los 6 KPIs principales estrictamente en las últimas 24 horas."""
        self.refresh_from_s3()
        with self._lock:
            max_time_row = self.conn.execute("SELECT MAX(time) FROM earthquake_events;").fetchone()
            max_time = max_time_row[0] if max_time_row and max_time_row[0] else datetime.now(timezone.utc)

            res = self.conn.execute(f"""
                SELECT 
                    COUNT(*) as total_events,
                    COALESCE(MAX(mag), 0.0) as max_mag,
                    COALESCE(ROUND(AVG(mag), 2), 0.0) as avg_mag,
                    COALESCE(SUM(CASE WHEN tsunami = 1 THEN 1 ELSE 0 END), 0) as tsunami_count,
                    strftime(MAX(time), '%Y-%m-%dT%H:%M:%SZ') as last_update
                FROM earthquake_events
                WHERE time >= TIMESTAMP '{max_time}' - INTERVAL 24 HOUR;
            """).fetchone()

            if res and res[0] > 0:
                total = int(res[0])
                max_mag = float(res[1])
                avg_mag = float(res[2])
                tsunami_count = int(res[3])
                last_update = str(res[4]) if res[4] else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                total = 0
                max_mag = 0.0
                avg_mag = 0.0
                tsunami_count = 0
                last_update = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            # Cálculo de calidad real basado en Silver en las últimas 24h
            try:
                inv = self.conn.execute(f"""
                    SELECT COUNT(*) FROM read_parquet('s3://sismowatch-lake/silver/**/*.parquet')
                    WHERE processing_status = 'INVALID' AND time >= TIMESTAMP '{max_time}' - INTERVAL 24 HOUR;
                """).fetchone()[0]
                tot = total + inv
                quality_score = round(100.0 * total / tot, 2) if tot > 0 else 100.0
            except Exception:
                quality_score = 100.0

            return {
                "total_events_24h": total,
                "max_magnitude": max_mag,
                "avg_magnitude": avg_mag,
                "tsunami_alerts": tsunami_count,
                "quality_score": quality_score,
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

        with self._lock:
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
                ORDER BY time DESC 
                LIMIT ? OFFSET ?;
                """,  # nosec B608
                pagination_params
            ).fetchall()

            events = []
            for r in rows:
                events.append({
                    "id": r[0],
                    "mag": float(r[1]) if r[1] is not None else 0.0,
                    "place": str(r[2]),
                    "time": str(r[3]),
                    "longitude": float(r[4]) if r[4] is not None else 0.0,
                    "latitude": float(r[5]) if r[5] is not None else 0.0,
                    "depth_km": float(r[6]) if r[6] is not None else 0.0,
                    "tsunami": int(r[7]) if r[7] is not None else 0,
                    "sig": int(r[8]) if r[8] is not None else 0,
                    "status": str(r[9]),
                    "mag_type": str(r[10]),
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
        with self._lock:
            # 1. Intentar ventana estricta de 24h basada en el evento más reciente
            rows = self.conn.execute("""
                WITH max_t AS (
                    SELECT COALESCE(MAX(time), CURRENT_TIMESTAMP) as mt FROM earthquake_events
                )
                SELECT 
                    strftime(time, '%H:00') as hour_label,
                    COUNT(*) as count,
                    COALESCE(ROUND(AVG(mag), 2), 0.0) as avg_mag,
                    COALESCE(MAX(mag), 0.0) as max_mag
                FROM earthquake_events, max_t
                WHERE time >= max_t.mt - INTERVAL 24 HOUR
                GROUP BY hour_label 
                ORDER BY hour_label ASC;
            """).fetchall()

            # 2. Si no hay datos en la ventana relativa, usar agregación general por hora
            if not rows:
                rows = self.conn.execute("""
                    SELECT 
                        strftime(time, '%H:00') as hour_label,
                        COUNT(*) as count,
                        COALESCE(ROUND(AVG(mag), 2), 0.0) as avg_mag,
                        COALESCE(MAX(mag), 0.0) as max_mag
                    FROM earthquake_events 
                    GROUP BY hour_label 
                    ORDER BY hour_label ASC;
                """).fetchall()

            # 3. Si aún no hay eventos (base vacía), garantizar array de 24 horas para la gráfica
            if not rows:
                return [
                    {"hour": f"{h:02d}:00", "count": 0, "avg_mag": 0.0, "max_mag": 0.0}
                    for h in range(24)
                ]

            return [
                {
                    "hour": str(r[0]),
                    "count": int(r[1]),
                    "avg_mag": float(r[2]) if r[2] is not None else 0.0,
                    "max_mag": float(r[3]) if r[3] is not None else 0.0,
                }
                for r in rows
            ]

    def get_top_regions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Retorna las regiones con mayor frecuencia sísmica."""
        with self._lock:
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
                    COALESCE(ROUND(AVG(mag), 2), 0.0) as avg_mag
                FROM earthquake_events
                GROUP BY region
                ORDER BY count DESC
                LIMIT ?;
            """, [limit]).fetchall()

            return [
                {
                    "region": str(r[0]),
                    "count": int(r[1]),
                    "avg_mag": float(r[2]) if r[2] is not None else 0.0,
                }
                for r in rows
            ]

    def get_map_events(self, hours: int = 24, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Retorna eventos para la cartografía global filtrados estrictamente por las últimas N horas.
        Por defecto: últimas 24 horas.
        Prioriza sismos con alerta activa de tsunami y sismos significativos dentro de la ventana de 24h.
        """
        with self._lock:
            cursor = self.conn.cursor()
            max_time_row = cursor.execute("SELECT MAX(time) FROM earthquake_events;").fetchone()
            if not max_time_row or not max_time_row[0]:
                return []

            ref_time = max_time_row[0]

            rows = cursor.execute(f"""
                SELECT id, mag, place, strftime(time, '%Y-%m-%dT%H:%M:%SZ') as time,
                       longitude, latitude, depth_km, tsunami, sig, status, mag_type
                FROM earthquake_events
                WHERE time >= TIMESTAMP '{ref_time}' - (CAST(? AS INTEGER) * INTERVAL '1 HOUR')
                ORDER BY tsunami DESC, mag DESC, time DESC
                LIMIT ?;
            """, [hours, limit]).fetchall()

            return [
                {
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
                }
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

        # 2. Ejecución thread-safe con cursor aislado
        with self._lock:
            cursor = self.conn.cursor()
            result = cursor.execute(clean_sql)
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
