# 🌍 SismoWatch: Plataforma de Monitoreo Sísmico Global en Tiempo Real

> **Arquitectura Data Lakehouse Moderna: MinIO (S3 Object Storage), Apache Spark (PySpark), Arquitectura Medallion (Bronze ➔ Silver ➔ Gold), Motor Vectorizado DuckDB, Apache Airflow, Inteligencia Artificial Local (Qwen 2.5:2b con Ollama) y Frontend React + Vite.**

---

## 📋 Tabla de Contenidos
1. [Flujo de Datos Medallion (Bronze ➔ Silver ➔ Gold)](#-flujo-de-datos-medallion-bronze--silver--gold)
2. [Arquitectura General Lakehouse](#-arquitectura-general-lakehouse)
3. [El Rol de MinIO + Spark + DuckDB](#-el-rol-de-minio--spark--duckdb)
4. [Puesta en Marcha (Un solo comando)](#-puesta-en-marcha-un-solo-comando)
5. [Estrategia de Calidad de Datos y Alertas](#-estrategia-de-calidad-de-datos-y-alertas)
6. [Seguridad y Mínimo Privilegio](#-seguridad-y-mínimo-privilegio)
7. [Inteligencia Artificial y Chatbot DuckDB](#-inteligencia-artificial-y-chatbot-duckdb)
8. [Transmisión en Tiempo Real (SSE)](#-transmisión-en-tiempo-real-sse)
9. [Diseño Frontend Profesional](#-diseño-frontend-profesional)
10. [Preguntas Guía para la Sustentación](#-preguntas-guía-para-la-sustentación)

---

## 🏅 Flujo de Datos Medallion (Bronze ➔ Silver ➔ Gold)

```mermaid
flowchart LR
    USGS["API USGS"] -->|Ingesta cruda| Bronze["BRONZE (MinIO S3)<br/>GeoJSON inmutable"]
    Bronze -->|Apache Spark: Desanidar + Tipar| Silver["SILVER (MinIO Parquet)<br/>VALID + INVALID con motivos"]
    
    Silver -.->|Si hay INVALID| AlertaAirflow["⚠️ Alerta Inmediata<br/>en Airflow"]
    Silver -->|Filtro: solo VALID + Enriquecimiento| Gold["GOLD (MinIO Parquet)<br/>Datos certificados + Agregaciones"]
    
    Gold -->|read_parquet() con httpfs| DuckDB["DuckDB Engine<br/>(FastAPI)"]
    DuckDB --> Chatbot["Chatbot Qwen 2.5:2b<br/>& Dashboard Web"]
```

### Detalle de las 3 Capas en MinIO (`sismowatch-lake`)

| Capa | Ruta en MinIO S3 | Formato | Contenido y Función |
| :--- | :--- | :--- | :--- |
| **BRONZE** | `s3://sismowatch-lake/bronze/` | `.geojson` / `.json` | Payload GeoJSON crudo e inmutable tal como llega de la API de USGS. |
| **SILVER** | `s3://sismowatch-lake/silver/earthquake_events/` | `.snappy.parquet` | Datos desanidados y tipados por Apache Spark. Contiene todos los eventos con `processing_status` (`VALID` o `INVALID` con `validation_error`). Si hay fallos, dispara la alerta inmediata en Airflow para auditoría. |
| **GOLD** | `s3://sismowatch-lake/gold/earthquake_events/` | `.snappy.parquet` | Datos analíticos certificados. Contiene **únicamente registros con estado `VALID`**, enriquecidos y listos para ser consumidos por **DuckDB** para el dashboard y el Chatbot. |

---

## 🎯 Arquitectura General Lakehouse

```
[ USGS Feed API ]
       │
       ▼ (Cada 5 min / Micro-lote con try-catch)
[ Apache Airflow Ingestion DAG ]
       │
       ▼ (Escribe GeoJSON inmutable vía S3)
[ MinIO: sismowatch-lake/bronze/ ]
       │
       ▼ (PySpark Transformation Job)
[ MinIO: sismowatch-lake/silver/ (Parquet: VALID + INVALID) ]
       │
       ├─► (Si hay registros INVALID) ──► [ Alerta Inmediata en Airflow ]
       ▼ (Filtro: solo registros certificados VALID)
[ MinIO: sismowatch-lake/gold/ (Parquet certificado) ]
       │
       ▼ (Lectura directa vectorizada sin bloqueos vía httpfs)
[ Motor Analítico DuckDB (FastAPI) ] ◄──► [ Chatbot Qwen 2.5:2b (Ollama) ]
       │                                  (Text-to-SQL ejecutado sobre Parquet)
       ▼ (REST API + Server-Sent Events)
[ Frontend React + Vite (MetricRibbon + Leaflet + Recharts + Chatbot) ]
```

*Detalles ampliados de diseño y justificación técnica en:* [docs/ARQUITECTURA.md](file:///home/cohorte5/Documentos/dypok/prueba2IA/docs/ARQUITECTURA.md).

---

## ⚡ El Rol de MinIO + Spark + DuckDB

1. **MinIO (S3 Object Storage):** Almacenamiento centralizado compatible con Amazon S3. Administra el bucket `sismowatch-lake` separando `bronze/`, `silver/` y `gold/`. Consola web en puerto `9001`.
2. **Apache Spark en la Transformación:** Lee de Bronze, aísla y aplana los payloads GeoJSON masivos de USGS, aplica reglas de calidad con Pandera y genera archivos **Apache Parquet** comprimidos con Snappy en Silver y Gold.
3. **DuckDB como Motor Analítico y de Chatbot:** 
   - El backend de FastAPI utiliza DuckDB con la extensión `httpfs` conectada a MinIO (`http://minio:9000`).
   - DuckDB monta la vista sobre los Parquets de la capa Gold:
     ```sql
     CREATE VIEW earthquake_events AS 
     SELECT * FROM read_parquet('s3://sismowatch-lake/gold/earthquake_events/**/*.parquet');
     ```
   - **Cero bloqueos de concurrencia** (*database lock*).
   - El **Chatbot (Qwen 2.5:2b)** traduce las preguntas en español a consultas DuckDB SQL que se ejecutan en menos de 5 milisegundos.

---

## 🚀 Puesta en Marcha (Un solo comando)

```bash
cp .env.example .env
docker compose up -d
```

### Servicios Disponibles

| Servicio | URL Local | Credenciales por Defecto |
| :--- | :--- | :--- |
| **Plataforma Web** | [http://localhost:3000](http://localhost:3000) | `admin` / `AdminSismoWatch2026!`<br/>`viewer` / `ViewerSismoWatch2026!` |
| **Documentación API (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) | Autenticación JWT en `/auth/login` |
| **Consola MinIO (S3 Lake)** | [http://localhost:9001](http://localhost:9001) | `minioadmin` / `minioadmin2026!` |
| **Airflow Webserver** | [http://localhost:8080](http://localhost:8080) | `admin` / `admin_sismowatch_airflow_2026!` |
| **Inferencia Ollama** | [http://localhost:11434](http://localhost:11434) | Modelo: `qwen2.5:2b` |

---

## 🎨 Diseño Frontend Profesional

- **Cero Badges:** Se eliminaron las etiquetas tipo píldora de colores; se usan indicadores tipográficos limpios y puntos discretos de estado (`status dots`).
- **Cero Exceso de Cards:** Barra unificada de métricas (`MetricRibbon`) y paneles continuos con diseño profesional (estilo Datadog / Stripe).
- **Mapa Leaflet y Gráficos:** Visualización geoespacial interactiva y series temporales alimentadas directamente por DuckDB.
