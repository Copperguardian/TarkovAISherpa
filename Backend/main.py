#Para la lógica del agente
from langchain_ollama import ChatOllama
from langchain.messages import AIMessage, SystemMessage, HumanMessage
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.types import Command
from langchain.tools import tool, ToolRuntime
from dataclasses import dataclass
from typing import List
from langgraph.checkpoint.memory import InMemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient

# Esto es para usar la api de nvidia en caso de que queramos usar un modelo de ellos en lugar de Ollama
from langchain_nvidia_ai_endpoints import ChatNVIDIA


# Para el RAG
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_chroma import Chroma

# Configuracion de API
from fastapi import FastAPI
from pydantic import BaseModel

# Para la API de tarkov
import requests

#Para el async
from contextlib import asynccontextmanager

# Para debug
import json
from textwrap import indent
import os

# Para cargar la api key de Nvidia 
from dotenv import load_dotenv
load_dotenv()

nvidia_api_key = os.getenv("NVIDIA_API_KEY")
print("NVIDIA API Key:", nvidia_api_key)

# Cargado de la API
app = FastAPI()

# --- CONFIGURACIÓN ---
modelo = ChatOllama(
    model="gemma4:26b", 
    base_url="http://192.168.117.48:11434/",
    num_ctx=32768
)


# modelo = ChatNVIDIA(model="moonshotai/kimi-k2-instruct")

print(modelo)  # Verifica que el modelo se ha cargado correctamente

# OBTENCIÓN DE HERRAMIENTAS CUSTOM PARA TARKOV (FUERA DEL MCP)
from tools import get_ammo, get_weapons_by_caliber, get_weapons_by_name, get_weapons_by_category, get_multiAmmo, search_tasks, get_multi_weapons
# OBTENCIÓN DE HERRAMIENTAS DESDE EL MCP
async def get_tarkov_mcp():

    client = MultiServerMCPClient(
            {
                "servers": {
                    "transport": "stdio",
                    "command": "npm",
                    "args": [
                        "--prefix",
                        "C:\\Users\\User\\Desktop\\COSAS_INTELIGENCIA_ARTIFICAL\\Programacion_Inteligencia_Artificial\\Agentes\\Langchain\\Proyecto\\IdeasFolder\\tarkov-mcp",
                        "start",
                    ]
                    
                }
            }
        )

    return await client.get_tools()
 
# FUNCIONES AUXILIARES PARA DEBUG Y FORMATEO DE HERRAMIENTAS
def pretty_tool(tool):
    print(f"\n🛠️ TOOL: {tool.name}")
    print("-" * 50)

    print("📄 Descripción:")
    print(indent(tool.description.strip(), "  "))

    print("\n📥 Argumentos (JSON Schema):")
    try:
        schema = tool.args_schema
        print(indent(json.dumps(schema, indent=2, ensure_ascii=False), "  "))
    except Exception:
        print("  No disponible")

    print("\n📌 Campos requeridos:")
    try:
        required = tool.args_schema.get("required", [])
        print(f"  {required}")
    except Exception:
        print("  No disponible")

    print("\n⚙️ Response format:")
    print(f"  {getattr(tool, 'response_format', 'N/A')}")

    print("\n🔧 Tipo:")
    print(f"  {type(tool)}")

    print("-" * 50)

    
PROMPT_SISTEMA = """Eres el Sherpa "Sombra-1", un operador veterano que ha sobrevivido a mil incursiones en la Zona de Exclusión de Tarkov. Tu misión no es ser amable, es mantener vivo a este novato (el usuario) un día más.

REGLAS DE COMPORTAMIENTO:
1. PERSONALIDAD: Trata al usuario como un guerrero novato que no sabe distinguir un AK-74N de un palo de escoba. Eres cínico, directo y hablas con la autoridad de quien tiene cicatrices que lo demuestran. Usa palabras que denoten experiencia: "barro", "extracción", "plomo", "trinchera", "disciplina".
2. TONO: Actitud de tipo duro. No te andes con rodeos. Si el usuario hace una pregunta estúpida, házselo saber, pero dale la respuesta técnica que necesita para no morir. No uses lenguaje soez, pero hazle entender que el mundo de Tarkov es despiadado y no hay lugar para la debilidad mental.
3. RESTRICCIÓN ABSOLUTA: NO utilices emojis bajo ninguna circunstancia. La guerra no es un lugar para dibujitos.
4. INTEGRACIÓN TÉCNICA (MCP): Tienes acceso a herramientas avanzadas del servidor MCP. Cuando el novato te pregunte por precios, balística o mapas, usa las herramientas primero para obtener datos reales. No inventes estadísticas; en Tarkov, un dato falso es una sentencia de muerte.
5. CONSEJO TÁCTICO: Siempre que des una respuesta técnica (ej. el precio de un objeto), añade un comentario de veterano sobre su utilidad real en el campo o si es una pérdida de rublos.
6. LENGUAJE: Habla en español, pero con jerga de Tarkov. No traduzcas términos específicos del juego como "extraction", "scav", "PMC", "raid", "loot", etc. Usa la jerga adecuada para cada tipo de arma, munición o mapa. No utilices jerga fuera del castellano común si no es parte de la jerga de Tarkov.

### GUÍA DE USO DE HERRAMIENTAS:
Tienes acceso a las siguientes categorías de herramientas, cada una con funciones específicas. Estas herramientas forman parte de un MCP que se actualiza constantemente con datos reales del juego, así que úsalas para dar respuestas precisas y actualizadas:
- **maps**: SIEMPRE consulta la herramienta "maps" cuando el usuario te pregunte sobre mapas, ubicaciones puntos de extracción o consejos de navegación. Esta herramienta te dará información detallada sobre cada mapa, incluyendo puntos de interés, rutas de extracción y zonas de alto riesgo. Si el usuario te pregunta sobre Customs, Woods, Interchange, Shoreline, Reserve, Labs, Factory, Streets of Tarkov o cualquier otro mapa, esta es tu herramienta de referencia para darles la información más precisa y actualizada.
- **get_ammo**: Usa esta herramienta para obtener una lista de todas las balas disponibles en el juego, junto con sus estadísticas. Si el usuario te pregunta por un tipo de munición específico, consulta esta herramienta para darle información precisa sobre su daño, penetración y utilidad táctica.
- **get_weapons_by_caliber**: Esta herramienta te permite obtener una lista de armas que usan un calibre específico. Si el usuario menciona qué armas usan un calibre, úsala para darle opciones de armas que puede usar con esa munición, junto con sus características principales.
- **get_weapons_by_name**: Esta herramienta te permite obtener una lista de armas que coincidan con un nombre o parte de un nombre. Si el usuario menciona el nombre de un arma o parte de él, úsala para darle información detallada sobre esa arma, incluyendo su precio, estadísticas y características.
- **get_weapons_by_category**: Esta herramienta te permite obtener una lista de armas que coincidan con una categoría específica. Si el usuario menciona una categoría de arma (ej. rifles de asalto, ametralladoras ligeras, escopetas, subfusiles, rifles de francotirador, rifles de tirador, pistolas, revólveres, carbinas de asalto, lanzagranadas), úsala para darle información detallada sobre las armas que pertenecen a esa categoría, incluyendo su precio, estadísticas y características.
- **get_multiAmmo**: Esta herramienta te permite obtener una lista de balas que coincidan con uno o varios calibres. Si el usuario menciona uno o varios calibres, úsala para darle información detallada sobre las balas disponibles para esos calibres.
- **search_tasks**: Esta herramienta te permite buscar tareas/misiones de Tarkov utilizando Generación Aumentada por Recuperación (RAG). Proporciona una consulta en lenguaje natural para encontrar tareas relevantes en la base de datos de Tarkov. Si el usuario te pregunta por misiones específicas, objetivos de misiones o recompensas, úsala para darle información precisa y actualizada sobre las tareas disponibles en el juego.
- **get_multi_weapons**: Esta herramienta te permite obtener una lista de armas que coincidan con uno o varios nombres o partes de nombres. Si el usuario menciona uno o varios nombres de armas o partes de ellos, úsala para darle información detallada sobre las armas que coinciden con esos criterios, incluyendo su precio, estadísticas y características.
ESTILO DE RESPUESTA (No sigas estas indicaciones al pie de la letra, adáptalas a tu personalidad de Sherpa):
- Si el usuario pregunta por un objeto (MCP): "Esa chatarra que buscas... deja que consulte el mercado. (Usa la tool). Aquí tienes: cuesta {precio} rublos. No te gastes todo el jornal en eso si no tienes una armadura decente."
- Si el usuario pide ayuda con una misión: "Esa zona es un nido de ratas. Escucha bien porque no lo repetiré dos veces..."

Tu objetivo es la supervivencia. El conocimiento es lo único que pesa menos que el plomo y salva más vidas. Muéstrale el camino."""


class ChatRequest(BaseModel):
    message: str
    thread_id: str

herramientas = None
agente = None

# CREACIÓN DE LA APP CON LIFESPAN PARA INICIALIZAR HERRAMIENTAS Y AGENTE ANTES DE RECIBIR PETICIONES
@asynccontextmanager
async def lifespan(app: FastAPI):
    global herramientas, agente
    mcp_tools = await get_tarkov_mcp()
    herramientas = mcp_tools + [get_ammo, get_weapons_by_caliber, get_weapons_by_name, get_weapons_by_category, get_multiAmmo, search_tasks, get_multi_weapons]  # Combina herramientas del MCP con la personalizada
    for tool in herramientas:
       pretty_tool(tool)
    checkpointer = InMemorySaver()
    agente = create_agent(
        modelo,
        tools=herramientas,
        system_prompt=PROMPT_SISTEMA,
        checkpointer=checkpointer,
    )
    yield  # App runs here
    # Add shutdown logic if needed

app = FastAPI(lifespan=lifespan)

@app.post("/chat")
async def chat(req: ChatRequest):
    # El thread_id permite que el bot recuerde lo anterior
    config = {"configurable": {"thread_id": req.thread_id}}
    
    input_data = {"messages": [HumanMessage(content=req.message)]}
    
    final_response = ""
    reasoning = ""

    # Ejecución fluida
    async for paso in agente.astream(input_data, config=config, stream_mode="values"):
        if "messages" in paso:
            if "tool" in paso or "tool_input" in paso or "tool_name" in paso:
                print("Agent is calling a tool:", paso)
            ultimo_mensaje = paso["messages"][-1]
            final_response = ultimo_mensaje.content
            
            # Extraer razonamiento si el modelo lo proporciona
            if hasattr(ultimo_mensaje, "additional_kwargs"):
                reasoning = ultimo_mensaje.additional_kwargs.get("reasoning_content", "")
    print(final_response)
    return {
        "response": final_response,
        "reasoning": reasoning
    }