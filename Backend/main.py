"""
main.py — Servidor FastAPI para Tarkov Sherpa.
Expone el endpoint POST /ask que actúa como puente entre el frontend
Streamlit y el agente LangChain definido en agent.py.

Cómo arrancar el servidor:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from agent import run_agent  # Importa el agente desde agent.py

# ---------------------------------------------------------------------------
# Inicialización de FastAPI
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Tarkov Sherpa API",
    description="Backend del agente IA para Escape from Tarkov.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS — Permite que el frontend Streamlit (localhost:8501) acceda a la API
# En producción, reemplaza "*" con la URL exacta del frontend.
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Modelos Pydantic para validación de entrada/salida
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    """Cuerpo de la petición al endpoint /ask."""
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Pregunta o solicitud del jugador al Sherpa.",
        examples=["¿Cuánto vale una LEDX?"],
    )


class AskResponse(BaseModel):
    """Cuerpo de la respuesta del endpoint /ask."""
    answer: str = Field(..., description="Respuesta generada por el agente.")
    status: str = Field(default="ok", description="Estado de la operación.")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
async def root():
    """Endpoint de comprobación de salud (health check)."""
    return {"status": "El Sherpa está operativo. 🪖"}


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_sherpa(request: AskRequest):
    """
    Envía una pregunta al agente Tarkov Sherpa y devuelve su respuesta.

    - **message**: Pregunta del usuario (máx. 2000 caracteres).
    """
    try:
        answer = run_agent(request.message)
        return AskResponse(answer=answer, status="ok")
    except ValueError as ve:
        # Error de validación o de lógica de negocio
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        # Error inesperado — no exponer detalles internos al cliente
        raise HTTPException(
            status_code=500,
            detail=f"El Sherpa está caído temporalmente: {str(e)}",
        )
