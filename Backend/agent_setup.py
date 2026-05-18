import os

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from pathlib import Path
from tools import (
    get_ammo, get_armor_materials, get_map_info, get_weapons_by_caliber, get_weapons_by_name, 
    get_weapons_by_category, get_multiAmmo, search_tasks, get_multi_weapons, 
    search_items, search_hideout, get_user_progress
)
from prompts import PROMPT_SISTEMA
import json
from textwrap import indent
import os

load_dotenv()
nvidia_api_key = os.getenv("NVIDIA_API_KEY")

modelo = ChatOllama(
    model="gemma4:26b", 
    base_url="http://192.168.117.48:11434/",
    num_ctx=16384
)

# modelo = ChatNvidia(
#     model="gemma-2b-instruct",
#     nvidia_api_key=nvidia_api_key
# )

ruta_mcp = Path(
    r"C:\Users\User\Desktop\COSAS_INTELIGENCIA_ARTIFICAL"
    r"\Programacion_Inteligencia_Artificial"
    r"\Agentes\Langchain\Proyecto\TarkovAISherpa\Backend\tarkov-mcp"
)

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

async def init_agent():
    mcp_tools = await get_tarkov_mcp()
    herramientas = mcp_tools + [
        get_ammo, get_weapons_by_caliber, get_weapons_by_name, 
        get_weapons_by_category, get_multiAmmo, search_tasks, 
        get_multi_weapons, search_items, search_hideout, get_map_info, 
        get_user_progress, get_armor_materials
    ]
    for tool in herramientas:
        pretty_tool(tool)
        
    checkpointer = InMemorySaver()
    agente = create_agent(
        modelo,
        tools=herramientas,
        system_prompt=PROMPT_SISTEMA,
        checkpointer=checkpointer,
    )
    return agente
