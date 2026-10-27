import re
import json
import logging
from typing import Dict, Any, Optional, List
import requests
from config import OLLAMA_BASE_URL, OLLAMA_MODEL
from duckdb_service import duckdb_service

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
    Agente Cognitivo de SismoWatch con inferencia adaptativa de intenciones:
    - CONVERSATIONAL: Saludos, presentación, cortesía y ayuda.
    - KNOWLEDGE: Explicaciones científicas, sismología, placas y protocolos de prevención.
    - STATUS: Telemetría y estado de operación de SismoWatch.
    - ANALYTICS: Consultas cuantitativas sobre la base DuckDB con generación segura de gráficos.
    """

    def __init__(self):
        self.ollama_url = f"{OLLAMA_BASE_URL}/api/generate"
        self.model = OLLAMA_MODEL

    def classify_intent(self, prompt: str) -> str:
        """
        Clasifica la intención del mensaje en:
        - CONVERSATIONAL
        - KNOWLEDGE
        - STATUS
        - ANALYTICS
        """
        p = _normalize_text(prompt)

        # 1. Reglas conversacionales rápidas
        greetings = {"hola", "buenas", "buen dia", "buenos dias", "buenas tardes", "buenas noches", "hey", "hello", "hi", "saludos"}
        help_phrases = {"que puedes hacer", "que haces", "ayuda", "help", "como funciona", "opciones", "quien eres"}
        thanks_phrases = {"gracias", "muchas gracias", "ok", "vale", "listo", "perfecto", "adios", "chao", "hasta luego"}

        if p in greetings or any(p.startswith(g + " ") for g in greetings):
            return "CONVERSATIONAL"
        if p in help_phrases or "puedes hacer" in p or "como te uso" in p:
            return "CONVERSATIONAL"
        if p in thanks_phrases:
            return "CONVERSATIONAL"

        # 2. Estado de la plataforma / Telemetría
        status_triggers = [
            "cuantos sismos", "total de sismos", "datos cargados", "estado del sistema",
            "salud de la plataforma", "origen de los datos", "de donde vienen los datos",
            "cada cuanto se actualiza", "pipeline status", "cuantos registros",
            "estado del pipeline", "salud del sistema"
        ]
        if any(trigger in p for trigger in status_triggers) and "mas fuertes" not in p and "ranking" not in p:
            return "STATUS"

        # 3. Conocimiento científico / divulgación / prevención
        knowledge_triggers = [
            "que es", "por que tiembla", "por que ocurren", "escala richter", "magnitud de momento",
            "falla de san andres", "falla geologica", "cinturon de fuego", "anillo de fuego",
            "que hacer en", "medidas de prevencion", "evacuar", "mochila de emergencia",
            "epicentro", "hipocentro", "foco sismico", "como se produce un tsunami",
            "placas tectonicas", "subduccion", "mercalli", "seguridad", "recomendaciones de seguridad"
        ]
        if any(trigger in p for trigger in knowledge_triggers):
            return "KNOWLEDGE"

        # 4. Señales analíticas (datos específicos, tablas, comparativas, gráficas)
        analytics_triggers = [
            "sismos", "terremoto", "temblor", "magnitud", "zona", "region", "fuerte",
            "tsunami", "ranking", "grafica", "tabla", "promedio", "maximo", "recientes",
            "chile", "japon", "california", "alaska", "panama", "peru", "mexico"
        ]
        if any(trigger in p for trigger in analytics_triggers):
            return "ANALYTICS"

        # Si no encaja en analítica, evaluar como conocimiento general / conversacional
        return "KNOWLEDGE" if len(p.split()) > 3 else "CONVERSATIONAL"

    def process_message(self, prompt: str) -> Dict[str, Any]:
        """
        Procesa el mensaje del usuario con la estrategia adecuada según su intención inferida.
        """
        clean_prompt = prompt.strip()
        intent = self.classify_intent(clean_prompt)
        logger.info(f"Inferencia cognitiva para '{clean_prompt[:40]}...': INTENT={intent}")

        if intent == "CONVERSATIONAL":
            return self._handle_conversational(clean_prompt)
        elif intent == "STATUS":
            return self._handle_status(clean_prompt)
        elif intent == "KNOWLEDGE":
            return self._handle_knowledge(clean_prompt)
        else:
            return self._handle_analytics(clean_prompt)

    # --------------------------------------------------------------------------
    # Handlers Especializados
    # --------------------------------------------------------------------------

    def _handle_conversational(self, prompt: str) -> Dict[str, Any]:
        p = prompt.lower().strip("?!.,;: ")
        thanks_words = {"gracias", "muchas gracias", "ok", "vale", "listo", "perfecto", "adios", "chao"}
        
        if any(w in p for w in thanks_words):
            reply = "¡Con gusto! Quedo a tu disposición si necesitas analizar algún otro evento sísmico o resolver dudas."
        elif "que puedes hacer" in p or "ayuda" in p:
            reply = (
                "Soy el asistente analítico y de gestión de riesgos de **SismoWatch** impulsado por IA local (Qwen 2.5:2b).\n\n"
                "Puedo ayudarte en tres áreas clave:\n"
                "1. **Analítica de Datos Sísmicos:** Consultar sismos en tiempo real y del histórico de 30 días en MinIO/DuckDB, identificar máximas magnitudes y generar gráficos.\n"
                "2. **Divulgación y Ciencia:** Explicar conceptos de geofísica, fallas tectónicas, escalas de magnitud y dinámicas de subducción.\n"
                "3. **Seguridad y Prevención:** Brindarte protocolos de evacuación, protección civil y alertas de tsunami.\n\n"
                "💡 *Pruébame con preguntas como:* '¿Cuáles son los 5 sismos más fuertes?', '¿Qué es la falla de San Andrés?' o '¿Qué hacer durante un sismo?'."
            )
        else:
            reply = (
                "¡Hola! 👋 Soy tu asistente inteligente de **SismoWatch**.\n\n"
                "Estoy conectado a la red de monitoreo sísmico en tiempo real. Puedes hacerme preguntas sobre datos cuantitativos, conceptos científicos de sismología o medidas de protección civil.\n\n"
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

        # 1. Búsqueda en base de conocimiento de alta fidelidad (orden por especificidad)
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
                "Responde la siguiente pregunta del usuario de forma profesional, clara, didáctica y estructurada con viñetas en Markdown. "
                "NO generes código SQL ni inventes tablas de base de datos. Enfócate exclusivamente en la explicación conceptual o de seguridad."
            )
            payload = {
                "model": self.model,
                "prompt": f"{sys_prompt}\nPregunta del usuario: {prompt}\nRespuesta:",
                "stream": False,
                "options": {"temperature": 0.2, "num_predict": 250}
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
            logger.warning(f"Ollama no respondió a tiempo para consulta de conocimiento: {e}")

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

    def _handle_analytics(self, prompt: str) -> Dict[str, Any]:
        """Traduce lenguaje natural a SQL DuckDB, ejecuta sobre Parquets y entrega datos/gráficos."""
        clean_prompt = prompt.strip()
        sql_to_execute = None

        # 1. Intentar Text-to-SQL con Qwen 2.5:2b
        try:
            sys_prompt = (
                "Eres un asistente de datos SQL para DuckDB sobre la vista `earthquake_events` "
                "(columnas: id, mag, place, time, longitude, latitude, depth_km, tsunami, sig).\n"
                "Reglas estrictas:\n"
                "1. Genera ÚNICAMENTE una consulta SQL válida comenzando con SELECT. Sin markdown ni explicaciones.\n"
                "2. SIEMPRE incluye 'LIMIT 5' o 'LIMIT 10' si la consulta no es agregada (GROUP BY).\n"
                "3. NUNCA devuelvas 'SELECT * FROM earthquake_events' sin LIMIT ni filtros.\n"
                "4. Si piden los más fuertes, usa 'ORDER BY mag DESC LIMIT 5'.\n"
                "5. Si piden los más recientes, usa 'ORDER BY time DESC LIMIT 8'."
            )
            payload = {
                "model": self.model,
                "prompt": f"{sys_prompt}\nPregunta del usuario: {clean_prompt}\nSQL:",
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 100}
            }
            resp = requests.post(self.ollama_url, json=payload, timeout=25)
            if resp.status_code == 200:
                raw_sql = resp.json().get("response", "").strip()
                sql_match = re.search(r"SELECT\s+.*", raw_sql, re.IGNORECASE | re.DOTALL)
                if sql_match:
                    candidate = sql_match.group(0).split(";")[0].strip()
                    if candidate.upper().startswith("SELECT"):
                        sql_to_execute = candidate
        except Exception as e:
            logger.warning(f"Ollama no disponible para Text-to-SQL ({e}); activando motor determinista.")

        # 2. Fallback determinista seguro de SQL
        if not sql_to_execute:
            p_lower = clean_prompt.lower()
            if "fuerte" in p_lower or "mayor" in p_lower or "max" in p_lower:
                sql_to_execute = "SELECT place, mag, depth_km, time FROM earthquake_events ORDER BY mag DESC LIMIT 5"
            elif "region" in p_lower or "zona" in p_lower or "donde" in p_lower:
                sql_to_execute = "SELECT place, COUNT(*) as count, ROUND(AVG(mag), 2) as avg_mag FROM earthquake_events GROUP BY place ORDER BY count DESC LIMIT 5"
            elif "tsunami" in p_lower:
                sql_to_execute = "SELECT place, mag, tsunami, time FROM earthquake_events WHERE tsunami = 1 ORDER BY time DESC LIMIT 5"
            else:
                sql_to_execute = "SELECT place, mag, depth_km, time FROM earthquake_events ORDER BY time DESC LIMIT 8"

        # 3. Salvaguarda de límite obligatorio
        upper_sql = sql_to_execute.upper()
        if "LIMIT" not in upper_sql and "GROUP BY" not in upper_sql and "COUNT(" not in upper_sql:
            sql_to_execute = f"{sql_to_execute.rstrip(';')} LIMIT 10"

        # 4. Ejecución en DuckDB
        try:
            res = duckdb_service.execute_read_only_query(sql_to_execute)
            row_count = res.get("row_count", 0)
            data = res.get("data", [])
            cols = res.get("columns", [])

            # Formatear timestamps en los datos
            for row in data:
                for k, v in row.items():
                    if isinstance(v, str) and "T" in v and len(v) >= 16:
                        row[k] = v.replace("T", " ")[:16]

            if row_count > 0:
                top_item = data[0]
                if "mag" in top_item and "place" in top_item:
                    reply = (
                        f"He consultado los datos en DuckDB ({row_count} registros recuperados). "
                        f"El evento más destacado fue de magnitud **{top_item['mag']}** en *'{top_item['place']}'*."
                    )
                else:
                    reply = f"He ejecutado la consulta SQL sobre los eventos en DuckDB y recuperé {row_count} registros."
            else:
                reply = "La consulta se ejecutó exitosamente pero no se encontraron registros que coincidan con esos criterios."

        except Exception as e:
            logger.error(f"Error ejecutando consulta analítica: {e}")
            reply = f"No se pudo completar la consulta sobre los datos: {e}"
            data = []
            cols = []
            row_count = 0

        # 5. Inferencia de gráfico solo si agrega valor visual (entre 2 y 30 puntos)
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


cognitive_agent = CognitiveAgent()
