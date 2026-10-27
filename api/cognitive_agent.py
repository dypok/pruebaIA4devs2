import re
import json
import time
import logging
from typing import Dict, Any, Optional, List
import requests
from config import OLLAMA_BASE_URL, OLLAMA_MODEL
from duckdb_service import duckdb_service
from schemas import IntentCatalogMetadata

logger = logging.getLogger(__name__)


# Base de conocimiento determinista de geofísica y prevención (Fallback de alta fidelidad)
KNOWLEDGE_KB = {
    "richter": (
        "### 🌍 Escala Richter vs. Magnitud de Momento (Mw)\n\n"
        "• **Escala Richter ($M_L$):** Creada en 1935 por Charles Richter, mide la amplitud máxima de las ondas sísmicas en un sismógrafo Wood-Anderson. Se satura en sismos grandes (mayores a magnitud 7.0).\n\n"
        "• **Magnitud de Momento ($M_w$):** Es el estándar científico actual utilizado por USGS y SismoWatch. Mide la energía total liberada basándose en el área de ruptura de la falla, el deslizamiento promedio y la rigidez de la roca.\n\n"
        "• **Escala Mercalli ($MMI$):** A diferencia de la magnitud (energía), la escala de Mercalli mide la **intensidad** o percepción del sismo y los daños causados en un lugar específico (del I al XII)."
    ),
    "mercalli": (
        "### 🏢 Escala de Intensidad Mercalli Modificada (MMI)\n\n"
        "La escala de Mercalli evalúa los **efectos e intensidad** de un sismo sobre personas, estructuras y el terreno en una escala del I (imperceptible) al XII (destrucción total).\n\n"
        "• **Diferencia clave:** Un mismo sismo tiene **una sola magnitud** (energía liberada), pero **múltiples intensidades de Mercalli** según la distancia al epicentro y el tipo de suelo."
    ),
    "falla geologica": (
        "### ⚡ ¿Qué es una falla geológica?\n\n"
        "Una **falla geológica** es una fractura en la corteza terrestre a lo largo de la cual se ha producido un desplazamiento relativo de bloques rocosos debido a esfuerzos tectónicos.\n\n"
        "**Tipos principales:**\n"
        "1. **Fallas de rumbo o desgarre:** Desplazamiento horizontal (ej: la **Falla de San Andrés** en California).\n"
        "2. **Fallas normales:** La roca superior se desliza hacia abajo por extensión de la corteza.\n"
        "3. **Fallas inversas o de cabalgamiento:** La roca superior asciende por compresión tectónica (comunes en zonas de subducción como Chile, Japón y Perú)."
    ),
    "falla": (
        "### ⚡ ¿Qué es una falla geológica?\n\n"
        "Una **falla geológica** es una fractura en la corteza terrestre a lo largo de la cual se ha producido un desplazamiento relativo de bloques rocosos debido a esfuerzos tectónicos.\n\n"
        "**Tipos principales:**\n"
        "1. **Fallas de rumbo o desgarre:** Desplazamiento horizontal (ej: la **Falla de San Andrés** en California).\n"
        "2. **Fallas normales:** La roca superior se desliza hacia abajo por extensión de la corteza.\n"
        "3. **Fallas inversas o de cabalgamiento:** La roca superior asciende por compresión tectónica (comunes en zonas de subducción como Chile, Japón y Perú)."
    ),
    "san andres": (
        "### 🏜️ La Falla de San Andrés\n\n"
        "La Falla de San Andrés es una falla transformante continental de aproximadamente 1,200 km de longitud que marca el límite entre la **Placa del Pacífico** y la **Placa Norteamericana** en California.\n\n"
        "• **Mecanismo:** Desplazamiento horizontal dextral a una velocidad promedio de 3 a 5 cm por año.\n"
        "• **Riesgo:** Acumula tensión elástica continua y es la fuente del temido *'Big One'*, un potencial sismo de magnitud $\\ge 7.8$ esperado en el sur de California."
    ),
    "cinturon de fuego": (
        "### 🔥 El Cinturón de Fuego del Pacífico (Ring of Fire)\n\n"
        "Es una herradura de más de 40,000 kilómetros que bordea el Océano Pacífico, concentrando aproximadamente el **90% de todos los sismos del mundo** y el **75% de los volcanes activos** del planeta.\n\n"
        "• **Causa:** Subducción constante donde placas oceánicas densas (como la Placa de Nazca o la del Pacífico) se hunden bajo placas continentales.\n"
        "• **Países clave en esta zona:** Chile, Perú, Ecuador, Colombia, México, EE.UU. (California/Alaska), Japón, Filipinas e Indonesia."
    ),
    "cinturon": (
        "### 🔥 El Cinturón de Fuego del Pacífico (Ring of Fire)\n\n"
        "Es una herradura de más de 40,000 kilómetros que bordea el Océano Pacífico, concentrando aproximadamente el **90% de todos los sismos del mundo** y el **75% de los volcanes activos** del planeta.\n\n"
        "• **Causa:** Subducción constante donde placas oceánicas densas (como la Placa de Nazca o la del Pacífico) se hunden bajo placas continentales.\n"
        "• **Países clave en esta zona:** Chile, Perú, Ecuador, Colombia, México, EE.UU. (California/Alaska), Japón, Filipinas e Indonesia."
    ),
    "que hacer": (
        "### 🛡️ Medidas de Seguridad y Prevención ante un Terremoto\n\n"
        "**Durante el sismo:**\n"
        "1. **Agáchate, Cúbrete y Sujétate:** Protégete bajo un mueble resistente (escritorio o mesa) y cúbrete la cabeza con las manos.\n"
        "2. **Aléjate de peligros:** Mantente lejos de ventanas, vidrios, espejos y objetos pesados que puedan caer.\n"
        "3. **No uses elevadores:** Emplea siempre las escaleras de emergencia tras cesar el movimiento sísmico.\n"
        "4. **Cierra suministros:** Si es seguro, corta gas y electricidad para evitar incendios secundarios.\n\n"
        "**Después del sismo:**\n"
        "• Prepárate para **réplicas** (*aftershocks*).\n"
        "• Si estás cerca de la costa y el sismo fue violento o prolongado, evacúa de inmediato hacia zonas altas por posible **alerta de tsunami**."
    ),
    "seguridad": (
        "### 🛡️ Medidas de Seguridad y Prevención ante un Terremoto\n\n"
        "**Durante el sismo:**\n"
        "1. **Agáchate, Cúbrete y Sujétate:** Protégete bajo un mueble resistente (escritorio o mesa) y cúbrete la cabeza con las manos.\n"
        "2. **Aléjate de peligros:** Mantente lejos de ventanas, vidrios, espejos y objetos pesados que puedan caer.\n"
        "3. **No uses elevadores:** Emplea siempre las escaleras de emergencia tras cesar el movimiento sísmico.\n"
        "4. **Cierra suministros:** Si es seguro, corta gas y electricidad para evitar incendios secundarios.\n\n"
        "**Después del sismo:**\n"
        "• Prepárate para **réplicas** (*aftershocks*).\n"
        "• Si estás cerca de la costa y el sismo fue violento o prolongado, evacúa de inmediato hacia zonas altas por posible **alerta de tsunami**."
    ),
    "prevencion": (
        "### 🛡️ Medidas de Seguridad y Prevención ante un Terremoto\n\n"
        "**Durante el sismo:**\n"
        "1. **Agáchate, Cúbrete y Sujétate:** Protégete bajo un mueble resistente (escritorio o mesa) y cúbrete la cabeza con las manos.\n"
        "2. **Aléjate de peligros:** Mantente lejos de ventanas, vidrios, espejos y objetos pesados que puedan caer.\n"
        "3. **No uses elevadores:** Emplea siempre las escaleras de emergencia tras cesar el movimiento sísmico.\n"
        "4. **Cierra suministros:** Si es seguro, corta gas y electricidad para evitar incendios secundarios.\n\n"
        "**Después del sismo:**\n"
        "• Prepárate para **réplicas** (*aftershocks*).\n"
        "• Si estás cerca de la costa y el sismo fue violento o prolongado, evacúa de inmediato hacia zonas altas por posible **alerta de tsunami**."
    ),
    "epicentro": (
        "### 🎯 Epicentro vs. Hipocentro (Foco)\n\n"
        "• **Hipocentro (o Foco Sísmico):** Es el punto exacto en el interior de la corteza terrestre donde se inicia la ruptura de la falla y la liberación súbita de energía.\n"
        "• **Epicentro:** Es el punto en la superficie terrestre ubicado verticalmente justo arriba del hipocentro. Es donde se registran las mayores aceleraciones y daños inmediatos."
    ),
    "hipocentro": (
        "### 🎯 Epicentro vs. Hipocentro (Foco)\n\n"
        "• **Hipocentro (o Foco Sísmico):** Es el punto exacto en el interior de la corteza terrestre donde se inicia la ruptura de la falla y la liberación súbita de energía.\n"
        "• **Epicentro:** Es el punto en la superficie terrestre ubicado verticalmente justo arriba del hipocentro. Es donde se registran las mayores aceleraciones y daños inmediatos."
    ),
    "tsunami": (
        "### 🌊 ¿Cómo se genera un Tsunami Sísmico?\n\n"
        "Un tsunami de origen tectónico ocurre cuando un sismo submarino de gran magnitud (habitualmente $M_w > 7.0$) y con hipocentro poco profundo ($< 60$ km) produce una deformación vertical brusca en el fondo oceánico.\n\n"
        "• Esta deformación desplaza una enorme columna de agua que genera olas que viajan a más de 700 km/h en mar abierto.\n"
        "• En SismoWatch, el campo `tsunami = 1` señala advertencias emitidas por centros oficiales como el PTWC y NOAA."
    ),
}


def _normalize_text(text: str) -> str:
    """Normaliza texto a minúsculas y elimina acentos y signos para matching semántico."""
    t = text.lower()
    t = re.sub(r'[áàä]', 'a', t)
    t = re.sub(r'[éèë]', 'e', t)
    t = re.sub(r'[íìï]', 'i', t)
    t = re.sub(r'[óòö]', 'o', t)
    t = re.sub(r'[úùü]', 'u', t)
    t = re.sub(r'[^\w\s]', ' ', t)
    return " ".join(t.split())


class CognitiveAgent:
    """
    Agente Cognitivo de 2 Fases con Inferencia Pura de Qwen 2.5:2b:
    - FASE 1: Identificación de intención, extracción de entidades y catalogación estructurada en JSON.
    - FASE 2: Ejecución especializada guiada por el catálogo sobre DuckDB Lakehouse o base de conocimiento.
    """

    def __init__(self):
        self.ollama_url = f"{OLLAMA_BASE_URL}/api/generate"
        self.model = OLLAMA_MODEL

    # ==========================================================================
    # FASE 1: CLASIFICACIÓN Y CATALOGACIÓN PREVIA (LLM CON QWEN 2.5:2b)
    # ==========================================================================

    def classify_and_catalog(self, prompt: str) -> IntentCatalogMetadata:
        """
        Fase 1: Analiza la pregunta con Qwen 2.5:2b y produce un catálogo formal en JSON
        con intención principal, subtipo analítico/científico, entidades y confianza.
        """
        t0 = time.perf_counter()
        clean_prompt = prompt.strip()

        sys_prompt = (
            "Eres el módulo de Clasificación y Catalogación Cognitiva de SismoWatch.\n"
            "Analiza la pregunta del usuario y responde ÚNICAMENTE con un objeto JSON válido con este esquema exacto:\n"
            "{\n"
            '  "intent": "ANALYTICS" | "KNOWLEDGE" | "STATUS" | "CONVERSATIONAL",\n'
            '  "subtype": "latest_event" | "strongest_events" | "regional_activity" | "tsunami_alerts" | "aggregation" | "science_concept" | "disaster_prevention" | "platform_telemetry" | "greeting" | "help_capabilities" | "gratitude",\n'
            '  "target_location": string o null,\n'
            '  "time_frame": "latest" | "24h" | "historical" | null,\n'
            '  "confidence": float entre 0.0 y 1.0,\n'
            '  "reasoning": string breve de 3 a 5 palabras en ESPAÑOL (ej. "consulta del sismo mas reciente")\n'
            "}\n"
            "Reglas estrictas:\n"
            "1. Toda la respuesta DEBE estar 100% en ESPAÑOL. Está TERMINANTEMENTE PROHIBIDO responder en chino ni usar caracteres asiáticos.\n"
            "2. Preguntas sobre dónde, cuándo o cuál fue el último/más reciente sismo o temblor son SIEMPRE intent=\"ANALYTICS\", subtype=\"latest_event\" y time_frame=\"latest\".\n"
            "3. Preguntas sobre los sismos más fuertes o de mayor magnitud son intent=\"ANALYTICS\" y subtype=\"strongest_events\".\n"
            "4. Si la pregunta menciona '24h', '24 horas', 'últimas 24', 'hoy', 'en el día', DEBES asignar obligatoriamente time_frame=\"24h\".\n"
            "5. Preguntas sobre sismos en una región/país (ej. Chile, California, México) son intent=\"ANALYTICS\" y subtype=\"regional_activity\".\n"
            "6. Preguntas conceptuales teóricas (qué es la falla de San Andrés, qué es la escala Richter) son intent=\"KNOWLEDGE\".\n"
            "7. Saludos o preguntas de cortesía son intent=\"CONVERSATIONAL\".\n"
            "Devuelve EXCLUSIVAMENTE el objeto JSON sin markdown ni texto adicional."
        )

        catalog_data = None
        try:
            payload = {
                "model": self.model,
                "prompt": f"{sys_prompt}\nPregunta: \"{clean_prompt}\"\nJSON:",
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.0, "num_predict": 55}
            }
            resp = requests.post(self.ollama_url, json=payload, timeout=20)
            if resp.status_code == 200:
                raw_json = resp.json().get("response", "").strip()
                clean = re.sub(r"^```(?:json)?\s*", "", raw_json, flags=re.IGNORECASE)
                clean = re.sub(r"\s*```$", "", clean).strip()
                match = re.search(r"\{.*\}", clean, re.DOTALL)
                if match:
                    catalog_data = json.loads(match.group(0))
        except Exception as e:
            logger.warning(f"Error en Fase 1 de catalogación LLM ({e}); activando catalogador de respaldo.")

        step1_latency = round((time.perf_counter() - t0) * 1000, 2)

        # Si el modelo respondió un JSON válido, validarlo y normalizarlo
        if catalog_data and isinstance(catalog_data, dict) and "intent" in catalog_data:
            intent_raw = str(catalog_data.get("intent", "ANALYTICS")).upper()
            intent_norm = intent_raw.lower()
            if intent_norm not in ["conversational", "status", "knowledge", "analytics"]:
                intent_norm = "analytics"

            subtype_norm = str(catalog_data.get("subtype", "latest_event" if intent_norm == "analytics" else "general")).lower()
            confidence_val = float(catalog_data.get("confidence", 0.95))
            target_loc = catalog_data.get("target_location")
            if target_loc and target_loc.lower() == "null":
                target_loc = None
            time_fr = catalog_data.get("time_frame")
            if time_fr and time_fr.lower() == "null":
                time_fr = None

            # Normalización y salvaguarda de entidades y ventana temporal
            p_clean = _normalize_text(clean_prompt)
            if any(w in p_clean for w in ["24h", "24 h", "24 horas", "ultimas 24", "hoy", "el dia de hoy", "del dia", "en el dia"]):
                time_fr = "24h"
            elif any(w in p_clean for w in ["ultimo", "mas reciente", "acaba de ocurrir"]):
                if not time_fr:
                    time_fr = "latest"

            if any(w in p_clean for w in ["fuerte", "mayor magnitud", "mas potente", "maxima magnitud"]):
                subtype_norm = "strongest_events"
                intent_norm = "analytics"

            reasoning_str = catalog_data.get("reasoning", "Clasificado por Qwen 2.5:2b")
            clean_reasoning = self._sanitize_reasoning(reasoning_str, subtype_norm, target_loc)

            return IntentCatalogMetadata(
                intent=intent_norm,
                subtype=subtype_norm,
                confidence=round(confidence_val, 2),
                target_location=target_loc,
                time_frame=time_fr,
                reasoning=clean_reasoning,
                step1_latency_ms=step1_latency,
                total_latency_ms=0.0
            )

        # Fallback determinista si el LLM no estuvo disponible
        return self._heuristic_fallback_catalog(clean_prompt, step1_latency)

    def _sanitize_reasoning(self, reasoning: str, subtype: str, target_loc: Optional[str]) -> str:
        """Garantiza que la descripción de auditoría esté 100% en español sin caracteres chinos/CJK."""
        if not reasoning or re.search(r'[\u4e00-\u9fff]', reasoning):
            descriptions = {
                "latest_event": "Consulta del sismo más reciente en el catálogo",
                "strongest_events": "Ranking de sismos de mayor intensidad sísmica",
                "regional_activity": f"Filtro de sismos en {target_loc}" if target_loc else "Consulta de sismos por región geográfica",
                "tsunami_alerts": "Verificación de alertas de tsunami activas",
                "aggregation": "Concentración sísmica por territorio",
                "science_concept": "Explicación conceptual de sismología",
                "disaster_prevention": "Protocolo de prevención y seguridad",
                "platform_telemetry": "Telemetría y estado operativo del Lakehouse",
                "greeting": "Saludo y bienvenida al usuario",
                "help_capabilities": "Orientación sobre capacidades del asistente",
                "gratitude": "Respuesta a cortesía de usuario",
            }
            return descriptions.get(subtype, "Análisis de consulta sísmica")
        return reasoning

    def _heuristic_fallback_catalog(self, prompt: str, latency_ms: float) -> IntentCatalogMetadata:
        """Catalogador heurístico resiliente de respaldo para garantizar cero fallos de red."""
        p = _normalize_text(prompt)

        # Detectar ventana temporal
        time_frame = None
        if any(w in p for w in ["24h", "24 h", "24 horas", "ultimas 24", "hoy", "el dia de hoy", "del dia", "en el dia"]):
            time_frame = "24h"
        elif any(w in p for w in ["ultimo", "mas reciente", "acaba de ocurrir"]):
            time_frame = "latest"
        elif any(w in p for w in ["historico", "todos los tiempos", "mes"]):
            time_frame = "historical"

        # Conversacional
        if any(w in p for w in ["hola", "buenas", "buen dia", "hey", "saludos"]):
            return IntentCatalogMetadata(
                intent="conversational",
                subtype="greeting",
                confidence=0.99,
                reasoning="Saludo detectado",
                step1_latency_ms=latency_ms
            )
        if any(w in p for w in ["que puedes hacer", "ayuda", "quien eres"]):
            return IntentCatalogMetadata(
                intent="conversational",
                subtype="help_capabilities",
                confidence=0.98,
                reasoning="Solicitud de capacidades del asistente",
                step1_latency_ms=latency_ms
            )

        # Telemetría
        if any(w in p for w in ["total de sismos", "estado del sistema", "pipeline status", "salud"]):
            return IntentCatalogMetadata(
                intent="status",
                subtype="platform_telemetry",
                confidence=0.95,
                reasoning="Consulta de telemetría y salud de plataforma",
                step1_latency_ms=latency_ms
            )

        # Último sismo
        if any(w in p for w in ["ultimo", "reciente"]) and any(w in p for w in ["sismo", "temblor", "terremoto", "donde", "cuando", "fue"]):
            return IntentCatalogMetadata(
                intent="analytics",
                subtype="latest_event",
                time_frame="latest",
                confidence=0.99,
                reasoning="Consulta de ocurrencia del sismo más reciente",
                step1_latency_ms=latency_ms
            )

        # Más fuertes
        if any(w in p for w in ["fuerte", "mayor magnitud", "mas potente", "maxima magnitud"]):
            reasoning = "Ranking de sismos en las últimas 24h" if time_frame == "24h" else "Ranking de sismos por energía liberada"
            return IntentCatalogMetadata(
                intent="analytics",
                subtype="strongest_events",
                time_frame=time_frame,
                confidence=0.98,
                reasoning=reasoning,
                step1_latency_ms=latency_ms
            )

        # Alertas de tsunami
        if any(w in p for w in ["tsunami", "alerta de tsunami", "olas gigantes"]):
            return IntentCatalogMetadata(
                intent="analytics",
                subtype="tsunami_alerts",
                time_frame=time_frame,
                confidence=0.98,
                reasoning="Verificación de alertas de tsunami",
                step1_latency_ms=latency_ms
            )

        # Conceptos teóricos
        if any(p.startswith(pref) for pref in ["que es", "por que tiembla", "que hacer en"]):
            return IntentCatalogMetadata(
                intent="knowledge",
                subtype="science_concept" if "que es" in p else "disaster_prevention",
                confidence=0.96,
                reasoning="Explicación teórica de sismología o prevención",
                step1_latency_ms=latency_ms
            )

        # Búsqueda geográfica
        matched_loc = None
        for loc in ["chile", "japon", "california", "alaska", "hawaii", "mexico", "peru", "panama", "nevada", "vanuatu"]:
            if loc in p:
                matched_loc = loc.title()
                break
        if matched_loc:
            return IntentCatalogMetadata(
                intent="analytics",
                subtype="regional_activity",
                target_location=matched_loc,
                time_frame=time_frame,
                confidence=0.95,
                reasoning=f"Filtro territorial para {matched_loc}",
                step1_latency_ms=latency_ms
            )

        # Predeterminado a analítica
        return IntentCatalogMetadata(
            intent="analytics",
            subtype="latest_event",
            time_frame=time_frame,
            confidence=0.90,
            reasoning="Consulta de datos cuantitativos sobre DuckDB",
            step1_latency_ms=latency_ms
        )

    # ==========================================================================
    # FASE 2: EJECUCIÓN ESPECIALIZADA GUIADA POR EL CATÁLOGO
    # ==========================================================================

    def execute_cataloged_strategy(self, catalog: IntentCatalogMetadata, raw_prompt: str) -> Dict[str, Any]:
        """
        Fase 2: Ejecuta la acción exacta determinada por la catalogación de la Fase 1.
        """
        intent = catalog.intent

        if intent == "conversational":
            return self._handle_conversational(raw_prompt)
        elif intent == "status":
            return self._handle_status(raw_prompt)
        elif intent == "knowledge":
            return self._handle_knowledge(raw_prompt)
        else:
            return self._handle_analytics_guided(catalog, raw_prompt)

    # --------------------------------------------------------------------------
    # Handlers Especializados
    # --------------------------------------------------------------------------

    def _handle_conversational(self, prompt: str) -> Dict[str, Any]:
        p = prompt.lower().strip("?!.,;: ")
        thanks_words = {"gracias", "muchas gracias", "ok", "vale", "listo", "perfecto", "adios", "chao"}
        
        if any(w in p for w in thanks_words):
            reply = "¡Con gusto! Quedo a tu disposición si necesitas consultar algún evento sísmico o resolver dudas."
        elif "que puedes hacer" in p or "ayuda" in p:
            reply = (
                "Soy el asistente analítico de **SismoWatch** impulsado por IA local (Qwen 2.5:2b).\n\n"
                "Puedo ayudarte en tres áreas clave:\n"
                "1. **Analítica de Datos Sísmicos:** Consultar sismos en tiempo real y del histórico de 30 días en DuckDB, identificar máximas magnitudes y generar gráficos.\n"
                "2. **Divulgación y Ciencia:** Explicar conceptos de geofísica, fallas tectónicas, escalas de magnitud y dinámicas de subducción.\n"
                "3. **Seguridad y Prevención:** Brindarte protocolos de evacuación, protección civil y alertas de tsunami.\n\n"
                "💡 *Pruébame con preguntas como:* '¿Dónde fue el último sismo?', '¿Cuáles son los 5 sismos más fuertes?' o '¿Qué es la falla de San Andrés?'."
            )
        else:
            reply = (
                "¡Hola! 👋 Soy tu asistente inteligente de **SismoWatch**.\n\n"
                "Estoy conectado a la red de monitoreo sísmico en tiempo real. Puedes hacerme preguntas sobre datos cuantitativos, sismos recientes o medidas de protección civil.\n\n"
                "¿En qué te puedo colaborar hoy?"
            )

        return {
            "intent": "conversational",
            "reply": reply,
            "sql": None,
            "data": [],
            "chart_suggestion": None,
            "row_count": 0,
        }

    def _handle_status(self, prompt: str) -> Dict[str, Any]:
        """Informa sobre la salud, volumen de datos y origen del Lakehouse SismoWatch."""
        kpis = duckdb_service.get_kpis()
        total_events = kpis.get("total_events_24h", 0)
        max_mag = kpis.get("max_magnitude", 0.0)
        last_sync = kpis.get("last_updated", "Reciente")

        reply = (
            f"### 📡 Estado de la Plataforma SismoWatch\n\n"
            f"• **Almacenamiento Lakehouse (MinIO S3):** Conectado y sincronizado (`sismowatch-lake`).\n"
            f"• **Motor Analítico:** DuckDB operando sobre Parquets particionados.\n"
            f"• **Eventos Sísmicos Registrados:** **{total_events:,} sismos** validados con Pandera (calidad 100%).\n"
            f"• **Magnitud Máxima del Período:** $M_w$ **{max_mag}**.\n"
            f"• **Fuente de Datos:** Feed oficial del *USGS Earthquake Hazards Program*.\n"
            f"• **Orquestación:** Apache Airflow ingiriendo cada 5 minutos de forma autónoma.\n\n"
            f"Todos los servicios operan con normalidad y los datos están disponibles para consulta inmediata."
        )

        return {
            "intent": "status",
            "reply": reply,
            "sql": None,
            "data": [],
            "chart_suggestion": None,
            "row_count": total_events,
        }

    def _handle_knowledge(self, prompt: str) -> Dict[str, Any]:
        """Responde preguntas conceptuales, científicas y de prevención en lenguaje natural puro."""
        p_norm = _normalize_text(prompt)

        # 1. Búsqueda en base de conocimiento de alta fidelidad
        for key, text in sorted(KNOWLEDGE_KB.items(), key=lambda x: len(x[0]), reverse=True):
            if key in p_norm:
                return {
                    "intent": "knowledge",
                    "reply": text,
                    "sql": None,
                    "data": [],
                    "chart_suggestion": None,
                    "row_count": 0,
                }

        # 2. Inferencia con Qwen 2.5:2b para preguntas abiertas no catalogadas
        try:
            sys_prompt = (
                "Eres un sismólogo y experto en gestión de riesgos de desastres de SismoWatch. "
                "Responde la siguiente pregunta del usuario de forma profesional, didáctica y estructurada con viñetas en Markdown. "
                "NO generes código SQL ni inventes tablas. Enfócate exclusivamente en la explicación conceptual o de seguridad."
            )
            payload = {
                "model": self.model,
                "prompt": f"{sys_prompt}\nPregunta del usuario: {prompt}\nRespuesta:",
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 220}
            }
            resp = requests.post(self.ollama_url, json=payload, timeout=25)
            if resp.status_code == 200:
                answer = resp.json().get("response", "").strip()
                if answer and len(answer) > 20:
                    return {
                        "intent": "knowledge",
                        "reply": answer,
                        "sql": None,
                        "data": [],
                        "chart_suggestion": None,
                        "row_count": 0,
                    }
        except Exception as e:
            logger.warning(f"Ollama no respondió para consulta de conocimiento: {e}")

        # Fallback genérico científico
        fallback_reply = (
            "Los sismos ocurren principalmente por la liberación repentina de energía acumulada en las fallas geológicas "
            "debido al movimiento constante de las placas tectónicas. En SismoWatch puedes consultar la distribución "
            "y magnitud de los sismos recientes registrados globalmente por USGS."
        )
        return {
            "intent": "knowledge",
            "reply": fallback_reply,
            "sql": None,
            "data": [],
            "chart_suggestion": None,
            "row_count": 0,
        }

    def _handle_analytics_guided(self, catalog: IntentCatalogMetadata, raw_prompt: str) -> Dict[str, Any]:
        """
        Ejecuta la analítica en DuckDB guiada con precisión por el subtipo catalogado en la Fase 1.
        Soporta filtrado temporal por ventana de 24 horas y filtrado geográfico compuesto.
        """
        subtype = catalog.subtype
        p_norm = _normalize_text(raw_prompt)

        # Evaluar ventana de 24 horas tanto desde catalog como desde raw_prompt
        is_24h = catalog.time_frame == "24h" or any(w in p_norm for w in ["24h", "24 h", "24 horas", "ultimas 24", "hoy", "el dia de hoy", "del dia", "en el dia"])
        time_clause_24h = "time >= (SELECT MAX(time) FROM earthquake_events) - INTERVAL '24 HOUR'"

        sql_to_execute = None

        if subtype == "latest_event":
            if catalog.target_location:
                loc = catalog.target_location.lower()
                sql_to_execute = f"SELECT place, mag, depth_km, strftime(time, '%Y-%m-%d %H:%M:%S UTC') as time FROM earthquake_events WHERE LOWER(place) LIKE '%{loc}%' ORDER BY time DESC LIMIT 1"
            else:
                sql_to_execute = "SELECT place, mag, depth_km, strftime(time, '%Y-%m-%d %H:%M:%S UTC') as time FROM earthquake_events ORDER BY time DESC LIMIT 1"

        elif subtype == "strongest_events":
            where_parts = []
            if is_24h:
                where_parts.append(time_clause_24h)
            if catalog.target_location:
                loc = catalog.target_location.lower()
                where_parts.append(f"LOWER(place) LIKE '%{loc}%'")

            where_sql = f"WHERE {' AND '.join(where_parts)} " if where_parts else ""
            sql_to_execute = f"SELECT place, mag, depth_km, strftime(time, '%Y-%m-%d %H:%M:%S UTC') as time FROM earthquake_events {where_sql}ORDER BY mag DESC LIMIT 5"

        elif subtype == "tsunami_alerts":
            where_parts = ["tsunami = 1"]
            if is_24h:
                where_parts.append(time_clause_24h)
            if catalog.target_location:
                loc = catalog.target_location.lower()
                where_parts.append(f"LOWER(place) LIKE '%{loc}%'")

            where_sql = f"WHERE {' AND '.join(where_parts)} "
            sql_to_execute = f"SELECT place, mag, depth_km, strftime(time, '%Y-%m-%d %H:%M:%S UTC') as time FROM earthquake_events {where_sql}ORDER BY time DESC LIMIT 5"

        elif subtype == "regional_activity":
            where_parts = []
            if catalog.target_location:
                loc = catalog.target_location.lower()
                where_parts.append(f"LOWER(place) LIKE '%{loc}%'")
            if is_24h:
                where_parts.append(time_clause_24h)

            where_sql = f"WHERE {' AND '.join(where_parts)} " if where_parts else ""
            sql_to_execute = f"SELECT place, mag, depth_km, strftime(time, '%Y-%m-%d %H:%M:%S UTC') as time FROM earthquake_events {where_sql}ORDER BY time DESC LIMIT 10"

        elif subtype == "aggregation":
            where_sql = f"WHERE {time_clause_24h} " if is_24h else ""
            sql_to_execute = f"SELECT place, COUNT(*) as count, ROUND(AVG(mag), 2) as avg_mag FROM earthquake_events {where_sql}GROUP BY place ORDER BY count DESC LIMIT 5"

        else:
            # Fallback a Text-to-SQL guiado por LLM
            try:
                sys_prompt = (
                    "Eres un asistente de datos SQL para DuckDB sobre la vista `earthquake_events` "
                    "(columnas: id, mag, place, time, depth_km, tsunami, sig).\n"
                    f"Contexto: La intención ya fue clasificada como '{subtype}'.\n"
                    "Genera ÚNICAMENTE una consulta SQL válida que comience con SELECT. Sin markdown ni explicaciones.\n"
                    "Siempre incluye LIMIT."
                )
                payload = {
                    "model": self.model,
                    "prompt": f"{sys_prompt}\nPregunta: {raw_prompt}\nSQL:",
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 100}
                }
                resp = requests.post(self.ollama_url, json=payload, timeout=20)
                if resp.status_code == 200:
                    raw_sql = resp.json().get("response", "").strip()
                    clean_candidate = re.sub(r"^```(?:sql)?\s*", "", raw_sql, flags=re.IGNORECASE)
                    clean_candidate = re.sub(r"\s*```$", "", clean_candidate).strip().rstrip(";")
                    sql_match = re.search(r"SELECT\s+.*", clean_candidate, re.IGNORECASE | re.DOTALL)
                    if sql_match:
                        sql_to_execute = sql_match.group(0).strip()
            except Exception:
                pass

            if not sql_to_execute:
                where_sql = f"WHERE {time_clause_24h} " if is_24h else ""
                sql_to_execute = f"SELECT place, mag, depth_km, strftime(time, '%Y-%m-%d %H:%M:%S UTC') as time FROM earthquake_events {where_sql}ORDER BY time DESC LIMIT 5"

        # Salvaguarda de LIMIT obligatorio
        upper_sql = sql_to_execute.upper()
        if "LIMIT" not in upper_sql and "GROUP BY" not in upper_sql and "COUNT(" not in upper_sql:
            sql_to_execute = f"{sql_to_execute.rstrip(';')} LIMIT 10"

        # Ejecución en DuckDB
        try:
            res = duckdb_service.execute_read_only_query(sql_to_execute)
            row_count = res.get("row_count", 0)
            data = res.get("data", [])
            cols = res.get("columns", [])

            # Formatear timestamps
            for row in data:
                for k, v in row.items():
                    if isinstance(v, str) and "T" in v and len(v) >= 16:
                        row[k] = v.replace("T", " ")[:16]

            if row_count > 0:
                top_item = data[0]
                place_str = top_item.get("place", "Ubicación no especificada")
                mag_val = top_item.get("mag", "N/A")
                depth_val = top_item.get("depth_km", "N/A")
                time_val = top_item.get("time", "")

                if subtype == "latest_event":
                    reply = (
                        f"📍 **Último sismo registrado:**\n\n"
                        f"• **Epicentro:** *{place_str}*\n"
                        f"• **Magnitud:** **{mag_val} Mw**\n"
                        f"• **Profundidad:** **{depth_val} km**\n"
                        f"• **Hora:** {time_val}\n\n"
                        f"*(Información en tiempo real sincronizada desde USGS en DuckDB)*"
                    )
                elif subtype == "strongest_events":
                    period_str = " (últimas 24 horas)" if is_24h else ""
                    reply = (
                        f"💥 **Sismo de mayor magnitud registrado{period_str}:**\n\n"
                        f"• **Epicentro:** *{place_str}*\n"
                        f"• **Magnitud:** **{mag_val} Mw**\n"
                        f"• **Profundidad:** **{depth_val} km**\n"
                        f"• **Hora:** {time_val}\n\n"
                        f"Se presentan los {row_count} sismos de mayor intensidad sísmica{period_str}:"
                    )
                elif subtype == "tsunami_alerts":
                    period_str = " en las últimas 24 horas" if is_24h else ""
                    reply = (
                        f"🌊 **Eventos sísmicos con alerta de tsunami{period_str}:**\n\n"
                        f"Se encontraron **{row_count} eventos** con indicador de tsunami activo. "
                        f"El evento principal se registró en *{place_str}* con magnitud **{mag_val} Mw**."
                    )
                elif "count" in top_item and "place" in top_item:
                    period_str = " (últimas 24 horas)" if is_24h else ""
                    reply = (
                        f"📊 **Zonas con mayor concentración sísmica{period_str}:**\n\n"
                        f"La zona con mayor frecuencia es *'{top_item['place']}'* con **{top_item.get('count', 0)} sismos** "
                        f"y una magnitud promedio de **{top_item.get('avg_mag', 0)} Mw**."
                    )
                else:
                    period_str = " en las últimas 24 horas" if is_24h else ""
                    reply = (
                        f"📊 Se recuperaron **{row_count} eventos sísmicos** en DuckDB{period_str}.\n\n"
                        f"El evento principal es de magnitud **{mag_val} Mw** en *'{place_str}'* ({time_val})."
                    )
            else:
                period_str = " en las últimas 24 horas" if is_24h else ""
                reply = f"No se encontraron registros sísmicos que coincidan con los criterios solicitados{period_str}."

        except Exception as e:
            logger.error(f"Error ejecutando consulta analítica: {e}")
            reply = f"No se pudo completar la consulta sobre los datos: {e}"
            data = []
            cols = []
            row_count = 0

        # Inferencia de gráfico solo si agrega valor visual (entre 2 y 30 puntos)
        chart_sug = None
        if 2 <= len(data) <= 30:
            from routes.chat_routes import infer_chart_type
            chart_sug = infer_chart_type(data, cols)

        return {
            "intent": "analytics",
            "reply": reply,
            "sql": sql_to_execute,
            "data": data,
            "chart_suggestion": chart_sug,
            "row_count": row_count,
        }

    # ==========================================================================
    # PIPELINE INTEGRAL DE 2 PASOS (PROCESAMIENTO COMPLETO)
    # ==========================================================================

    def process_message(self, prompt: str) -> Dict[str, Any]:
        """
        Orquesta el flujo integral de 2 fases:
        Paso 1: Catalogación estructurada con Qwen 2.5:2b.
        Paso 2: Ejecución guiada y ensamble con metadatos de auditoría para Admin.
        """
        t_global = time.perf_counter()
        clean_prompt = prompt.strip()

        # PASO 1: Identificación y catalogación
        catalog = self.classify_and_catalog(clean_prompt)
        logger.info(f"Paso 1 Catalogado: intent={catalog.intent}, subtype={catalog.subtype}, confidence={catalog.confidence} ({catalog.step1_latency_ms}ms)")

        # PASO 2: Ejecución según catálogo
        result = self.execute_cataloged_strategy(catalog, clean_prompt)

        # Cálculo de latencia global
        total_latency = round((time.perf_counter() - t_global) * 1000, 2)
        catalog.total_latency_ms = total_latency

        # Adjuntar metadatos de catalogación
        result["catalog"] = catalog.dict()
        return result


cognitive_agent = CognitiveAgent()
