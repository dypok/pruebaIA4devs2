# 🌍 SismoWatch: Plataforma de Monitoreo Sísmico Global en Tiempo Real

githublink https://github.com/dypok/pruebaIA4devs2.git

> **Arquitectura Data Lakehouse Moderna: MinIO (S3 Object Storage), Polars (Motor Vectorizado en Rust), Arquitectura Medallion (Bronze ➔ Silver ➔ Gold), Motor Vectorizado DuckDB, Apache Airflow, Inteligencia Artificial Local (Qwen 2.5:2b con Ollama) y Frontend React + Vite con Gráficos Dinámicos Fijables.**

---

## 📋 Tabla de Contenidos
1. [Flujo de Datos Medallion (Bronze ➔ Silver ➔ Gold)](#-flujo-de-datos-medallion-bronze--silver--gold)
2. [Arquitectura General Lakehouse](#-arquitectura-general-lakehouse)
3. [El Rol de MinIO + Polars + DuckDB](#-el-rol-de-minio--polars--duckdb)
4. [Chatbot IA y Gráficos Dinámicos Fijables al Dashboard](#-chatbot-ia-y-gráficos-dinámicos-fijables-al-dashboard)
5. [Puesta en Marcha (Un solo comando)](#-puesta-en-marcha-un-solo-comando)
6. [Estrategia de Calidad de Datos y Alertas](#-estrategia-de-calidad-de-datos-y-alertas)
7. [Seguridad y Mínimo Privilegio](#-seguridad-y-mínimo-privilegio)
8. [Transmisión en Tiempo Real (SSE)](#-transmisión-en-tiempo-real-sse)
9. [Diseño Frontend Profesional](#-diseño-frontend-profesional)
10. [Preguntas Guía para la Sustentación](#-preguntas-guía-para-la-sustentación)

---

## 🏅 Flujo de Datos Medallion (Bronze ➔ Silver ➔ Gold)

```mermaid
flowchart LR
    USGS["API USGS"] -->|Ingesta cruda| Bronze["BRONZE (MinIO S3)<br/>GeoJSON inmutable"]
    Bronze -->|Polars: Desanidar + Tipar| Silver["SILVER (MinIO Parquet)<br/>VALID + INVALID con motivos"]
    
    Silver -.->|Si hay INVALID| AlertaAirflow["⚠️ Alerta Inmediata<br/>en Airflow"]
    Silver -->|Filtro: solo VALID + Enriquecimiento| Gold["GOLD (MinIO Parquet)<br/>Datos certificados + Agregaciones"]
    
    Gold -->|read_parquet() con httpfs| DuckDB["DuckDB Engine<br/>(FastAPI)"]
    DuckDB --> Chatbot["Chatbot Qwen 2.5:2b<br/>(Text-to-SQL + Auto-Chart)"]
    Chatbot -->|📌 Fijar gráfico dinámico| Dashboard["Dashboard React en Vivo<br/>(Se actualiza con SSE)"]
```

---

## 📊 Chatbot IA y Gráficos Dinámicos Fijables al Dashboard

Una de las capacidades más innovadoras de SismoWatch es su integración analítica conversacional:
1. **Generación Automática de Gráficos (Auto-Chart):**
   - El usuario realiza una pregunta en lenguaje natural: *"¿Cómo se distribuyen los sismos por magnitud hoy?"* o *"¿Cuáles son las 5 zonas con más actividad?"*.
   - **Qwen 2.5:2b** genera la consulta SQL optimizada para DuckDB.
   - DuckDB ejecuta la consulta sobre los Parquet de MinIO.
   - El sistema infiere el tipo de gráfico ideal (barras, líneas, áreas o distribución) y dibuja el gráfico interactivo directamente en el chat.
2. **Fijar al Dashboard (Pin to Dashboard):**
   - Cada gráfico en el chat incluye el botón **`📌 Fijar al Dashboard`**.
   - Al presionarlo, el gráfico se añade a la sección de **"Visualizaciones Personalizadas"** del Dashboard principal.
3. **Actualización Reactiva en Tiempo Real:**
   - Los gráficos fijados no son capturas estáticas: preservan su definición de consulta.
   - Cuando llegan nuevos sismos en vivo mediante el canal **Server-Sent Events (SSE)**, DuckDB re-ejecuta la consulta y los gráficos se actualizan reactivamente sin recargar la página.
   - Las preferencias se guardan en `localStorage` persistiendo entre sesiones.

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
| **Airflow Webserver** | [http://localhost:8085](http://localhost:8085) | `admin` / `admin_sismowatch_airflow_2026!` |
| **Inferencia Ollama** | [http://localhost:11434](http://localhost:11434) | Modelo: `qwen2.5:2b` |

---

## 🎨 Diseño Frontend Profesional

- **Cero Badges:** Se eliminaron las etiquetas tipo píldora de colores; se usan indicadores tipográficos limpios y puntos discretos de estado (`status dots`).
- **Cero Exceso de Cards:** Barra unificada de métricas (`MetricRibbon`) y paneles continuos con diseño profesional (estilo Datadog / Stripe).
- **Dashboard Dinámico:** Mapa Leaflet, gráficos fijos y sección de gráficos analíticos interactivos fijados desde el Chatbot.
