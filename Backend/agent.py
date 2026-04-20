"""
agent.py — Núcleo del agente LangChain/LangGraph para Tarkov Sherpa.
Compatible con:
  langchain      >= 1.2
  langgraph      >= 1.1
  langchain-ollama >= 1.0
  langchain-community >= 0.4

Herramientas incluidas:
  - Tool 1: consultar_precio_mercado (simulada)
  - Tool 2: calcular_balistica
  - RAG   : consultar_misiones_wiki  (si misiones_wiki.txt existe)
"""

import os
import math

# LangGraph — orquestador del agente ReAct para LangChain 1.x
from langgraph.prebuilt import create_react_agent

# LLM y embeddings locales (Ollama)
from langchain_ollama import ChatOllama, OllamaEmbeddings

# Definición de herramientas
from langchain_core.tools import tool

# RAG
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import RetrievalQA

# ---------------------------------------------------------------------------
# LLM — Ollama local (gemma4:26b con razonamiento)
# Servidor Ollama en red local: http://192.168.117.48:11434/
# Si quieres cambiar el modelo basta con editar OLLAMA_MODEL.
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL = "http://192.168.117.48:11434/"
OLLAMA_MODEL    = "gemma4:26b"

llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_BASE_URL,
    reasoning=True,
    num_ctx=16384,
)

# ===========================================================================
# TOOL 1 — Herramienta de Mercado (Market Price Simulator)
# Simula una llamada a la API pública de tarkov.dev.
# En producción: reemplaza el cuerpo de la función por una petición real con
# `requests` al endpoint GraphQL de tarkov.dev.
# ===========================================================================

_FAKE_MARKET_DB: dict[str, dict] = {
    "slick plate carrier":        {"price": 380_000,   "trader": "Ragman",   "currency": "₽"},
    "altyn helmet":               {"price": 420_000,   "trader": "Ragman",   "currency": "₽"},
    "ak-74m":                     {"price": 45_000,    "trader": "Prapor",   "currency": "₽"},
    "m4a1":                       {"price": 75_000,    "trader": "Mechanic", "currency": "₽"},
    "ledx skin transilluminator": {"price": 1_450_000, "trader": "Therapist","currency": "₽"},
    "gpu":                        {"price": 580_000,   "trader": "Mechanic", "currency": "₽"},
    "bitcoin":                    {"price": 430_000,   "trader": "Therapist","currency": "₽"},
    "red keycard":                {"price": 2_200_000, "trader": "Skier",    "currency": "₽"},
}

@tool
def consultar_precio_mercado(item_name: str) -> str:
    """
    Consulta el precio de un artículo en el mercado flea o con traders de Tarkov.
    Usa el nombre del artículo en inglés (ej. 'AK-74M', 'LEDX', 'GPU', 'Red Keycard').
    """
    key = item_name.strip().lower()
    data = _FAKE_MARKET_DB.get(key)
    if data is None:
        for db_key, db_val in _FAKE_MARKET_DB.items():
            if key in db_key or db_key in key:
                data = db_val
                key  = db_key
                break
    if data is None:
        return (
            f"No tengo datos de precio para '{item_name}'. "
            "Intenta con el nombre en inglés o revisa tarkov.dev directamente."
        )
    price_fmt = f"{data['price']:,}".replace(",", ".")
    return (
        f"💰 **{key.title()}** — Mejor venta: **{data['trader']}** "
        f"a **{price_fmt} {data['currency']}** (precio simulado del mercado flea)."
    )


# ===========================================================================
# TOOL 2 — Calculadora Balística
# Probabilidad de penetración usando sigmoide calibrada sobre el sistema real
# de Tarkov (pen_power vs armor_class × factor).
# ===========================================================================

_AMMO_PEN: dict[str, float] = {
    "7.62x39 ps":     26,
    "7.62x39 bp":     50,
    "5.45x39 ps":     29,
    "5.45x39 bs":     51,
    "9x19 pst":       34,
    "9x19 ap 6.3":    58,
    "5.56x45 m855a1": 53,
    "5.56x45 m995":   70,
    "12/70 slug":     18,
    ".338 lapua ap":  70,
    "7.62x54r snb":   62,
}

def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))

@tool
def calcular_balistica(ammo_type: str, armor_class: int) -> str:
    """
    Calcula la probabilidad de penetración de una munición contra una clase de armadura.

    Args:
        ammo_type:   Tipo de munición (ej. '5.45x39 BS', '9x19 AP 6.3').
        armor_class: Clase de armadura, número entero entre 1 y 6.
    """
    if not (1 <= armor_class <= 6):
        return "La clase de armadura debe estar entre 1 y 6."

    ammo_key  = ammo_type.strip().lower()
    pen_power = _AMMO_PEN.get(ammo_key)

    if pen_power is None:
        for k, v in _AMMO_PEN.items():
            if ammo_key in k or k in ammo_key:
                pen_power = v
                ammo_key  = k
                break

    if pen_power is None:
        return (
            f"No tengo datos de la munición '{ammo_type}'. "
            f"Municiones conocidas: {', '.join(_AMMO_PEN.keys())}."
        )

    factor = 8.0
    scale  = 10.0
    raw    = pen_power - (armor_class * factor)
    pct    = round(_sigmoid(raw / scale) * 100, 1)

    if pct >= 75:
        verdict = "✅ Alta probabilidad de penetración. Buena elección contra esta armadura."
    elif pct >= 40:
        verdict = "⚠️ Penetración posible pero no garantizada. Apunta a zonas sin armadura."
    else:
        verdict = "❌ Baja probabilidad. Esa munición rebotará. Cambia de munición."

    return (
        f"🔫 **{ammo_key.upper()}** vs **Armadura Clase {armor_class}**\n"
        f"   Poder de penetración: **{pen_power}** | Factor armadura: **{armor_class * factor:.0f}**\n"
        f"   Probabilidad de penetración: **{pct}%**\n"
        f"   {verdict}"
    )


# ===========================================================================
# RAG — Recuperación de Información desde misiones_wiki.txt
# Si el archivo no existe, la herramienta RAG simplemente no se añade al
# agente. Expande misiones_wiki.txt para mejorar las respuestas.
# ===========================================================================

_WIKI_PATH = os.path.join(os.path.dirname(__file__), "misiones_wiki.txt")
_tools: list = [consultar_precio_mercado, calcular_balistica]

try:
    if os.path.exists(_WIKI_PATH):
        loader    = TextLoader(_WIKI_PATH, encoding="utf-8")
        docs      = loader.load()
        splitter  = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks    = splitter.split_documents(docs)

        embeddings  = OllamaEmbeddings(model=OLLAMA_MODEL, base_url=OLLAMA_BASE_URL)
        vectorstore = FAISS.from_documents(chunks, embeddings)

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
        )

        # Envolver la cadena QA como herramienta @tool compatible con LangGraph
        @tool
        def consultar_misiones_wiki(query: str) -> str:
            """
            Busca información sobre misiones, objetivos de quest y guías de Tarkov
            en la base de conocimiento interna. Úsala cuando el usuario pregunte
            sobre traders, requisitos de misión o ubicación de objetos de quest.
            """
            return qa_chain.invoke(query)

        _tools.append(consultar_misiones_wiki)
        print("[RAG] Índice de misiones cargado correctamente.")
    else:
        print(f"[RAG] '{_WIKI_PATH}' no encontrado. Herramienta RAG desactivada.")
except Exception as e:
    print(f"[RAG] Error al inicializar el índice: {e}. Herramienta RAG desactivada.")


# ===========================================================================
# SYSTEM PROMPT — Personalidad del Sherpa
# ===========================================================================

SYSTEM_PROMPT = (
    "Eres el **Tarkov Sherpa**, un guía veterano y superviviente de las raids más duras "
    "de Norvinsk. Llevas años en la zona y has visto morir a más PMC novatos de los que "
    "puedes contar. Eres brutalmente honesto, ocasionalmente sarcástico y te encanta "
    "recordarle al usuario que 'deberías haber traído mejor munición', pero en el fondo "
    "te importa que sobreviva y prospere.\n\n"
    "Tu misión es ayudar con:\n"
    "- Precios del mercado flea y traders.\n"
    "- Análisis balístico de municiones vs armaduras.\n"
    "- Información sobre misiones y quests.\n"
    "- Consejos tácticos basados en tu vasta experiencia.\n\n"
    "Reglas:\n"
    "1. Responde siempre en el idioma en que te hablen.\n"
    "2. Usa las herramientas disponibles antes de inventarte datos.\n"
    "3. Sé específico, útil y conciso. Un Sherpa no divaga con enemigos en el servidor.\n"
    "4. Si no sabes algo, dilo honestamente: 'Ni yo lo sé, y llevo años aquí.'"
)

# ===========================================================================
# CREACIÓN DEL AGENTE (LangGraph 1.x)
# create_react_agent de langgraph reemplaza al antiguo AgentExecutor.
# ===========================================================================

_agent = create_react_agent(
    model=llm,
    tools=_tools,
    prompt=SYSTEM_PROMPT,
)


def run_agent(user_message: str) -> str:
    """
    Punto de entrada público para ejecutar el agente.

    Args:
        user_message: Mensaje del usuario.

    Returns:
        Respuesta del agente como string.
    """
    try:
        result = _agent.invoke({"messages": [("human", user_message)]})
        # LangGraph devuelve una lista de mensajes; el último es la respuesta final.
        messages = result.get("messages", [])
        if messages:
            return messages[-1].content
        return "El Sherpa no pudo procesar tu solicitud."
    except Exception as e:
        return f"⚠️ Error interno del Sherpa: {str(e)}"
