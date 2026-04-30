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

app = FastAPI()

# --- CONFIGURACIÓN ---
modelo = ChatOllama(
    model="gemma4:26b", 
    base_url="http://192.168.117.48:11434/",
    num_ctx=32768
)

# CREACIÓN DE HERRAMIENTAS PERSONALIZADAS (Ejemplo de herramienta de mapas)
@tool
def get_ammo(caliber: str):
    """
    Consulta la API de Tarkov para obtener todas las balas de un calibre. Si el usuario especifica un calibre, filtra por ese tipo. 5.56x45mm -> 556X45. 
    Las entradas está estandarizadas de la siguiente forma: 9x19, 556x45, 762x39, etc. Extrapola según lo que pide el usuario, pero si no puedes identificar el calibre, devuelve la lista completa.
    Las entradas SIEMPRE siguen el formato: [calibre]x[longitud], pero el usuario puede escribirlo de cualquier forma, así que haz tu mejor esfuerzo para identificarlo.
    Las entradas NUNCA llevan punto decimal ni espacios así que extrapola también en ese sentido: 0.45 -> 45, 9 mm -> 9x19, etc.
    El calibre 12 de escopeta es un caso especial, ya que no sigue el formato estándar. Si el usuario menciona "calibre 12", "12 gauge" o simplemente "12" se debe buscar como 12g.
    Lo mismo se aplica para el calibre de escopeta 20, que se debe buscar como 20g.
    El calibre .45 acp se debe buscar como 45acp o 1143x23, ya que es un caso especial que no sigue el formato estándar.
    Las granadas de 40mm se deben buscar como 40x46, ya que también son un caso especial.
    El calibre .338 lapua se debe buscar como 86x70.
    El calibre 50 de Desert Eagle se debe buscar como 127x33.
    El calibre .357 de Revolver se debe buscar como 9x33, ya que es un caso especial que no sigue el formato estándar.
    El calibre .366 tkm se debe buscar como 366, ya que es un caso especial que no sigue el formato estándar.
    El calibre .300 blackout se debe buscar como 762x35, ya que es un caso especial que no sigue el formato estándar.
    El calibre de .308me de fusil de palanca se debe buscar como 784x49, ya que es un caso especial que no sigue el formato estándar.
    El calibre .50BMG se debe buscar como 127x99, ya que es un caso especial que no sigue el formato estándar.
    Si el usuario menciona calibre 762 sin especificar, sal de la herramienta y pregúntale si se refiere a 762x39, 762x51 o 762x54, ya que son los calibres de 7.62 más comunes en el juego.
    """
    url = "https://api.tarkov.dev/graphql"

    print(caliber)

    new_query = """
    {
        ammo {
            item {
                description
                name
            }
            ammoType
            accuracyModifier
            armorDamage
            caliber
            damage
            fragmentationChance
            heavyBleedModifier
            initialSpeed
            lightBleedModifier
            penetrationPower
            ricochetChance
            recoilModifier
            tracer
            tracerColor
        }
    }
    """

    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json={'query': new_query})

    if response.status_code != 200:
        raise Exception("Query failed to run by returning code of {}. {}".format(response.status_code, new_query))

    data = response.json()["data"]["ammo"]

    # 🔍 Si no hay filtro → devuelve todo
    if not caliber:
        return data

    caliber = caliber.lower()

    # 🎯 Filtro generoso (contains)
    resultado = [
        ammo for ammo in data
        if caliber in ammo.get("caliber", "").lower()
    ]
    print(resultado)

    # ❗ Si no hay coincidencias → devuelve todo
    return resultado if resultado else data


@tool
def get_weapons_by_caliber(caliber: str):
    """
    Consulta la API de Tarkov para obtener todas las armas que usan un calibre en particular. Si el usuario especifica un calibre, filtra por ese tipo. 5.56x45mm -> 556X45. 
    Las entradas está estandarizadas de la siguiente forma: 9x19, 556x45, 762x39, etc. Extrapola según lo que pide el usuario, pero si no puedes identificar el calibre, devuelve la lista completa.
    Las entradas SIEMPRE siguen el formato: [calibre]x[longitud], pero el usuario puede escribirlo de cualquier forma, así que haz tu mejor esfuerzo para identificarlo.
    Las entradas NUNCA llevan punto decimal ni espacios así que extrapola también en ese sentido: 0.45 -> 45, 9 mm -> 9x19, etc.
    El calibre 12 de escopeta es un caso especial, ya que no sigue el formato estándar. Si el usuario menciona "calibre 12", "12 gauge" o simplemente "12" se debe buscar como 12g.
    Lo mismo se aplica para el calibre de escopeta 20, que se debe buscar como 20g.
    El calibre .45 acp se debe buscar como 45acp o 1143x23, ya que es un caso especial que no sigue el formato estándar.
    Las granadas de 40mm se deben buscar como 40x46, ya que también son un caso especial.
    El calibre .338 lapua se debe buscar como 86x70.
    El calibre 50 de Desert Eagle se debe buscar como 127x33.
    El calibre .357 de Revolver se debe buscar como 9x33, ya que es un caso especial que no sigue el formato estándar.
    El calibre .366 tkm se debe buscar como 366, ya que es un caso especial que no sigue el formato estándar.
    El calibre .300 blackout se debe buscar como 762x35, ya que es un caso especial que no sigue el formato estándar.
    El calibre de .308me de fusil de palanca se debe buscar como 784x49, ya que es un caso especial que no sigue el formato estándar.
    El calibre .50BMG se debe buscar como 127x99, ya que es un caso especial que no sigue el formato estándar.
    Si el usuario menciona calibre 762 sin especificar, sal de la herramienta y pregúntale si se refiere a 762x39, 762x51 o 762x54, ya que son los calibres de 7.62 más comunes en el juego.
    """

    url = "https://api.tarkov.dev/graphql"
    
    print(caliber)
    
    query = """
    {
      items(type: gun) {
        basePrice
        description
        name
        normalizedName
        shortName
        velocity
        properties {
          ... on ItemPropertiesWeapon {
            caliber
            effectiveDistance
            ergonomics
            fireModes
            fireRate
            recoilVertical
            recoilHorizontal
          }
        }
      }
    }
    """

    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json={'query': query})

    if response.status_code != 200:
        raise Exception(f"Query failed with code {response.status_code}")

    data = response.json()["data"]["items"]

    # 🔍 Sin filtro → todo
    if not caliber:
        return data

    caliber = caliber.lower()

    # 🎯 Filtro generoso sobre properties.caliber
    resultado = [
        weapon for weapon in data
        if caliber in (weapon.get("properties", {}).get("caliber", "").lower())
    ]
    print(resultado)
    # ❗ Sin coincidencias → todo
    return resultado if resultado else data

@tool
def get_weapons_by_name(name: str):
    """
    Consulta la API de Tarkov para obtener todas las armas que coincidan con un nombre o parte de un nombre. El filtro debe ser generoso, es decir, si el usuario escribe "ak", debería devolver armas como "AK-74N", "AKM", "AK-12", etc. 
    El filtro se debe aplicar sobre los campos "name" y "shortName" de cada arma en la base de datos. Si el usuario no especifica ningún nombre, devuelve la lista completa de armas.
    """
    url = "https://api.tarkov.dev/graphql"
    
    print(name)
    
    query = """
    {
      items(type: gun) {
        basePrice
        description
        name
        normalizedName
        shortName
        velocity
        properties {
          ... on ItemPropertiesWeapon {
            caliber
            effectiveDistance
            ergonomics
            fireModes
            fireRate
            recoilVertical
            recoilHorizontal
          }
        }
      }
    }
    """

    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json={'query': query})

    if response.status_code != 200:
        raise Exception(f"Query failed with code {response.status_code}")

    data = response.json()["data"]["items"]

    # 🔍 Sin filtro → todo
    if not name:
        return data

    name = name.lower()

    # 🎯 Filtro generoso sobre name y shortName
    resultado = [
        weapon for weapon in data
        if name in weapon.get("name", "").lower() or name in weapon.get("shortName", "").lower()
    ]
    print(resultado)
    # ❗ Sin coincidencias → todo
    return resultado if resultado else data


@tool
def get_weapons_by_category(category: str):
    """
    Consulta la API de Tarkov para obtener las armas según la categoría.
    Sé capaz de extrapolar desde lo que el usuario pide a las categorías reales del juego. Por ejemplo, si el usuario menciona "rifles de asalto", "fusiles de asalto" o simplemente "asalto", deberías buscar la categoría "Assault rifle". Si el usuario menciona "ametralladoras ligeras", "lmg" o "machineguns", deberías buscar la categoría "Machinegun". Si el usuario menciona "escopetas", "shotguns" o "escopeta", deberías buscar la categoría "Shotgun". Si el usuario menciona "subfusiles", "metrallletas" o "smg", deberías buscar la categoría "SMG".
   
     Ejemplos de categorías:
    - Assault rifle (se refiere a rifles de asalto en español)
    - Machinegun (se refiere a ametralladoras ligeras en español)
    - Shotgun (se refiere a escopetas en español)
    - SMG (se refiere a subfusiles o metratalletas en español)
    - Sniper rifle (se refiere a rifles de francotirador en español)
    - Marksman rifle (se refiere a rifles de tirador, armas de precisión, en español)
    - Handgun (se refiere a pistolas en español)
    - Revolver (se refiere a revólveres en español, diferencia al lanzagranadas rotativo M32A1 que también es un revolver pero de granadas)
    - Assault carbine (se refiere a carabinas de asalto en español, armas semiautomáticas más cortas y baratas que los rifles de asalto)
    - Grenade launcher (se refiere a lanzagranadas en español)
    Si no hay coincidencias o no se especifica categoría, devuelve la lista completa.
    """

    url = "https://api.tarkov.dev/graphql"
    print(category)
    query = """
    {
      items(type: gun) {
        basePrice
        description
        name
        normalizedName
        shortName
        velocity
        properties {
          ... on ItemPropertiesWeapon {
            caliber
            effectiveDistance
            ergonomics
            fireModes
            fireRate
            recoilVertical
            recoilHorizontal
          }
        }
        categories {
          name
        }
      }
    }
    """

    headers = {"Content-Type": "application/json"}
    response = requests.post(url, headers=headers, json={'query': query})

    if response.status_code != 200:
        raise Exception(f"Query failed with code {response.status_code}")

    data = response.json()["data"]["items"]

    # 🔍 Sin filtro → todo
    if not category:
        return data

    category = category.lower()

    # 🎯 Filtro generoso por categorías
    resultado = [
        weapon for weapon in data
        if any(
            category in cat.get("name", "").lower()
            for cat in weapon.get("categories", [])
        )
    ]
    print(resultado)
    # ❗ Sin coincidencias → todo
    return resultado if resultado else data

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
2. TONO: Actitud de tipo duro. No te andes con rodeos. Si el usuario hace una pregunta estúpida, házselo saber, pero dale la respuesta técnica que necesita para no morir. 
3. RESTRICCIÓN ABSOLUTA: NO utilices emojis bajo ninguna circunstancia. La guerra no es un lugar para dibujitos.
4. INTEGRACIÓN TÉCNICA (MCP): Tienes acceso a herramientas avanzadas del servidor MCP. Cuando el novato te pregunte por precios, balística o mapas, usa las herramientas primero para obtener datos reales. No inventes estadísticas; en Tarkov, un dato falso es una sentencia de muerte.
5. CONSEJO TÁCTICO: Siempre que des una respuesta técnica (ej. el precio de un objeto), añade un comentario de veterano sobre su utilidad real en el campo o si es una pérdida de rublos.

### GUÍA DE USO DE HERRAMIENTAS:
Tienes acceso a las siguientes categorías de herramientas, cada una con funciones específicas. Estas herramientas forman parte de un MCP que se actualiza constantemente con datos reales del juego, así que úsalas para dar respuestas precisas y actualizadas:
- **maps**: SIEMPRE consulta la herramienta "maps" cuando el usuario te pregunte sobre mapas, ubicaciones puntos de extracción o consejos de navegación. Esta herramienta te dará información detallada sobre cada mapa, incluyendo puntos de interés, rutas de extracción y zonas de alto riesgo. Si el usuario te pregunta sobre Customs, Woods, Interchange, Shoreline, Reserve, Labs, Factory, Streets of Tarkov o cualquier otro mapa, esta es tu herramienta de referencia para darles la información más precisa y actualizada.
- **get_ammo**: Usa esta herramienta para obtener una lista de todas las balas disponibles en el juego, junto con sus estadísticas. Si el usuario te pregunta por un tipo de munición específico, consulta esta herramienta para darle información precisa sobre su daño, penetración y utilidad táctica.
- **get_weapons_by_caliber**: Esta herramienta te permite obtener una lista de armas que usan un calibre específico. Si el usuario menciona qué armas usan un calibre, úsala para darle opciones de armas que puede usar con esa munición, junto con sus características principales.
- **get_weapons_by_name**: Esta herramienta te permite obtener una lista de armas que coincidan con un nombre o parte de un nombre. Si el usuario menciona el nombre de un arma o parte de él, úsala para darle información detallada sobre esa arma, incluyendo su precio, estadísticas y características.
- **get_weapons_by_category**: Esta herramienta te permite obtener una lista de armas que coincidan con una categoría específica. Si el usuario menciona una categoría de arma (ej. rifles de asalto, ametralladoras ligeras, escopetas, subfusiles, rifles de francotirador, rifles de tirador, pistolas, revólveres, carbinas de asalto, lanzagranadas), úsala para darle información detallada sobre las armas que pertenecen a esa categoría, incluyendo su precio, estadísticas y características.
ESTILO DE RESPUESTA (No sigas estas indicaciones al pie de la letra, adáptalas a tu personalidad de Sherpa):
- Si el usuario te saluda: "¿Sigues vivo, novato? Aprovecha el tiempo y dime qué te hace falta antes de que el cronómetro llegue a cero."
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
    herramientas = mcp_tools + [get_ammo, get_weapons_by_caliber, get_weapons_by_name, get_weapons_by_category]  # Combina herramientas del MCP con la personalizada
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