# backend/agent.py
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.tools import tool
import requests

# Definición de la Tool para el mercado (Requisito: Uso de tools) [cite: 15]
@tool
def get_tarkov_price(item_name: str) -> str:
    """Busca el precio actual de un objeto en el mercado de Tarkov."""
    # Aquí iría tu query GraphQL a tarkov.dev
    # Por ahora devolvemos un mock para el MVP
    return f"El precio actual de {item_name} es de 45,000 rublos."

class TarkovSherpa:
    def __init__(self):
        # Usamos un modelo potente para el razonamiento [cite: 37]
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.tools = [get_tarkov_price]
        
        # Inicializamos el agente (Requisito: Agente con LangChain) [cite: 14]
        self.agent = initialize_agent(
            self.tools,
            self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True
        )

    def ask(self, query: str):
        return self.agent.run(query)