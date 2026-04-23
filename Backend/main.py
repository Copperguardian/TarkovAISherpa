from langchain_ollama import ChatOllama
from langchain.messages import AIMessage, SystemMessage, HumanMessage
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.types import Command
from langchain.tools import tool, ToolRuntime
from dataclasses import dataclass
from typing import List
from langgraph.checkpoint.memory import InMemorySaver

# Para el RAG
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_core.vectorstores import VectorStoreRetriever
from langchain_chroma import Chroma

# Configuracion de API
from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI()

# --- CONFIGURACIÓN ---
modelo = ChatOllama(
    model="gemma4:26b", 
    base_url="http://192.168.117.48:11434/"
)

# Herramientas (Aquí conectas tu MCP de Tarkov)
herramientas = [] 

# Memoria persistente
checkpointer = InMemorySaver()

# Agente directo (sin interrupciones)
agente = create_agent(
    modelo,
    tools=herramientas,
    system_prompt="Eres un Sherpa de Tarkov veterano. Responde de forma técnica y directa.",
    checkpointer=checkpointer
)

class ChatRequest(BaseModel):
    message: str
    thread_id: str

@app.post("/chat")
async def chat(req: ChatRequest):
    # El thread_id permite que el bot recuerde lo anterior
    config = {"configurable": {"thread_id": req.thread_id}}
    
    input_data = {"messages": [HumanMessage(content=req.message)]}
    
    final_response = ""
    reasoning = ""

    # Ejecución fluida
    for paso in agente.stream(input_data, config=config, stream_mode="values"):
        if "messages" in paso:
            ultimo_mensaje = paso["messages"][-1]
            final_response = ultimo_mensaje.content
            
            # Extraer razonamiento si el modelo lo proporciona
            if hasattr(ultimo_mensaje, "additional_kwargs"):
                reasoning = ultimo_mensaje.additional_kwargs.get("reasoning_content", "")

    return {
        "response": final_response,
        "reasoning": reasoning
    }