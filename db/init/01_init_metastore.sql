-- ==============================================================================
-- SISMOWATCH METASTORE & ROLES DE MÍNIMO PRIVILEGIO (PostgreSQL 16)
-- ==============================================================================

-- 1. Creación de Esquemas
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS curated;

-- 2. Creación de Roles de Mínimo Privilegio (si no existen)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'user_ingestion') THEN
        CREATE ROLE user_ingestion WITH LOGIN PASSWORD 'ingestion_least_privilege_2026!';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'user_transform') THEN
        CREATE ROLE user_transform WITH LOGIN PASSWORD 'transform_least_privilege_2026!';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'user_platform') THEN
        CREATE ROLE user_platform WITH LOGIN PASSWORD 'platform_readonly_privilege_2026!';
    END IF;
END $$;

-- 3. Tablas del Schema RAW
CREATE TABLE IF NOT EXISTS raw.earthquake_events_raw (
    id VARCHAR(64) PRIMARY KEY,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload JSONB NOT NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'usgs_realtime'
);

-- 4. Tablas del Schema STAGING
CREATE TABLE IF NOT EXISTS staging.earthquake_events_staging (
    id VARCHAR(64) PRIMARY KEY,
    mag NUMERIC(4,2),
    place TEXT,
    time TIMESTAMPTZ NOT NULL,
    updated TIMESTAMPTZ,
    longitude NUMERIC(9,6) NOT NULL,
    latitude NUMERIC(9,6) NOT NULL,
    depth_km NUMERIC(7,2) NOT NULL,
    tsunami SMALLINT DEFAULT 0,
    sig INTEGER DEFAULT 0,
    status VARCHAR(32) DEFAULT 'automatic',
    mag_type VARCHAR(16) DEFAULT 'ml',
    processing_status VARCHAR(20) DEFAULT 'PENDING' CHECK (processing_status IN ('PENDING', 'VALID', 'INVALID', 'CORRECTED')),
    validation_error TEXT,
    failed_rules JSONB,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Tablas del Schema CURATED
CREATE TABLE IF NOT EXISTS curated.earthquake_events (
    id VARCHAR(64) PRIMARY KEY,
    mag NUMERIC(4,2) NOT NULL,
    place TEXT,
    time TIMESTAMPTZ NOT NULL,
    updated TIMESTAMPTZ,
    longitude NUMERIC(9,6) NOT NULL,
    latitude NUMERIC(9,6) NOT NULL,
    depth_km NUMERIC(7,2) NOT NULL,
    tsunami SMALLINT DEFAULT 0,
    sig INTEGER DEFAULT 0,
    status VARCHAR(32) DEFAULT 'reviewed',
    mag_type VARCHAR(16) DEFAULT 'ml',
    processing_status VARCHAR(20) DEFAULT 'VALID' CHECK (processing_status IN ('VALID', 'CORRECTED')),
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_curated_time ON curated.earthquake_events(time DESC);
CREATE INDEX IF NOT EXISTS idx_curated_mag ON curated.earthquake_events(mag);
CREATE INDEX IF NOT EXISTS idx_curated_coords ON curated.earthquake_events(latitude, longitude);

-- Métricas de Calidad por Ejecución
CREATE TABLE IF NOT EXISTS curated.quality_metrics (
    id SERIAL PRIMARY KEY,
    dag_id VARCHAR(64) NOT NULL,
    run_id VARCHAR(128) NOT NULL,
    execution_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_records INT NOT NULL DEFAULT 0,
    valid_records INT NOT NULL DEFAULT 0,
    invalid_records INT NOT NULL DEFAULT 0,
    quality_score NUMERIC(5,2) NOT NULL DEFAULT 100.00,
    rules_summary JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alertas Analíticas de Anomalías (IsolationForest / Z-score)
CREATE TABLE IF NOT EXISTS curated.anomaly_alerts (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(64) REFERENCES curated.earthquake_events(id) ON DELETE CASCADE,
    anomaly_score NUMERIC(6,3),
    anomaly_type VARCHAR(64) NOT NULL,
    explanation TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Reportes Ejecutivos Diarios de IA
CREATE TABLE IF NOT EXISTS curated.ai_reports (
    id SERIAL PRIMARY KEY,
    report_date DATE UNIQUE NOT NULL,
    title TEXT NOT NULL,
    executive_summary TEXT NOT NULL,
    active_zones JSONB,
    highlighted_events JSONB,
    calculated_metrics JSONB NOT NULL,
    ai_verified BOOLEAN NOT NULL DEFAULT TRUE,
    prompt_version VARCHAR(32) DEFAULT 'v1.0',
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Logs de Ejecución de IA (Tokens, Latencia, Costos)
CREATE TABLE IF NOT EXISTS curated.ai_execution_logs (
    id SERIAL PRIMARY KEY,
    report_id INT REFERENCES curated.ai_reports(id) ON DELETE SET NULL,
    model VARCHAR(64) NOT NULL,
    prompt_name VARCHAR(64) NOT NULL,
    prompt_version VARCHAR(32) DEFAULT 'v1.0',
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    total_tokens INT DEFAULT 0,
    latency_ms INT DEFAULT 0,
    cost_usd NUMERIC(8,6) DEFAULT 0.000000,
    status VARCHAR(32) NOT NULL DEFAULT 'SUCCESS',
    error_message TEXT,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Usuarios de la Plataforma para Autenticación RBAC
CREATE TABLE IF NOT EXISTS curated.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL CHECK (role IN ('viewer', 'admin')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Siembra de Usuarios Iniciales (Admin y Viewer)
INSERT INTO curated.users (username, password_hash, role)
VALUES 
    ('admin', '$2b$12$LQodgwkg8/ZOURcvHYT7AeiBbi4huFlLQO5iHKPqTX2HwaH7QVxoq', 'admin'),
    ('viewer', '$2b$12$uvif7VJKdQMphzI.4oL9HOtLVW483BzN2dluPFG4.LiZiwDYjZ/ye', 'viewer')
ON CONFLICT (username) DO UPDATE 
SET password_hash = EXCLUDED.password_hash, role = EXCLUDED.role;

-- 7. Asignación de Permisos de Mínimo Privilegio

-- user_ingestion: solo INSERT sobre raw
GRANT USAGE ON SCHEMA raw TO user_ingestion;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA raw TO user_ingestion;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT, INSERT ON TABLES TO user_ingestion;

-- user_transform: lee raw, escribe en staging y curated
GRANT USAGE ON SCHEMA raw, staging, curated TO user_transform;
GRANT SELECT ON ALL TABLES IN SCHEMA raw TO user_transform;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA staging, curated TO user_transform;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA curated TO user_transform;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO user_transform;
ALTER DEFAULT PRIVILEGES IN SCHEMA curated GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO user_transform;

-- user_platform: SELECT exclusivo sobre curated
REVOKE ALL ON SCHEMA raw, staging FROM user_platform;
GRANT USAGE ON SCHEMA curated TO user_platform;
GRANT SELECT ON ALL TABLES IN SCHEMA curated TO user_platform;
ALTER DEFAULT PRIVILEGES IN SCHEMA curated GRANT SELECT ON TABLES TO user_platform;
