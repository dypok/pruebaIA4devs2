import re
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def sanitize_text(text: Optional[str], max_length: int = 120) -> str:
    """
    Sanitiza campos de texto libre (como 'place') para mitigar riesgos de inyección de prompts
    y caracteres de control no deseados.
    """
    if not text:
        return "Unknown location"
    
    # 1. Truncar longitud
    cleaned = str(text)[:max_length].strip()
    
    # 2. Reemplazar delimitadores o etiquetas maliciosas
    cleaned = re.sub(r"[`<>{}\\\"\^~|]+", "", cleaned)
    
    # 3. Remover saltos de línea y tabuladores múltiples
    cleaned = re.sub(r"[\r\n\t]+", " ", cleaned)
    
    return cleaned.strip() or "Unknown location"


def parse_epoch_ms(epoch_ms: Any) -> Optional[datetime]:
    """Convierte milisegundos de época a objeto datetime con zona horaria UTC."""
    if epoch_ms is None:
        return None
    try:
        ts_sec = float(epoch_ms) / 1000.0
        return datetime.fromtimestamp(ts_sec, tz=timezone.utc)
    except (ValueError, TypeError, OverflowError) as e:
        logger.warning(f"Error parseando epoch ms '{epoch_ms}': {e}")
        return None


def transform_geojson_feature(feature: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforma un Feature individual del GeoJSON de USGS a un registro relacional tipado.
    Garantiza que ningún campo clave sea nulo o cause caídas.
    """
    properties = feature.get("properties") or {}
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates") or [0.0, 0.0, 0.0]

    event_id = feature.get("id") or properties.get("code") or "unknown_id"
    
    # Extracción de coordenadas: [longitud, latitud, profundidad_km]
    lon = float(coordinates[0]) if len(coordinates) > 0 and coordinates[0] is not None else 0.0
    lat = float(coordinates[1]) if len(coordinates) > 1 and coordinates[1] is not None else 0.0
    depth = float(coordinates[2]) if len(coordinates) > 2 and coordinates[2] is not None else 0.0

    # Magnitud con fallback seguro
    raw_mag = properties.get("mag")
    try:
        mag = float(raw_mag) if raw_mag is not None else 0.0
    except (ValueError, TypeError):
        mag = 0.0

    # Marcas de tiempo
    event_time = parse_epoch_ms(properties.get("time")) or datetime.now(timezone.utc)
    updated_time = parse_epoch_ms(properties.get("updated")) or event_time

    # Metadatos sismológicos
    tsunami = int(properties.get("tsunami") or 0)
    sig = int(properties.get("sig") or 0)
    status = str(properties.get("status") or "automatic")
    mag_type = str(properties.get("magType") or "ml")
    raw_place = properties.get("place") or ""
    clean_place = sanitize_text(raw_place)

    return {
        "id": str(event_id),
        "mag": round(mag, 2),
        "place": clean_place,
        "time": event_time,
        "updated": updated_time,
        "longitude": round(lon, 6),
        "latitude": round(lat, 6),
        "depth_km": round(depth, 2),
        "tsunami": tsunami,
        "sig": sig,
        "status": status,
        "mag_type": mag_type,
        "year": event_time.year,
        "month": event_time.month,
    }
