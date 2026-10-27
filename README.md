# 🌍 SismoWatch: Plataforma de Monitoreo Sísmico Global en Tiempo Real

> **Arquitectura Data Lakehouse Moderna: Apache Spark (PySpark), Almacenamiento Columnar Parquet en Capa Gold, Motor Vectorizado DuckDB, Apache Airflow, Inteligencia Artificial Local (Qwen 2.5:2b con Ollama) y Frontend React + Vite.**

---

## 📋 Tabla de Contenidos
1. [Propósito del Negocio y Arquitectura Lakehouse](#-propósito-del-negocio-y-arquitectura-lakehouse)
2. [El Poder de Spark + Parquet + DuckDB](#-el-poder-de-spark--parquet--duckdb)
3. [Puesta en Marcha (Un solo comando)](#-puesta-en-marcha-un-solo-comando)
4. [Estrategia de Calidad de Datos y Alertas](#-estrategia-de-calidad-de-datos-y-alertas)
5. [Seguridad y Mínimo Privilegio](#-seguridad-y-mínimo-privilegio)
6. [Inteligencia Artificial y Chatbot DuckDB](#-inteligencia-artificial-y-chatbot-duckdb)
7. [Transmisión en Tiempo Real (SSE)](#-transmisión-en-tiempo-real-sse)
8. [Diseño Frontend Profesional](#-diseño-frontend-profesional)
9. [Suite de Pruebas Automatizadas](#-suite-de-pruebas-automatizadas)
10. [Preguntas Guía para la Sustentación](#-preguntas-guía-para-la-sustentación)

---

## 🎯 Propósito del Negocio y Arquitectura Lakehouse

SuperApp requiere monitorear la sismicidad global para priorizar decisiones de riesgo y contingencia operativa en sus redes de transporte, distribución y logística.
**SismoWatch** toma el feed público de la **USGS (United States Geological Survey)** y lo transforma mediante una arquitectura **Data Lakehouse** de alto rendimiento:

```
[ USGS Feed API ]
       │
       ▼ (Cada 5 min / Micro-lote con try-catch)
[ Apache Airflow Ingestion DAG ]
       │
       ▼ (JSONB / GeoJSON crudo)
[ Landing Layer: data/raw/ ]
       │
       ▼ (PySpark Transformation Job)
[ Apache Spark: Limpieza, tipado y validación de calidad ]
       │
       ├─► (Si hay registros inválidos) ──► [ Alerta Inmediata en Airflow ]
       ▼ (Escritura columnar particionada por fecha)
[ Gold Layer: data/gold/earthquake_events/ (Archivos Parquet) ]
       │
       ▼ (Lectura directa vectorizada sin bloqueos con read_parquet)
[ Motor Analítico DuckDB (FastAPI) ] ◄──► [ Chatbot Qwen 2.5:2b (Ollama) ]
       │                                  (Text-to-SQL ejecutado sobre Parquet)
       ▼ (REST API + Server-Sent Events)
[ Frontend React + Vite (MetricRibbon + Leaflet + Recharts + Chatbot) ]
```

*Detalles ampliados de diseño y justificación técnica en:* [docs/ARQUITECTURA.md](file:///home/cohorte5/Documentos/dypok/prueba2IA/docs/ARQUITECTURA.md).

---

## ⚡ El Poder de Spark + Parquet + DuckDB

1. **Apache Spark en la Transformación:** Procesa y aplana los payloads GeoJSON masivos de USGS, aplica reglas de calidad y genera archivos **Apache Parquet** comprimidos con Snappy, particionados por año y mes (`year=YYYY/month=MM/`).
2. **Gold Layer en Parquet:** Formato columnar óptimo que almacena metadatos y estadísticas de columnas (mínimos, máximos) y reduce el espacio en disco en más de un 80%.
3. **DuckDB como Motor Analítico y de Chatbot:** 
   - El backend de FastAPI instancia DuckDB en memoria.
   - DuckDB monta una vista sobre los Parquets:
     ```sql
     CREATE VIEW earthquake_events AS SELECT * FROM read_parquet('data/gold/earthquake_events/**/*.parquet');
     ```
   - Al ser consultas de lectura sobre archivos Parquet, **no existe riesgo de bloqueos por concurrencia** (*database lock*).
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
| **Airflow Webserver** | [http://localhost:8080](http://localhost:8080) | `admin` / `admin_sismowatch_airflow_2026!` |
| **Inferencia Ollama** | [http://localhost:11434](http://localhost:11434) | Modelo: `qwen2.5:2b` |

---

## 🛡️ Estrategia de Calidad de Datos y Alertas

- **Reglas de Pandera:** Coordenadas latitud $[-90, 90]$, longitud $[-180, 180]$, magnitud $[-2.0, 10.0]$, profundidad $[-10.0, 1000.0]$ km.
- **Máquina de Estados:** `PENDING`, `VALID`, `INVALID`, `CORRECTED`.
- **Alerta Inmediata en Airflow:** Si un registro no cumple las especificaciones, la tarea `notify_invalid_records` emite una alerta destacada en los logs y en la interfaz de Airflow para advertir al operador.
- **Resiliencia:** Bloques `try/catch` integrales protegen el flujo para que los datos válidos sigan procesándose hacia los Parquet de la capa Gold sin caídas del sistema.

---

## 🤖 Inteligencia Artificial y Chatbot DuckDB

- **Chatbot con Qwen 2.5:2b (Ollama):** 
  - El usuario consulta en español: *"¿Cuáles fueron los 3 sismos más fuertes hoy?"*.
  - El LLM genera la consulta SQL de solo lectura para DuckDB:
    ```sql
    SELECT place, mag, time, depth_km FROM earthquake_events ORDER BY mag DESC LIMIT 3;
    ```
  - DuckDB lee los Parquet y ejecuta la consulta instantáneamente.
  - El chatbot redacta la respuesta en lenguaje natural y muestra la consulta ejecutada en la interfaz.

---

## 🎨 Diseño Frontend Profesional

- **Cero Badges:** Se eliminaron las etiquetas tipo píldora de colores; se usan indicadores tipográficos limpios y puntos discretos de estado (`status dots`).
- **Cero Exceso de Cards:** Barra unificada de métricas (`MetricRibbon`) y paneles continuos con diseño profesional (estilo Datadog / Stripe).
- **Mapa Leaflet y Gráficos:** Visualización geoespacial interactiva y series temporales alimentadas directamente por DuckDB.
