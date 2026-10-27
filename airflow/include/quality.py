import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
import pandas as pd
import pandera as pa
from pandera import Column, Check, DataFrameSchema

logger = logging.getLogger(__name__)

# Esquema declarativo de calidad de datos con Pandera
EarthquakePanderaSchema = DataFrameSchema(
    {
        "id": Column(str, nullable=False, unique=False),
        "mag": Column(
            float,
            Check.in_range(-2.0, 10.0, include_min=True, include_max=True),
            nullable=False,
        ),
        "latitude": Column(
            float,
            Check.in_range(-90.0, 90.0, include_min=True, include_max=True),
            nullable=False,
        ),
        "longitude": Column(
            float,
            Check.in_range(-180.0, 180.0, include_min=True, include_max=True),
            nullable=False,
        ),
        "depth_km": Column(
            float,
            Check.in_range(-10.0, 1000.0, include_min=True, include_max=True),
            nullable=False,
        ),
        "time": Column(pd.Timestamp, nullable=False),
    },
    coerce=True,
    strict=False,
)


def validate_records_batch(
    records: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], float, Dict[str, Any]]:
    """
    Valida un lote de registros contra las reglas sismológicas de Pandera.
    Retorna: (valid_records, invalid_records, quality_score, rules_summary)
    NUNCA levanta una excepción no controlada: clasifica y marca el estado.
    """
    if not records:
        logger.info("Lote de registros vacío para validación.")
        return [], [], 100.0, {"total": 0, "valid": 0, "invalid": 0}

    valid_records = []
    invalid_records = []
    rules_summary = {
        "schema_compliance": {"passed": 0, "failed": 0},
        "coordinate_boundaries": {"passed": 0, "failed": 0},
        "magnitude_range": {"passed": 0, "failed": 0},
        "depth_range": {"passed": 0, "failed": 0},
        "mandatory_fields": {"passed": 0, "failed": 0},
    }

    for item in records:
        errors = []
        
        # 1. Validación de campos obligatorios
        event_id = item.get("id")
        mag = item.get("mag")
        lat = item.get("latitude")
        lon = item.get("longitude")
        depth = item.get("depth_km")
        event_time = item.get("time")

        if not event_id or event_id == "":
            errors.append("Campo 'id' obligatorio faltante o vacío.")
            rules_summary["mandatory_fields"]["failed"] += 1
        else:
            rules_summary["mandatory_fields"]["passed"] += 1

        # 2. Validación de Magnitud [-2.0, 10.0]
        try:
            mag_float = float(mag)
            if mag_float < -2.0 or mag_float > 10.0:
                errors.append(f"Magnitud {mag_float} fuera de rango plausible [-2.0, 10.0].")
                rules_summary["magnitude_range"]["failed"] += 1
            else:
                rules_summary["magnitude_range"]["passed"] += 1
        except (ValueError, TypeError):
            errors.append(f"Magnitud '{mag}' inválida o no numérica.")
            rules_summary["magnitude_range"]["failed"] += 1

        # 3. Validación de Coordenadas
        try:
            lat_float = float(lat)
            lon_float = float(lon)
            if lat_float < -90.0 or lat_float > 90.0:
                errors.append(f"Latitud {lat_float} fuera del rango [-90.0, 90.0].")
                rules_summary["coordinate_boundaries"]["failed"] += 1
            elif lon_float < -180.0 or lon_float > 180.0:
                errors.append(f"Longitud {lon_float} fuera del rango [-180.0, 180.0].")
                rules_summary["coordinate_boundaries"]["failed"] += 1
            else:
                rules_summary["coordinate_boundaries"]["passed"] += 1
        except (ValueError, TypeError):
            errors.append("Coordenadas geográficas inválidas o ausentes.")
            rules_summary["coordinate_boundaries"]["failed"] += 1

        # 4. Validación de Profundidad [-10.0, 1000.0]
        try:
            depth_float = float(depth)
            if depth_float < -10.0 or depth_float > 1000.0:
                errors.append(f"Profundidad {depth_float} km fuera de rango plausible [-10, 1000].")
                rules_summary["depth_range"]["failed"] += 1
            else:
                rules_summary["depth_range"]["passed"] += 1
        except (ValueError, TypeError):
            errors.append(f"Profundidad '{depth}' no es un valor numérico válido.")
            rules_summary["depth_range"]["failed"] += 1

        # 5. Clasificación y asignación de estado
        record_copy = dict(item)
        if errors:
            record_copy["processing_status"] = "INVALID"
            record_copy["validation_error"] = " | ".join(errors)
            record_copy["failed_rules"] = errors
            invalid_records.append(record_copy)
        else:
            record_copy["processing_status"] = "VALID"
            record_copy["validation_error"] = None
            record_copy["failed_rules"] = []
            valid_records.append(record_copy)

    total = len(records)
    valid_count = len(valid_records)
    invalid_count = len(invalid_records)
    quality_score = round((valid_count / total) * 100.0, 2) if total > 0 else 100.0

    logger.info(
        f"Validación de calidad completada: Total={total}, Válidos={valid_count}, Inválidos={invalid_count}, Score={quality_score}%"
    )
    return valid_records, invalid_records, quality_score, rules_summary


def check_freshness(latest_event_time: datetime, max_delay_minutes: int = 60) -> Tuple[bool, float]:
    """Verifica si la marca temporal del sismo más reciente cumple con el umbral de frescura."""
    now_utc = datetime.now(timezone.utc)
    if latest_event_time.tzinfo is None:
        latest_event_time = latest_event_time.replace(tzinfo=timezone.utc)
    delay_minutes = (now_utc - latest_event_time).total_seconds() / 60.0
    is_fresh = delay_minutes <= max_delay_minutes
    return is_fresh, round(delay_minutes, 2)
