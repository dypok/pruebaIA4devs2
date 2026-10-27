# Documento de Arquitectura de Datos: Plataforma SismoWatch (Data Lakehouse con MinIO, Spark, Parquet, DuckDB y Dashboards Dinámicos con IA)

## 1. Propósito de la Arquitectura

### 1.1 Problema que Resuelve
SuperApp requiere monitorear la sismicidad global en tiempo casi real para anticipar impactos operativos y mitigar riesgos en sus operaciones logísticas, infraestructura y base de usuarios. La fuente pública del **USGS (United States Geological Survey)** publica un feed de sismos que cambia cada minuto; sin embargo, este feed:
- **No preserva historial:** Únicamente expone una ventana móvil de eventos recientes.
- **Sufre mutaciones posteriores:** Los sismos son recalculados por sismólogos (cambios de magnitud, estado de revisión o relocalización de coordenadas), generando riesgo de duplicidad o inconsistencia.
- **Carece de validación de calidad y control de esquema:** Datos anómalos o malformados pueden propagarse sin control.
- **No ofrece síntesis ejecutiva ni consumo ágil:** No existe una plataforma centralizada que permita a los analistas de riesgo visualizar mapas, consultar gráficos, recibir reportes ejecutivos o consultar datos en lenguaje natural con generación automática de visualizaciones interactivas.

### 1.2 A Quién Sirve
- **Área de Gestión de Riesgo y Operaciones:** Para priorizar toma de decisiones, activar protocolos de contingencia ante eventos de alta magnitud o alertas de tsunami, y consultar tendencias territoriales.
- **Ingenieros y Operadores de Datos:** Para monitorear la salud del pipeline, recibir alertas inmediatas de registros con anomalías de esquema o calidad, y auditar la frescura del dato.
- **Directivos de SuperApp:** Para recibir resúmenes ejecutivos diarios generados por IA con métricas consolidadas matemáticamente confiables y crear gráficos analíticos personalizados fijables en el dashboard.

---

## 2. Diagrama de Flujo Medallion (Bronze ➔ Silver ➔ Gold)

```mermaid
flowchart LR
    USGS["API USGS"] -->|Ingesta cruda| Bronze["BRONZE (MinIO S3)<br/>GeoJSON inmutable"]
    Bronze -->|Apache Spark: Desanidar + Tipar| Silver["SILVER (MinIO Parquet)<br/>VALID + INVALID con motivos"]
    
    Silver -.->|Si hay INVALID| AlertaAirflow["⚠️ Alerta Inmediata<br/>en Airflow"]
    Silver -->|Filtro: solo VALID + Enriquecimiento| Gold["GOLD (MinIO Parquet)<br/>Datos certificados + Agregaciones"]
    
    Gold -->|read_parquet() con httpfs| DuckDB["DuckDB Engine<br/>(FastAPI)"]
    DuckDB --> Chatbot["Chatbot Qwen 2.5:2b<br/>(Text-to-SQL + Auto-Chart)"]
    Chatbot -->|📌 Fijar gráfico dinámico| Dashboard["Dashboard React en Vivo<br/>(Se actualiza con SSE)"]
```

---

## 3. Diagrama Integral de Componentes de Punta a Punta

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

    subgraph CapaLakehouse["3. Object Storage Data Lake (MinIO S3)"]
        direction TB
        MINIO_RAW[("BRONZE: sismowatch-lake/bronze/<br/>events_HHMMSS.geojson")]
        MINIO_SILVER[("SILVER: sismowatch-lake/silver/<br/>Parquet: VALID + INVALID con error_detail")]
        MINIO_GOLD[("GOLD: sismowatch-lake/gold/<br/>Parquet certificado (solo VALID)")]
    end

    subgraph CapaProcesamiento["4. Procesamiento Distribuido (Apache Spark)"]
        SPARK_JOB["Apache Spark (PySpark)<br/>• Lectura de Bronze S3A<br/>• Desanidado, tipado y Pandera<br/>• Escritura a Silver Parquet<br/>• Promoción a Gold Parquet"]
        ANOMALY_ML["Detección de Anomalías<br/>(IsolationForest & Z-score)"]
    end

    subgraph CapaMetastore["5. Metastore y Seguridad (PostgreSQL)"]
        POSTGRES_DB[("PostgreSQL 16<br/>• users (Admin & Viewer con bcrypt)<br/>• quality_metrics<br/>• ai_reports & ai_execution_logs<br/>• anomaly_alerts<br/>• Airflow Metastore")]
    end

    subgraph CapaConsulta["6. Motor Vectorizado OLAP (DuckDB)"]
        DUCKDB_ENGINE["DuckDB In-Memory Engine<br/>• Conexión HTTPFS a MinIO S3 (minio:9000)<br/>• Lectura de Gold sin bloqueos<br/>• View: earthquake_events"]
    end

    subgraph CapaIA["7. Inteligencia Artificial Local (Ollama)"]
        OLLAMA_SERVER["Ollama Daemon (Inferencia Local CPU)"]
        MODEL_QWEN["Modelo Qwen 2.5:2b<br/>(Text-to-SQL + Sugerencia de Gráficos)"]
    end

    subgraph CapaServicio["8. Capa de API y Backend (FastAPI)"]
        FASTAPI_CORE["FastAPI REST & SSE Server"]
        AUTH_JWT["Seguridad RBAC (JWT)<br/>Viewer vs Admin"]
        CHAT_SERVICE["Servicio Chatbot y Auto-Charts<br/>(SQL ➔ DuckDB ➔ Datos estructurados ➔ Tipo de Gráfico)"]
    end

    subgraph CapaConsumo["9. Consumo Web (React + TypeScript + Vite)"]
        METRIC_RIBBON["Metric Ribbon Unificado<br/>(Métricas clave sin cards pesadas)"]
        LEAFLET_MAP["Mapa Interactivo Global (Leaflet)"]
        PINNED_CHARTS["Panel de Gráficos Fijados desde Chatbot<br/>(Reactivos a eventos en tiempo real SSE)"]
        SSE_LIVE["Recepción En Vivo (SSE)"]
        CHATBOT_WIDGET["Drawer Chatbot SismoWatch AI<br/>(Generación de Gráficos con botón 📌 Fijar)"]
    end

    %% Conexiones
    USGS_RT -->|HTTP GET (try/catch)| DAG_INGEST
    USGS_HIST -->|HTTP GET| DAG_BACKFILL

    DAG_INGEST -->|Escribe GeoJSON crudo| MINIO_RAW
    DAG_INGEST -->|Trigger| DAG_TRANSFORM

    MINIO_RAW -->|Lee con S3A| SPARK_JOB
    SPARK_JOB -->|Escribe Parquets desanidados| MINIO_SILVER
    SPARK_JOB -.->|Si hay registros INVALID| ALERTA_TASK
    SPARK_JOB -->|Promueve conformes| MINIO_GOLD
    SPARK_JOB -->|Registra métricas| POSTGRES_DB

    MINIO_GOLD --> ANOMALY_ML
    ANOMALY_ML -->|Alertas| POSTGRES_DB

    MINIO_GOLD -->|S3 read_parquet() vía httpfs| DUCKDB_ENGINE
    DUCKDB_ENGINE <--> FASTAPI_CORE

    FASTAPI_CORE <--> CHAT_SERVICE
    CHAT_SERVICE <-->|Text-to-SQL| MODEL_QWEN
    CHAT_SERVICE <-->|Ejecuta SQL seguro| DUCKDB_ENGINE

    FASTAPI_CORE --> METRIC_RIBBON
    FASTAPI_CORE --> LEAFLET_MAP
    FASTAPI_CORE --> PINNED_CHARTS
    FASTAPI_CORE --> SSE_LIVE
    FASTAPI_CORE <--> CHATBOT_WIDGET
    CHATBOT_WIDGET -.->|📌 Fijar gráfico personalizado| PINNED_CHARTS
```

---

## 4. Gráficos Dinámicos y Fijables en el Dashboard desde el Chatbot

### 4.1 Generación Automática de Gráficos (Auto-Chart)
Cuando un usuario consulta al Chatbot en lenguaje natural:
1. **Traducción SQL:** `qwen2.5:2b` genera la consulta DuckDB de solo lectura.
2. **Ejecución Vectorizada:** DuckDB ejecuta la consulta sobre los Parquet de MinIO y obtiene los registros en milisegundos.
3. **Inferencia de Tipo de Gráfico:** El servicio analiza la estructura de los datos resultantes:
   - *Tiempo + Métrica numéricas:* Gráfico de líneas o áreas temporales (`line` / `area`).
   - *Categoría geográfica + Métrica:* Gráfico de barras horizontales o verticales (`bar`).
   - *Distribución de magnitudes:* Histograma o distribución (`histogram`).
4. **Renderizado en el Chat:** El Chatbot dibuja el gráfico interactivo (Recharts) en la misma ventana de conversación, junto con la síntesis explicativa.

### 4.2 Fijación y Reactividad en Tiempo Real (Pin to Dashboard)
- **Botón `📌 Fijar al Dashboard`:** Permite al usuario añadir ese gráfico a la sección de **"Visualizaciones Personalizadas"** del Dashboard principal.
- **Actualización Reactiva Continua:** Cada gráfico fijado guarda la consulta DuckDB subyacente. Cuando el canal **SSE (`/api/stream`)** recibe nuevos eventos sísmicos en vivo, DuckDB re-evalúa la consulta y el gráfico en el Dashboard se actualiza automáticamente con los datos más recientes.
- **Persistencia en Navegador:** La configuración de gráficos fijados se guarda en `localStorage`, permaneciendo disponible al recargar la sesión.
