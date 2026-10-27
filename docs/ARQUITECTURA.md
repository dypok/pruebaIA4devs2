# Documento de Arquitectura de Datos: Plataforma SismoWatch (Lakehouse con Spark, Parquet y DuckDB)

## 1. Propósito de la Arquitectura

### 1.1 Problema que Resuelve
SuperApp requiere monitorear la sismicidad global en tiempo casi real para anticipar impactos operativos y mitigar riesgos en sus operaciones logísticas, infraestructura y base de usuarios. La fuente pública del **USGS (United States Geological Survey)** publica un feed de sismos que cambia cada minuto; sin embargo, este feed:
- **No preserva historial:** Únicamente expone una ventana móvil de eventos recientes.
- **Sufre mutaciones posteriores:** Los sismos son recalculados por sismólogos (cambios de magnitud, estado de revisión o relocalización de coordenadas), generando riesgo de duplicidad o inconsistencia.
- **Carece de validación de calidad y control de esquema:** Datos anómalos o malformados pueden propagarse sin control.
- **No ofrece síntesis ejecutiva ni consumo ágil:** No existe una plataforma centralizada que permita a los analistas de riesgo visualizar mapas, consultar gráficos, recibir reportes ejecutivos o consultar datos en lenguaje natural.

### 1.2 A Quién Sirve
- **Área de Gestión de Riesgo y Operaciones:** Para priorizar toma de decisiones, activar protocolos de contingencia ante eventos de alta magnitud o alertas de tsunami, y consultar tendencias territoriales.
- **Ingenieros y Operadores de Datos:** Para monitorear la salud del pipeline, recibir alertas inmediatas de registros con anomalías de esquema o calidad, y auditar la frescura del dato.
- **Directivos de SuperApp:** Para recibir resúmenes ejecutivos diarios generados por IA con métricas consolidadas matemáticamente confiables.

---

## 2. Diagrama de Arquitectura: Data Lakehouse (Spark ➔ Gold Parquet ➔ DuckDB)

```mermaid
flowchart TD
    subgraph CapaFuente["1. Fuente Externa"]
        USGS_RT["USGS Real-Time Feed<br/>(GeoJSON all_hour / 5 min)"]
        USGS_HIST["USGS Query API<br/>(Backfill histórico 30 días)"]
    end

    subgraph CapaOrquestacion["2. Orquestación (Apache Airflow)"]
        DAG_INGEST["dag_usgs_ingestion<br/>(Cada 5 min)"]
        DAG_TRANSFORM["dag_transform_quality<br/>(Trigger automático)"]
        DAG_REPORT["dag_ai_daily_report<br/>(Diario 00:00 UTC)"]
        DAG_BACKFILL["dag_historical_backfill<br/>(Parametrizado: 30 días)"]
        ALERTA_TASK["notify_invalid_records<br/>(Alerta inmediata en UI de Airflow)"]
    end

    subgraph CapaProcesamiento["3. Procesamiento Distribuido (Apache Spark)"]
        SPARK_JOB["Apache Spark (PySpark)<br/>• Desanidado de FeatureCollection<br/>• Casting de Epoch a Timestamps<br/>• Validación Pandera<br/>• Generación de Parquet particionado"]
        ANOMALY_ML["Modelo de Anomalías<br/>(IsolationForest & Z-score)"]
    end

    subgraph CapaAlmacenamiento["4. Capa Lakehouse (Parquet Gold + Metastore)"]
        RAW_STORE["Landing Raw<br/>data/raw/ (JSONB/GeoJSON)"]
        GOLD_PARQUET[("Capa GOLD (Columnar Parquet)<br/>data/gold/earthquake_events/<br/>year=YYYY/month=MM/events.parquet")]
        POSTGRES_META[("PostgreSQL Metastore<br/>• users (RBAC con bcrypt)<br/>• quality_metrics<br/>• ai_reports & logs<br/>• anomaly_alerts")]
    end

    subgraph CapaConsulta["5. Motor Vectorizado OLAP (DuckDB)"]
        DUCKDB_ENGINE["DuckDB In-Memory Engine<br/>• Lectura directa de Parquet sin bloqueos<br/>• Ejecución vectorizada en milisegundos<br/>• View: earthquake_events"]
    end

    subgraph CapaIA["6. Inteligencia Artificial Local (Ollama)"]
        OLLAMA_SERVER["Ollama Daemon (Inferencia Local CPU)"]
        MODEL_QWEN["Modelo Qwen 2.5:2b<br/>(Text-to-SQL DuckDB)"]
    end

    subgraph CapaServicio["7. Capa de API y Backend (FastAPI)"]
        FASTAPI_CORE["FastAPI REST & SSE Server"]
        AUTH_JWT["Seguridad RBAC (JWT)<br/>Viewer vs Admin"]
        CHAT_SERVICE["Servicio de Chatbot<br/>(Prompt ➔ SQL DuckDB ➔ Síntesis)"]
    end

    subgraph CapaConsumo["8. Consumo Web (React + TypeScript + Vite)"]
        METRIC_RIBBON["Metric Ribbon Unificado<br/>(Métricas clave sin cards pesadas)"]
        LEAFLET_MAP["Mapa Interactivo Global (Leaflet)"]
        TIME_CHARTS["Series Temporales y Distribución (Recharts)"]
        SSE_LIVE["Recepción En Vivo (SSE)"]
        CHATBOT_WIDGET["Drawer Chatbot SismoWatch AI<br/>(Consultas DuckDB en lenguaje natural)"]
    end

    %% Conexiones
    USGS_RT -->|HTTP GET (try/catch)| DAG_INGEST
    USGS_HIST -->|HTTP GET| DAG_BACKFILL

    DAG_INGEST -->|Escribe dato crudo| RAW_STORE
    DAG_INGEST -->|Trigger| DAG_TRANSFORM

    RAW_STORE --> SPARK_JOB
    SPARK_JOB -->|Escribe particiones Parquet| GOLD_PARQUET
    SPARK_JOB -->|Registra métricas| POSTGRES_META
    SPARK_JOB -.->|Si hay registros INVALID| ALERTA_TASK

    GOLD_PARQUET --> ANOMALY_ML
    ANOMALY_ML -->|Alertas| POSTGRES_META

    GOLD_PARQUET -->|read_parquet()| DUCKDB_ENGINE
    DUCKDB_ENGINE <--> FASTAPI_CORE

    FASTAPI_CORE <--> CHAT_SERVICE
    CHAT_SERVICE <-->|Text-to-SQL| MODEL_QWEN
    CHAT_SERVICE <-->|Ejecuta SQL seguro| DUCKDB_ENGINE

    FASTAPI_CORE --> METRIC_RIBBON
    FASTAPI_CORE --> LEAFLET_MAP
    FASTAPI_CORE --> TIME_CHARTS
    FASTAPI_CORE --> SSE_LIVE
    FASTAPI_CORE <--> CHATBOT_WIDGET
```

---

## 3. Justificación Técnica: El Poder de Spark + Parquet + DuckDB

| Componente | Elección | Justificación Técnica |
| :--- | :--- | :--- |
| **Transformación** | **Apache Spark (PySpark)** | Procesa el JSON complejo de USGS de forma distribuida, desanida geometrías y propiedades, ejecuta validaciones de calidad y escribe archivos **Parquet** altamente comprimidos (Snappy) y particionados por año y mes. |
| **Almacenamiento Gold** | **Apache Parquet** | Formato columnar abierto estándar en la industria. Reduce el tamaño en disco hasta un 85% frente a JSON/filas relacionales y almacena metadatos de estadísticas de columnas (mínimos, máximos) que permiten *predicate pushdown* instantáneo. |
| **Motor de Consulta y Chatbot** | **DuckDB** | DuckDB se conecta directamente a los archivos Parquet en memoria (`read_parquet('data/gold/earthquake_events/**/*.parquet')`). Al ser de solo lectura para las consultas, **no genera bloqueos de concurrencia**. Ejecuta agregaciones analíticas vectorizadas en menos de 5 ms. |
| **Chatbot Text-to-SQL** | **Qwen 2.5:2b (Ollama)** | El modelo traduce la pregunta del usuario directamente a una sintaxis SQL compatible con DuckDB (`SELECT place, mag, time FROM earthquake_events ...`). DuckDB ejecuta la consulta contra los archivos Parquet y el modelo redacta la respuesta en lenguaje natural para el usuario. |
| **Metastore y Seguridad** | **PostgreSQL** | Maneja la autenticación JWT de usuarios (`curated.users`), métricas históricas de calidad, reportes diarios y la base de datos de metadatos de Airflow. |

---

## 4. Estructura de Datos en Disco y Metadatos

### 4.1 Capa Gold en Parquet (`data/gold/earthquake_events/`)
Particionado por fecha:
```
data/gold/earthquake_events/
├── year=2026/
│   └── month=10/
│       ├── part-00000.snappy.parquet
│       └── part-00001.snappy.parquet
```
**Esquema de columnas en Parquet:**
- `id` (STRING, Primary Key del evento)
- `mag` (DOUBLE, Magnitud)
- `place` (STRING, Ubicación geográfica descriptiva)
- `time` (TIMESTAMP, Fecha y hora del evento)
- `updated` (TIMESTAMP, Última actualización de USGS)
- `longitude` (DOUBLE, Coordenada decimal)
- `latitude` (DOUBLE, Coordenada decimal)
- `depth_km` (DOUBLE, Profundidad en kilómetros)
- `tsunami` (INTEGER, 0 = No, 1 = Sí)
- `sig` (INTEGER, Nivel de significancia)
- `mag_type` (STRING, Tipo de magnitud)
- `status` (STRING, Estado del sismo)
- `processing_status` (STRING, `VALID` / `CORRECTED`)

### 4.2 Vista DuckDB en FastAPI
```python
import duckdb

# Conexión en memoria que monta la vista sobre los Parquets
con = duckdb.connect(database=":memory:")
con.execute("""
    CREATE OR REPLACE VIEW earthquake_events AS 
    SELECT * FROM read_parquet('data/gold/earthquake_events/**/*.parquet')
""")
```

---

## 5. Alerta Inmediata en Airflow y Resiliencia `try/catch`
1. Durante la ejecución de Spark, cada evento pasa por las reglas de Pandera.
2. Si un registro tiene anomalías (latitud fuera de rango, fecha errónea), se clasifica como `INVALID`.
3. **Alerta Inmediata:** Si el lote contiene registros inválidos, se dispara la tarea `notify_invalid_records` en Airflow, notificando al operador en los logs y la interfaz para su revisión.
4. Los registros conformes se consolidan en los Parquet de la capa Gold sin detener el flujo.
