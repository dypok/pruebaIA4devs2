from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import CORS_ORIGINS
from routes.auth_routes import router as auth_router
from routes.events_routes import router as events_router
from routes.reports_routes import router as reports_router
from routes.stream_routes import router as stream_router
from routes.pipeline_routes import router as pipeline_router
from routes.chat_routes import router as chat_router

app = FastAPI(
    title="SismoWatch API - SuperApp RiskOps",
    description="API empresarial de monitoreo sísmico global en tiempo casi real con DuckDB, IA y RBAC.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS if CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montaje de Rutas
app.include_router(auth_router)
app.include_router(events_router)
app.include_router(reports_router)
app.include_router(stream_router)
app.include_router(pipeline_router)
app.include_router(chat_router)


@app.get("/health", tags=["Salud"])
def health_check():
    """Endpoint de comprobación de estado de la API."""
    return {"status": "HEALTHY", "service": "SismoWatch-API", "version": "1.0.0"}
