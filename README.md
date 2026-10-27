# 🌍 SismoWatch: Plataforma de Monitoreo Sísmico Global en Tiempo Real

> **Solución Integral de Ingeniería de Datos, Automatización con Apache Airflow, Apache Spark, Calidad con Pandera, Seguridad Multicapa e Inteligencia Artificial Local (Qwen 2.5:2b).**

---

## 📋 Tabla de Contenidos
1. [Propósito del Negocio y Arquitectura](#-propósito-del-negocio-y-arquitectura)
2. [Puesta en Marcha (Un solo comando)](#-puesta-en-marcha-un-solo-comando)
3. [Estrategia de Calidad de Datos y Alertas](#-estrategia-de-calidad-de-datos-y-alertas)
4. [Seguridad y Mínimo Privilegio](#-seguridad-y-mínimo-privilegio)
5. [Inteligencia Artificial y Chatbot Local](#-inteligencia-artificial-y-chatbot-local)
6. [Transmisión en Tiempo Real (SSE)](#-transmisión-en-tiempo-real-sse)
7. [Diseño Frontend Profesional](#-diseño-frontend-profesional)
8. [Suite de Pruebas Automatizadas](#-suite-de-pruebas-automatizadas)
9. [Preguntas Guía para la Sustentación](#-preguntas-guía-para-la-sustentación)
10. [Limitaciones Conocidas y Mejoras Futuras](#-limitaciones-conocidas-y-mejoras-futuras)

---

## 🎯 Propósito del Negocio y Arquitectura

SuperApp requiere monitorear la sismicidad global para priorizar decisiones de riesgo y contingencia operativa en sus redes de transporte, distribución y logística.
**SismoWatch** toma el feed público de la **USGS (United States Geological Survey)** y lo transforma en un producto de datos empresarial mediante una arquitectura Medallion desacoplada:

```
[ USGS Feed API ]
       │
       ▼ (Cada 5 min / Micro-lote con try-catch)
[ Apache Airflow Ingestion DAG ]
       │
       ▼ (JSONB inmutable)
[ PostgreSQL: Schema RAW ]
       │
       ▼ (PySpark Transformation Job)
[ PostgreSQL: Schema STAGING ]
       │
       ├─► [ Pandera Quality Engine ] ──(Si hay INVALID)──► [ Alerta Inmediata en Airflow ]
       ▼ (Registros con estado VALID)
[ PostgreSQL: Schema CURATED ] ◄──► [ Detección de Anomalías: IsolationForest & Z-score ]
       │
       ├─► [ Airflow AI Reporter (Qwen 2.5:2b) ] ──► [ curated.ai_reports ]
       │
       ▼ (Lectura exclusiva con user_platform)
[ FastAPI Backend (RBAC JWT + SSE) ] ◄──► [ Ollama Local Ingestion: Qwen 2.5:2b ]
       │
       ▼ (HTTP REST + Server-Sent Events)
[ Frontend React + TypeScript + Vite (MetricRibbon + Leaflet + Recharts + Chatbot) ]
```

*Detalles ampliados de diseño y justificación de herramientas en:* [docs/ARQUITECTURA.md](file:///home/cohorte5/Documentos/dypok/prueba2IA/docs/ARQUITECTURA.md).

---

## 🚀 Puesta en Marcha (Un solo comando)

### 1. Requisitos Previos
- Docker y Docker Compose instalados.
- Puertos libres en el host: `8080` (Airflow), `8000` (API), `3000` (Web), `5432` o `5435` (PostgreSQL), `11434` (Ollama).

### 2. Configuración de Entorno
Clona o ingresa al directorio del repositorio y copia el archivo de variables de entorno:
```bash
cp .env.example .env
```
*(No es necesario editar nada para el entorno local; los valores por defecto están completamente sincronizados con los servicios de Docker).*

### 3. Levantar Todo el Ecosistema
Ejecuta el siguiente comando:
```bash
docker compose up -d
```

### 4. Servicios y Accesos

| Servicio | URL Local | Credenciales por Defecto |
| :--- | :--- | :--- |
| **Plataforma Web** | [http://localhost:3000](http://localhost:3000) | `admin` / `AdminSismoWatch2026!`<br/>`viewer` / `ViewerSismoWatch2026!` |
| **Documentación API (Swagger)** | [http://localhost:8000/docs](http://localhost:8000/docs) | Autenticación vía `/auth/login` |
| **Airflow Webserver** | [http://localhost:8080](http://localhost:8080) | `admin` / `admin_sismowatch_airflow_2026!` |
| **Inferencia Ollama** | [http://localhost:11434](http://localhost:11434) | Modelo: `qwen2.5:2b` |

---

## 🛡️ Estrategia de Calidad de Datos y Alertas

### Reglas de Calidad (Pandera)
- **Coordenadas Geográficas:** Latitud $[-90, 90]$, Longitud $[-180, 180]$.
- **Magnitud:** Rango sismológico plausible $[-2.0, 10.0]$.
- **Profundidad:** Rango geológico plausible $[-10.0, 1000.0]$ km.
- **Unicidad e Identidad:** Identificador de evento único y marcas temporales coherentes.

### Máquina de Estados y Alertas Inmediatas en Airflow
En lugar de una tabla de cuarentena que aísle el dato en silos, implementamos una **Máquina de Estados de Datos**:
- Todo registro recibe un estado: `PENDING`, `VALID`, `INVALID` o `CORRECTED`.
- Si un registro incumple alguna regla, es etiquetado como `INVALID` guardando el motivo exacto en `validation_error`.
- **Alerta Inmediata en Airflow:** La tarea `notify_invalid_records` en el DAG de calidad detecta la presencia de registros no conformes y genera un aviso crítico en los logs y la interfaz de Airflow para que el operador de guardia intervenga y corrija el dato inmediatamente.
- **Protección Total del Flujo (`try/catch`):** Los registros sanos con estado `VALID` continúan sin tropiezos hacia `curated.earthquake_events`.

---

## 🔒 Seguridad y Mínimo Privilegio

1. **Gestión de Secretos:** Archivo `.env` estrictamente ignorado en git. Claves Fernet y JWT autogeneradas.
2. **Roles de Mínimo Privilegio en PostgreSQL:**
   - `user_ingestion`: Solo puede insertar en `raw.earthquake_events_raw`.
   - `user_transform`: Lee `raw`, escribe en `staging` y `curated`.
   - `user_platform`: Permiso exclusivo de solo lectura (`SELECT`) en `curated` (usado por la API pública).
3. **Control de Acceso Basado en Roles (RBAC):**
   - **Viewer:** Visualiza dashboard, mapa interactivo, gráficos, stream en vivo y reportes.
   - **Admin:** Todos los permisos de Viewer + visualización de registros inválidos (`/api/quality/quarantine`), disparo de backfill histórico (`POST /api/admin/backfill`) y regeneración de reportes de IA.
   - **Llamadas sin Token:** Rechazo estricto con código HTTP `401 Unauthorized`.
   - **Viewer intentando acción Admin:** Rechazo estricto con código HTTP `403 Forbidden`.
4. **Protección contra Inyección de Prompt (OWASP LLM01):**
   - Sanitización del campo `place` antes de interactuar con el LLM.
   - Validación restrictiva de consultas SQL generadas por el Chatbot (solo `SELECT` en schema `curated`).

*Auditoría completa en:* [docs/SECURITY.md](file:///home/cohorte5/Documentos/dypok/prueba2IA/docs/SECURITY.md).

---

## 🤖 Inteligencia Artificial y Chatbot Local

### 1. Chatbot Conversacional Text-to-SQL con Qwen 2.5:2b
- Corre localmente sobre **Ollama** en CPU (aprovechando los 12 núcleos del servidor sin costos de API ni filtración de datos).
- Permite a cualquier usuario consultar información sísmica en español natural.
- El backend transforma la pregunta en una consulta SQL segura de solo lectura, extrae los datos y entrega una síntesis ejecutiva.

### 2. Reporte Narrativo Diario Verificado
- **Cero Alucinaciones:** Todas las cifras estadísticas (máxima, promedio, sismos por hora, alertas de tsunami) son calculadas por código Python/SQL. El LLM únicamente redacta la narrativa.
- **Verificación Automática:** Un algoritmo validador escanea el texto generado para garantizar que los números coincidan con las cifras calculadas.
- **Motor de Fallback:** Si Ollama está ocupado o se apaga, un motor determinista genera el reporte automáticamente sin romper el DAG.

---

## 📡 Transmisión en Tiempo Real (SSE)

- Implementado mediante **Server-Sent Events (SSE)** en la ruta `GET /api/stream`.
- **¿Por qué SSE y no WebSockets o Polling?**
  - La comunicación es puramente unidireccional (del servidor hacia el cliente).
  - SSE utiliza HTTP estándar, reconecta de manera transparente si la red fluctúa, y consume una fracción de los recursos de CPU que demandaría un polling repetitivo.
- La interfaz muestra un indicador pulsante en vivo y la marca de tiempo exacta de la última actualización.

---

## 🎨 Diseño Frontend Profesional

Alineado con las directrices de diseño corporativo:
- **Cero Badges:** No se utilizan chips de colores ni etiquetas tipo píldora que saturen la vista. Se emplean indicadores tipográficos limpios y puntos sutiles de estado (`status dots`).
- **Cero Exceso de Cards:** Las tarjetas individuales flotantes fueron reemplazadas por una **Barra Unificada de Métricas (`MetricRibbon`)**, permitiendo una lectura panorámica continua de los KPIs principales.
- **Integración Fluida:** Mapa Leaflet a gran escala, gráficos compactos de Recharts y un drawer lateral deslizable para el Chatbot SismoWatch AI.

---

## 🧪 Suite de Pruebas Automatizadas

La solución incluye pruebas unitarias y de integración completas ejecutables con `pytest`:

```bash
# Ejecutar todas las pruebas
pytest -v
```

Pruebas incluidas:
1. `test_transforms.py`: Validación de la función de transformación de GeoJSON a esquema tabular (PySpark).
2. `test_dag_integrity.py`: Verificación de sintaxis, importación y estructura acíclica de todos los DAGs de Airflow.
3. `test_quality_rules.py`: Evaluación de reglas Pandera (casos conformes `VALID` y no conformes `INVALID`).
4. `test_api_rbac.py`: Pruebas de seguridad HTTP (401 sin credenciales, 403 a Viewer en endpoints de Admin, 200 a Admin).

---

## 🎤 Preguntas Guía para la Sustentación

Para defender tu solución ante el Tech Lead (TL), ten en cuenta estas respuestas basadas en tu implementación:

- **¿Cuál es el propósito de tu arquitectura, a quién sirve y qué decisiones permite tomar?**
  *Resuelve la falta de persistencia, calidad y síntesis del feed de USGS. Sirve a las áreas de Operaciones y Gestión de Riesgo de SuperApp para tomar decisiones preventivas ante sismos severos ($\ge 6.0$), alertas de tsunami o enjambres sísmicos.*
- **¿Por qué usaste Airflow y no un cron o un script?**
  *Airflow provee orquestación basada en DAGs con linaje, reintentos exponenciales automáticos, observabilidad en tiempo real, backfill histórico parametrizado e idempotencia, capacidades inexistentes en un cron plano.*
- **¿Cómo garantizas que ejecutar dos veces el mismo intervalo no duplica datos?**
  *Mediante operaciones de upsert idempotentes (`ON CONFLICT (id) DO UPDATE ...`) tanto en la capa `raw` como en `curated`, ancladas al ID único que asigna USGS a cada sismo.*
- **¿Qué ocurre si la API de USGS no responde o devuelve datos incompletos?**
  *Las peticiones HTTP están protegidas con timeouts estrictos y reintentos en bloques `try/catch`. Si el servicio está caído, el DAG finaliza de forma controlada sin tumbar los servicios ni corromper las capas de datos.*
- **¿Qué pasa con un registro que no pasa las reglas de calidad? ¿Dónde queda y cómo se ve?**
  *No se descarta a ciegas ni se usa una tabla redundante: se le asigna el estado `processing_status = 'INVALID'` en la capa de datos, se graba el motivo en `validation_error` y se detona de inmediato una alerta en Airflow para advertir al operador y permitir su corrección rápida.*
- **¿Dónde están tus secretos y cómo evitas que lleguen al repositorio?**
  *En variables de entorno inyectadas desde el archivo `.env`, el cual está estrictamente excluido en el `.gitignore`. Solo se versiona `.env.example` con valores de muestra.*
- **¿Qué permisos tiene cada rol de base de datos y por qué?**
  *Mínimo privilegio: `user_ingestion` solo hace INSERT en `raw`; `user_transform` lee `raw` y escribe en `staging`/`curated`; `user_platform` solo puede hacer SELECT sobre `curated`.*
- **¿Cómo evitas que el modelo de IA invente cifras?**
  *Las cifras matemáticas se calculan de forma determinista en Python/SQL. El modelo solo redacta, y un algoritmo validador posterior comprueba que las cifras del texto coincidan al 100% con los datos calculados antes de publicar el reporte.*
- **¿Cómo funciona el tiempo real en tu plataforma y qué pasa si se cae la conexión?**
  *Usa Server-Sent Events (SSE). Si la conexión de red se interrumpe, el cliente SSE de React se reconecta de forma automática mediante backoff exponencial sin recargar la página ni dejar la pantalla en blanco.*
- **¿Cómo impides que un usuario viewer ejecute acciones de admin?**
  *En el frontend se ocultan las interfaces restringidas, y en el backend FastAPI las rutas administrativas validan el claim `role == 'admin'` en el token JWT; si un viewer hace la llamada directa vía curl o Postman, recibe un código `403 Forbidden`.*

---

## 📈 Limitaciones Conocidas y Mejoras Futuras

1. **Ingesta de Streaming Puro:** En producción a gran escala, evolucionar de micro-lotes cada 5 min a un bus de eventos con **Apache Kafka** para latencias menores a 1 segundo.
2. **Lakehouse Object Storage:** Migrar las capas `raw` y `staging` a **MinIO / AWS S3** en formato columnar **Parquet / Iceberg** para abaratar costos de almacenamiento.
3. **Escalamiento con Kubernetes:** Desplegar Airflow con `KubernetesExecutor` para que cada tarea corra en pods aislados bajo demanda.
