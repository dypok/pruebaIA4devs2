import asyncio
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from auth import require_viewer
from duckdb_service import duckdb_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["Tiempo Real"])


async def event_generator(request: Request):
    """
    Generador asíncrono para Server-Sent Events (SSE).
    Envía periódicamente las últimas actualizaciones y pings de heartbeat cada 15 segundos.
    """
    client_host = request.client.host if request.client else "unknown"
    logger.info(f"Cliente SSE conectado desde {client_host}")

    try:
        # Enviar evento de conexión inicial
        initial_payload = {
            "type": "CONNECTION_ESTABLISHED",
            "connected_at": datetime.now(timezone.utc).isoformat(),
            "status": "LIVE",
        }
        yield f"data: {json.dumps(initial_payload)}\n\n"

        iteration = 0
        while True:
            # Comprobar si el cliente se desconectó
            if await request.is_disconnected():
                logger.info(f"Cliente SSE {client_host} desconectado.")
                break

            await asyncio.sleep(8)
            iteration += 1

            # Cada 8 segundos consultar sismos más recientes
            latest = duckdb_service.get_events(page=1, page_size=3)["events"]
            if latest:
                event_data = {
                    "type": "SEISMIC_UPDATE",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "latest_events": latest,
                }
                yield f"data: {json.dumps(event_data)}\n\n"

            # Heartbeat periódico
            if iteration % 2 == 0:
                yield f": ping - {datetime.now(timezone.utc).isoformat()}\n\n"

    except asyncio.CancelledError:
        logger.info(f"Stream SSE cancelado para {client_host}")
    except Exception as e:
        logger.error(f"Error en stream SSE: {e}", exc_info=True)


@router.get("/stream")
async def stream_live_events(request: Request, user: dict = Depends(require_viewer)):
    """
    Transmisión continua de sismos en tiempo casi real mediante Server-Sent Events (SSE).
    Soporta reconexión automática en el cliente y señales de pulso.
    """
    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
