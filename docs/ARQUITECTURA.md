# Documento de Arquitectura de Datos: Plataforma SismoWatch

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

### 1.3 Decisiones que Habilita
- **Despacho de alertas tempranas:** Identificación de eventos con `tsunami = 1` o magnitud $\ge 6.0$.
- **Priorización logística territorial:** Reubicación o suspensión de operaciones en regiones con enjambres sísmicos detectados por modelos de Machine Learning.
- **Gobernanza de calidad:** Corrección inmediata de registros marcados como no procesables (`INVALID`) antes de que impacten los tableros de mando.

---

## 2. Diagrama de Arquitectura y Capas

```mermaid
flowchart TD
    subgraph CapaFuente["1. Capa de Ingesta y Fuentes Externas"]
        USGS_RT["USGS Real-Time Feed<br/>(GeoJSON all_hour / 5 min)"]
        USGS_HIST["USGS Query API<br/>(Backfill histórico 30 días)"]
    end

    subgraph CapaOrquestacion["2. Capa de Orquestación (Apache Airflow)"]
        DAG_INGEST["dag_usgs_ingestion<br/>(Programado: */5 * * * *)"]
        DAG_TRANSFORM["dag_transform_quality<br/>(Trigger automático)"]
        DAG_REPORT["dag_ai_daily_report<br/>(Programado diario / On-demand)"]
        DAG_BACKFILL["dag_historical_backfill<br/>(Parametrizado: fechas y magnitud)"]
        ALERTA_TASK["notify_invalid_records<br/>(Alerta inmediata en UI de Airflow)"]
    end

    subgraph CapaProcesamiento["3. Capa de Procesamiento Distribuido (Spark & ML)"]
        SPARK_JOB["Apache Spark (PySpark)<br/>• Desanidado de FeatureCollection<br/>• Casting de Epoch a Timestamps<br/>• Agregaciones horarias"]
        PANDERA_ENGINE["Motor de Calidad (Pandera)<br/>• Validación de límites espaciales<br/>• Validación de magnitud y profundidad<br/>• Asignación de estado VALID / INVALID"]
        ANOMALY_ML["Modelo de Anomalías<br/>(IsolationForest & Z-score)"]
    end

    subgraph CapaAlmacenamiento["4. Capa de Almacenamiento Multicapa (PostgreSQL)"]
        direction TB
        RAW_SCHEMA[("Schema RAW (Bronze)<br/>earthquake_events_raw<br/>Payload JSONB inmutable")]
        STAGING_SCHEMA[("Schema STAGING (Silver)<br/>earthquake_events_staging<br/>Columnas tipadas y processing_status")]
        CURATED_SCHEMA[("Schema CURATED (Gold)<br/>• earthquake_events (solo VALID)<br/>• quality_metrics<br/>• ai_reports & ai_execution_logs<br/>• anomaly_alerts<br/>• users (RBAC)")]
    end

    subgraph CapaIA["5. Capa de Inteligencia Artificial Local (Ollama)"]
        OLLAMA_SERVER["Ollama Daemon (Inferencia Local en CPU)"]
        MODEL_QWEN["Modelo Qwen 2.5:2b<br/>(Text-to-SQL y Chatbot)"]
        FALLBACK_AI["Motor Determinista Fallback<br/>(Garantía anti-caídas)"]
    end

    subgraph CapaServicio["6. Capa de API y Backend (FastAPI)"]
        FASTAPI_CORE["FastAPI REST & SSE Engine"]
        AUTH_JWT["Seguridad RBAC (JWT)<br/>Viewer vs Admin"]
        ROLE_PLATFORM["Rol de BD: user_platform<br/>(SELECT exclusivo sobre CURATED)"]
    end

    subgraph CapaConsumo["7. Capa de Consumo Web (React + TypeScript + Vite)"]
        METRIC_RIBBON["Metric Ribbon Unificado<br/>(Métricas clave sin cards pesadas)"]
        LEAFLET_MAP["Mapa Interactivo Global (Leaflet)"]
        TIME_CHARTS["Series Temporales y Distribución (Recharts)"]
        SSE_LIVE["Recepción En Vivo (SSE)"]
        CHATBOT_WIDGET["Drawer Chatbot SismoWatch AI<br/>(Consultas en lenguaje natural)"]
    end

    %% Conexiones de datos
    USGS_RT -->|HTTP GET (try/catch)| DAG_INGEST
    USGS_HIST -->|HTTP GET| DAG_BACKFILL

    DAG_INGEST -->|Escribe JSONB crudo| RAW_SCHEMA
    DAG_INGEST -->|Dispara ejecución| DAG_TRANSFORM

    RAW_SCHEMA -->|Lectura con user_transform| SPARK_JOB
    SPARK_JOB -->|Escribe registros desanidados| STAGING_SCHEMA

    STAGING_SCHEMA --> PANDERA_ENGINE
    PANDERA_ENGINE -->|Reglas conformes: VALID| CURATED_SCHEMA
    PANDERA_ENGINE -->|Reglas fallidas: INVALID| STAGING_SCHEMA
    PANDERA_ENGINE -->|invalid_count > 0| ALERTA_TASK

    CURATED_SCHEMA --> ANOMALY_ML
    ANOMALY_ML -->|Alertas detectadas| CURATED_SCHEMA

    CURATED_SCHEMA --> DAG_REPORT
    DAG_REPORT -->|Prompt desinfectado| OLLAMA_SERVER
    OLLAMA_SERVER --> MODEL_QWEN
    MODEL_QWEN -.->|Si hay timeout/error| FALLBACK_AI
    DAG_REPORT -->|Reporte verificado| CURATED_SCHEMA

    CURATED_SCHEMA -->|Conexión user_platform| FASTAPI_CORE
    FASTAPI_CORE <-->|Consultas SQL seguras| OLLAMA_SERVER
    FASTAPI_CORE --> METRIC_RIBBON
    FASTAPI_CORE --> LEAFLET_MAP
    FASTAPI_CORE --> TIME_CHARTS
    FASTAPI_CORE --> SSE_LIVE
    FASTAPI_CORE <--> CHATBOT_WIDGET
```

---

## 3. Justificación Técnica de las Herramientas Elegidas

| Componente | Herramienta Elegida | Alternativas Evaluadas | Justificación Técnica y Criterio de Selección |
| :--- | :--- | :--- | :--- |
| **Orquestación** | **Apache Airflow** | Cron Linux, Celery Beat | Un cron carece de observabilidad, reintentos automáticos configurables (`exponential_backoff`), gestión de dependencias entre tareas (DAGs), trazabilidad de estados y soporte nativo para `backfill`. Airflow provee gobernanza operativa completa, alertas en fallos y linaje claro de datos. |
| **Procesamiento** | **Apache Spark (PySpark)** | Pandas puro, scripts SQL | PySpark permite paralelismo multinúcleo para procesar payloads GeoJSON masivos. La manipulación de estructuras complejas anidadas (`features[*].properties`, `features[*].geometry.coordinates`) se optimiza mediante el Catalyst Optimizer de Spark, garantizando escalabilidad inmediata ante backfills de meses o años. |
| **Almacenamiento** | **PostgreSQL (3 Schemas)** | MongoDB, MySQL, Snowflake | PostgreSQL ofrece soporte nativo avanzado para JSONB en la capa `raw`, transacciones ACID con soporte de idempotencia (`ON CONFLICT (id) DO UPDATE`), y aislamiento de privilegios mediante esquemas independientes (`raw`, `staging`, `curated`). |
| **Calidad de Datos** | **Pandera** | Great Expectations, dbt tests | Pandera ofrece definición declarativa de esquemas basada en código Python puro y DataFrames de Spark/Pandas, tipado estricto y alto rendimiento sin la complejidad de configuración de Great Expectations. |
| **Backend API** | **FastAPI** | Flask, Django, Express | FastAPI es asíncrono nativo (ASGI), ultra-rápido, tipado con Pydantic V2, provee documentación interactiva automática OpenAPI/Swagger y facilita la transmisión de eventos en tiempo real mediante **Server-Sent Events (SSE)**. |
| **Frontend Web** | **React + TS + Vite** | Streamlit, Dash, HTML plano | Streamlit renderiza la página completa ante cada interacción y no permite un control granular de layouts avanzados ni conexiones SSE fluidas. React con Vite entrega un rendimiento instantáneo (HMR), mapa Leaflet dinámico sin parpadeos y experiencia de usuario fluida sin exceso de cards ni badges. |
| **Motor de Chatbot** | **Ollama (Qwen 2.5:2b)** | OpenAI API, Claude API | Permite ejecución 100% local en CPU, costo de inferencia cero, privacidad estricta (ningún dato de infraestructura sale de la red local) y excelente capacidad de generación de SQL y comprensión del español en solo ~1.5 GB de RAM. |
| **Tiempo Real** | **Server-Sent Events (SSE)** | WebSockets, Polling corto | La transmisión de sismos es unidireccional (del servidor al cliente). SSE funciona sobre HTTP estándar, reconecta automáticamente de forma nativa en el navegador, atraviesa proxies y firewalls corporativos sin protocolos complejos, y evita la sobrecarga de handshake de WebSockets. |

---

## 4. Modelo de Datos Documentado

### 4.1 Schema `raw`
* **`raw.earthquake_events_raw`**:
  - `id VARCHAR(64) PRIMARY KEY`: Identificador único del evento según USGS (ej. `ci41353455`, `us6000tyxk`).
  - `fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`: Fecha y hora exacta de captura.
  - `payload JSONB NOT NULL`: Estructura JSON íntegra del GeoJSON original.
  - `ingestion_source VARCHAR(64) NOT NULL`: Origen (`usgs_all_hour`, `usgs_backfill_query`).

### 4.2 Schema `staging`
* **`staging.earthquake_events_staging`**:
  - `id VARCHAR(64) PRIMARY KEY`: Identificador del sismo.
  - `mag NUMERIC(4,2)`: Magnitud registrada.
  - `place TEXT`: Descripción textual del epicentro.
  - `time TIMESTAMPTZ NOT NULL`: Fecha y hora del sismo (convertida de epoch ms).
  - `updated TIMESTAMPTZ`: Fecha de última actualización de USGS.
  - `longitude NUMERIC(9,6) NOT NULL`: Longitud decimal [-180, 180].
  - `latitude NUMERIC(9,6) NOT NULL`: Latitud decimal [-90, 90].
  - `depth_km NUMERIC(7,2) NOT NULL`: Profundidad en kilómetros.
  - `tsunami SMALLINT DEFAULT 0`: Indicador de riesgo de tsunami (0 o 1).
  - `sig INTEGER`: Nivel de significancia del evento sísmico.
  - `status VARCHAR(32)`: Estado en USGS (`reviewed`, `automatic`).
  - `mag_type VARCHAR(16)`: Escala de medición (`mw`, `ml`, `md`, etc.).
  - `processing_status VARCHAR(20) DEFAULT 'PENDING'`: Estado de ciclo de vida (`PENDING`, `VALID`, `INVALID`, `CORRECTED`).
  - `validation_error TEXT`: Motivo de rechazo en caso de regla no superada.
  - `failed_rules JSONB`: Lista estructurada de reglas que fallaron.
  - `processed_at TIMESTAMPTZ DEFAULT NOW()`: Timestamp de procesamiento.

### 4.3 Schema `curated`
* **`curated.earthquake_events`**:
  - Almacena únicamente registros que alcanzaron el estado `processing_status = 'VALID'` o `'CORRECTED'`.
  - Índices:
    - `idx_curated_time` en `(time DESC)` para consultas cronológicas.
    - `idx_curated_mag` en `(mag)` para filtrado por severidad.
    - `idx_curated_coords` en `(latitude, longitude)` para renderizado geoespacial.
* **`curated.quality_metrics`**:
  - `id SERIAL PRIMARY KEY`
  - `dag_id VARCHAR(64)`, `run_id VARCHAR(128)`, `execution_date TIMESTAMPTZ`
  - `total_records INT`, `valid_records INT`, `invalid_records INT`
  - `quality_score NUMERIC(5,2)`: Porcentaje de registros válidos.
  - `rules_summary JSONB`: Desglose de evaluaciones por regla.
* **`curated.anomaly_alerts`**:
  - `id SERIAL PRIMARY KEY`
  - `event_id VARCHAR(64) REFERENCES curated.earthquake_events(id)`
  - `anomaly_score NUMERIC(6,3)`
  - `anomaly_type VARCHAR(64)`: Enjambre sísmico, pico de magnitud, profundidad extrema.
  - `explanation TEXT`: Descripción legible generada para el equipo de riesgo.
  - `detected_at TIMESTAMPTZ DEFAULT NOW()`
* **`curated.ai_reports`**:
  - `id SERIAL PRIMARY KEY`
  - `report_date DATE UNIQUE`
  - `title TEXT`, `executive_summary TEXT`
  - `active_zones JSONB`, `highlighted_events JSONB`, `calculated_metrics JSONB`
  - `ai_verified BOOLEAN DEFAULT TRUE`: Bandera que confirma concordancia numérica matemática.
  - `generated_at TIMESTAMPTZ DEFAULT NOW()`
* **`curated.ai_execution_logs`**:
  - `id SERIAL PRIMARY KEY`, `report_id INT REFERENCES curated.ai_reports(id)`
  - `model VARCHAR(64)`, `prompt_name VARCHAR(64)`, `prompt_tokens INT`, `completion_tokens INT`, `latency_ms INT`, `cost_usd NUMERIC(8,6)`, `status VARCHAR(32)`
* **`curated.users`**:
  - `id SERIAL PRIMARY KEY`, `username VARCHAR(64) UNIQUE`, `password_hash VARCHAR(255)`, `role VARCHAR(32) CHECK (role IN ('viewer', 'admin'))`

---

## 5. Decisiones Técnicas y Trade-offs

### 5.1 ¿Por qué Airflow y no un script o un Cron?
- **Idempotencia y Backfilling:** Un cron no entiende el concepto de intervalo de ejecución (`data_interval_start`, `data_interval_end`). Si el servicio se interrumpe durante 3 horas, el cron pierde las ejecuciones; Airflow permite re-ejecutar intervalos pasados (Backfill) sin duplicar datos.
- **Tolerancia a Fallos:** Airflow ofrece políticas de reintento (`retries=3`, `retry_delay=timedelta(seconds=30)`, `retry_exponential_backoff=True`) y callbacks de alerta ante caídas.
- **Linaje y Dependencias:** Airflow orquesta el flujo en grafos acíclicos dirigidos (DAGs), garantizando que la transformación solo se dispare si la ingesta concluyó exitosamente.

### 5.2 ¿Por qué una arquitectura de 3 capas (Raw, Staging, Curated)?
- **Capa Raw:** Garantiza la inmutabilidad de la fuente. Si el día de mañana se requiere extraer una propiedad adicional del GeoJSON (ej. `properties.felt` o `properties.gap`), no es necesario volver a consultar a USGS; se reprocesa desde `raw`.
- **Capa Staging:** Desacopla la lógica pesada de transformación (PySpark) de la capa de consumo. Permite normalizar tipos, imputar valores y evaluar la calidad.
- **Capa Curated:** Garantiza que los analistas de negocio, el frontend y el Chatbot consulten **únicamente datos 100% certificados**. Ninguna consulta analítica compite con los bloqueos de escritura de la ingesta.

### 5.3 ¿Cómo funciona el manejo de estados y la alerta inmediata en Airflow?
En lugar de una tabla de cuarentena separada que duplique esquemas, adoptamos una **Máquina de Estados de Datos**:
1. Todo dato transformado se etiqueta inicialmente como `PENDING`.
2. Las pruebas de Pandera evalúan la validez matemática y física de cada evento.
3. Si un dato tiene coordenadas o magnitudes imposibles, su estado cambia a `INVALID` y se graba el detalle del error en `validation_error`.
4. El pipeline ejecuta la tarea de control `check_data_quality`:
   - Si `invalid_count > 0`, se detona la tarea **`notify_invalid_records`**, la cual emite un log crítico y activa una alerta en la UI de Airflow para que el operador atienda y corrija el registro.
   - **El pipeline no se aborta de forma descontrolada**: los registros con `VALID` continúan a `curated.earthquake_events` para que SuperApp nunca se quede a oscuras.

---

## 6. Qué Haríamos Diferente en un Escenario de Producción Masiva

1. **Ingesta Orientada a Streaming con Apache Kafka o Redpanda:** En lugar de micro-lotes cada 5 minutos, los eventos se publicarían en un topic de Kafka, permitiendo latencias de ingestion inferiores a 1 segundo.
2. **Data Lakehouse en S3 / MinIO con Apache Iceberg o Delta Lake:** La capa `raw` y `staging` se almacenarían en almacenamiento de objetos en formato Parquet/Iceberg, reduciendo costos de almacenamiento en PostgreSQL en más del 80%.
3. **Airflow sobre Kubernetes Executor (MWAA o Astro):** Cada tarea del DAG correría en su propio pod efímero con recursos dinámicos, escalando a cero cuando el pipeline esté inactivo.
4. **Gestión Centralizada de Secretos:** Integración con **HashiCorp Vault** o **AWS Secrets Manager**, rotando automáticamente las credenciales de base de datos y llaves JWT.
5. **Caché en Memoria y Pub/Sub con Redis:** Para distribuir los eventos en tiempo real hacia millones de clientes concurrentes vía WebSocket clusters en lugar de una única instancia FastAPI.
