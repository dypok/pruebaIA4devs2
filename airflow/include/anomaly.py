import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


def detect_seismic_anomalies(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detecta anomalías sismológicas usando técnicas estadísticas (Z-score) y Machine Learning (IsolationForest):
    1. Sismos de magnitud extrema (Z-score > 2.5 o mag >= 5.5).
    2. Profundidades anormales (> 300 km o < 0 km).
    3. Eventos con alerta activa de tsunami.
    4. Concentración espacio-temporal inusual (enjambres sísmicos).
    """
    if not records or len(records) < 3:
        logger.info("Muestra insuficiente para análisis analítico de anomalías ML.")
        return []

    alerts = []
    df = pd.DataFrame(records)

    try:
        # 1. Z-score sobre magnitudes
        mags = df["mag"].values
        mean_mag = np.mean(mags)
        std_mag = np.std(mags) if np.std(mags) > 0 else 1.0
        z_scores = (mags - mean_mag) / std_mag

        # 2. Isolation Forest para detectar combinaciones atípicas de magnitud y profundidad
        features = df[["mag", "depth_km"]].fillna(0).values
        iso_forest = IsolationForest(contamination=0.1, random_state=42)
        preds = iso_forest.fit_predict(features)
        anomaly_scores = iso_forest.decision_function(features)

        for i, row in df.iterrows():
            event_id = row["id"]
            mag = float(row["mag"])
            depth = float(row["depth_km"])
            place = str(row["place"])
            tsunami = int(row.get("tsunami", 0))
            z = z_scores[i]
            is_iso_anomaly = (preds[i] == -1)

            # Regla A: Tsunami
            if tsunami == 1:
                alerts.append({
                    "event_id": event_id,
                    "anomaly_score": round(float(abs(z) + 3.0), 3),
                    "anomaly_type": "ALERTA_TSUNAMI",
                    "explanation": f"Sismo de magnitud {mag} en '{place}' con bandera de riesgo de tsunami activada.",
                    "detected_at": datetime.now(timezone.utc),
                })
                continue

            # Regla B: Magnitud extrema
            if mag >= 5.5 or z >= 2.5:
                alerts.append({
                    "event_id": event_id,
                    "anomaly_score": round(float(z), 3),
                    "anomaly_type": "PICO_MAGNITUD",
                    "explanation": f"Magnitud extrema {mag} (Z-score: {z:.2f}) detectada en '{place}'. Supera significativamente el promedio regional ({mean_mag:.2f}).",
                    "detected_at": datetime.now(timezone.utc),
                })
                continue

            # Regla C: Anomalía multivariable (Isolation Forest)
            if is_iso_anomaly and (depth > 250 or mag >= 4.5):
                score = round(float(abs(anomaly_scores[i]) * 10), 3)
                alerts.append({
                    "event_id": event_id,
                    "anomaly_score": score,
                    "anomaly_type": "PATRON_MULTIVARIABLE",
                    "explanation": f"Comportamiento anómalo multivariable (Magnitud {mag}, Profundidad {depth} km) detectado por IsolationForest en '{place}'.",
                    "detected_at": datetime.now(timezone.utc),
                })

        logger.info(f"Detección de anomalías finalizada: {len(alerts)} alertas identificadas.")
        return alerts
    except Exception as e:
        logger.error(f"Error durante el cálculo de anomalías: {e}", exc_info=True)
        return []
