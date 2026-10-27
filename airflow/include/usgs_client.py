import os
import time
import logging
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)

DEFAULT_REALTIME_URL = os.getenv(
    "USGS_REALTIME_URL",
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson",
)
DEFAULT_QUERY_URL = os.getenv(
    "USGS_QUERY_URL",
    "https://earthquake.usgs.gov/fdsnws/event/1/query",
)
TIMEOUT_SECONDS = int(os.getenv("HTTP_TIMEOUT_SECONDS", "10"))


def fetch_usgs_realtime(
    url: str = DEFAULT_REALTIME_URL,
    max_retries: int = 3,
    backoff_factor: float = 1.5,
) -> Optional[Dict[str, Any]]:
    """
    Obtiene el feed GeoJSON de sismos de la última hora desde la API de USGS.
    Implementa reintentos con espera exponencial y captura integral de excepciones.
    """
    headers = {"User-Agent": "SismoWatch-DataPlatform/1.0 (SuperApp RiskOps)"}
    attempt = 0

    while attempt < max_retries:
        attempt += 1
        try:
            logger.info(f"Consultando feed USGS en tiempo real (intento {attempt}/{max_retries}): {url}")
            response = requests.get(url, headers=headers, timeout=TIMEOUT_SECONDS)
            
            if response.status_code == 200:
                payload = response.json()
                features_count = len(payload.get("features", []))
                logger.info(f"Feed USGS obtenido exitosamente: {features_count} sismos registrados.")
                return payload
            
            logger.warning(
                f"Respuesta no satisfactoria de USGS (HTTP {response.status_code}): {response.text[:200]}"
            )
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout de conexión ({TIMEOUT_SECONDS}s) al consultar USGS en intento {attempt}.")
        except requests.exceptions.RequestException as req_err:
            logger.warning(f"Error de red o conexión HTTP en intento {attempt}: {req_err}")
        except Exception as e:
            logger.error(f"Error inesperado al parsear respuesta de USGS: {e}", exc_info=True)
            return None

        if attempt < max_retries:
            sleep_time = backoff_factor ** attempt
            logger.info(f"Esperando {sleep_time:.2f}s antes del siguiente reintento...")
            time.sleep(sleep_time)

    logger.error(f"Fallaron todos los {max_retries} intentos de consulta al feed de USGS.")
    return None


def fetch_usgs_query(
    start_time: str,
    end_time: str,
    min_magnitude: float = 2.5,
    query_url: str = DEFAULT_QUERY_URL,
    max_retries: int = 3,
) -> Optional[Dict[str, Any]]:
    """
    Consulta el endpoint histórico de USGS por rango de fechas y magnitud mínima.
    """
    params = {
        "format": "geojson",
        "starttime": start_time,
        "endtime": end_time,
        "minmagnitude": min_magnitude,
    }
    headers = {"User-Agent": "SismoWatch-DataPlatform/1.0 (SuperApp RiskOps)"}
    attempt = 0

    while attempt < max_retries:
        attempt += 1
        try:
            logger.info(f"Ejecutando consulta histórica USGS ({start_time} a {end_time}, minMag={min_magnitude})")
            response = requests.get(query_url, params=params, headers=headers, timeout=20)
            
            if response.status_code == 200:
                payload = response.json()
                count = len(payload.get("features", []))
                logger.info(f"Consulta histórica USGS exitosa: {count} eventos recuperados.")
                return payload
            
            logger.warning(f"Respuesta inesperada en query histórico (HTTP {response.status_code})")
        except Exception as e:
            logger.warning(f"Error en consulta histórica (intento {attempt}): {e}")

        time.sleep(1.5 * attempt)

    logger.error("No se pudo completar la consulta histórica de USGS tras reintentos.")
    return None
