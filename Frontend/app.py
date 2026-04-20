"""
app.py — Interfaz de usuario Streamlit para Tarkov Sherpa.
Actúa como cliente de la API FastAPI definida en Backend/main.py.

Cómo arrancar:
    streamlit run app.py

Asegúrate de que el backend FastAPI esté corriendo antes de abrir el frontend.
"""

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Configuración de la página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Tarkov Sherpa 🪖",
    page_icon="🪖",
    layout="centered",
)

# ---------------------------------------------------------------------------
# URL base del backend FastAPI
# Cambia el puerto si arrancas uvicorn en uno diferente.
# ---------------------------------------------------------------------------
BACKEND_URL = "http://localhost:8000/ask"

# ---------------------------------------------------------------------------
# Estilos personalizados (tema oscuro militar)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
        /* Fondo oscuro con tono militar */
        .stApp {
            background-color: #1a1a1a;
            color: #d4c5a9;
        }
        /* Burbuja de mensaje del usuario */
        .user-bubble {
            background-color: #2e4a29;
            border-radius: 12px;
            padding: 10px 14px;
            margin: 6px 0;
            text-align: right;
            color: #e8dcc8;
            font-family: monospace;
        }
        /* Burbuja de mensaje del Sherpa */
        .sherpa-bubble {
            background-color: #2a2a2a;
            border-left: 3px solid #8b7355;
            border-radius: 4px;
            padding: 10px 14px;
            margin: 6px 0;
            color: #d4c5a9;
            font-family: monospace;
        }
        /* Header principal */
        h1 { color: #c5a847 !important; font-family: 'Courier New', monospace; }
        h3 { color: #8b7355 !important; }
        /* Input de texto */
        .stTextInput > div > div > input {
            background-color: #2a2a2a;
            color: #d4c5a9;
            border: 1px solid #8b7355;
        }
        /* Botones */
        .stButton > button {
            background-color: #3d5c38;
            color: #e8dcc8;
            border: none;
            border-radius: 6px;
        }
        .stButton > button:hover {
            background-color: #4e7349;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🪖 Tarkov Sherpa")
st.markdown(
    "_Tu guía veterano en Norvinsk. Sarcástico, pero siempre útil._",
)
st.divider()

# ---------------------------------------------------------------------------
# Estado de sesión — historial de mensajes
# Cada mensaje es un dict: {"role": "user"|"sherpa", "content": str}
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

# Mensaje de bienvenida (solo se añade una vez)
if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "sherpa",
        "content": (
            "Bienvenido al servidor, PMC. Lleva tiempo sin ver una cara nueva... "
            "o sobreviviente, para ser exactos. 🗺️\n\n"
            "Puedo ayudarte con **precios del mercado**, **análisis balístico** "
            "y **consultas sobre misiones**. ¿En qué lío te has metido esta vez?"
        ),
    })

# ---------------------------------------------------------------------------
# Renderizado del historial de chat
# ---------------------------------------------------------------------------
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f'<div class="user-bubble">🧑 {msg["content"]}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="sherpa-bubble">🪖 {msg["content"]}</div>',
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Input del usuario
# ---------------------------------------------------------------------------
st.divider()

with st.form(key="chat_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input(
            label="Tu mensaje",
            placeholder="Ej: ¿Cuánto vale un GPU? / ¿Qué munición uso contra clase 5?",
            label_visibility="collapsed",
        )
    with col2:
        submitted = st.form_submit_button("Enviar ➤")

# ---------------------------------------------------------------------------
# Llamada al backend y actualización del historial
# ---------------------------------------------------------------------------
if submitted and user_input.strip():
    # 1. Añadir mensaje del usuario al historial
    st.session_state.messages.append({"role": "user", "content": user_input.strip()})

    # 2. Llamar al backend FastAPI
    with st.spinner("El Sherpa está consultando sus fuentes..."):
        try:
            response = requests.post(
                BACKEND_URL,
                json={"message": user_input.strip()},
                timeout=60,  # segundos — el agente puede tardar con múltiples pasos
            )
            response.raise_for_status()
            answer = response.json().get("answer", "Sin respuesta del servidor.")
        except requests.exceptions.ConnectionError:
            answer = (
                "⚠️ No puedo conectar con el servidor. "
                "Asegúrate de que el backend FastAPI está corriendo en `localhost:8000`."
            )
        except requests.exceptions.Timeout:
            answer = "⏱️ El Sherpa tardó demasiado en responder. Inténtalo de nuevo."
        except requests.exceptions.HTTPError as e:
            answer = f"❌ Error del servidor ({e.response.status_code}): {e.response.text}"
        except Exception as e:
            answer = f"💥 Error inesperado: {str(e)}"

    # 3. Añadir respuesta del Sherpa al historial
    st.session_state.messages.append({"role": "sherpa", "content": answer})

    # 4. Recargar la página para mostrar los nuevos mensajes
    st.rerun()

# ---------------------------------------------------------------------------
# Botón para limpiar el historial
# ---------------------------------------------------------------------------
st.divider()
col_clear, col_info = st.columns([1, 3])
with col_clear:
    if st.button("🗑️ Nueva raid"):
        st.session_state.messages = []
        st.rerun()
with col_info:
    st.caption(
        "💡 **Ejemplos:** 'precio de Red Keycard' · '9x19 AP 6.3 vs armadura clase 4' · "
        "'¿Qué misión me pide un LEDX?'"
    )
