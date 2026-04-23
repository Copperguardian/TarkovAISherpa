import streamlit as st
import requests
import uuid

st.set_page_config(page_title="Tarkov Sherpa Chat", page_icon="🔫")
st.title("🛡️ Tarkov Sherpa")

# Inicializar ID de conversación y lista de mensajes
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# Dibujar el historial de chat
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        if m.get("reasoning"):
            with st.expander("Pensamiento del Sherpa"):
                st.write(m["reasoning"])
        st.write(m["content"])

# Input del usuario
if prompt := st.chat_input("¿Qué necesitas saber, PMC?"):
    # 1. Mostrar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    # 2. Llamada a la API
    with st.chat_message("assistant"):
        with st.spinner("Consultando datos..."):
            try:
                payload = {"message": prompt, "thread_id": st.session_state.thread_id}
                r = requests.post("http://localhost:8000/chat", json=payload).json()
                
                # Mostrar razonamiento si existe
                if r["reasoning"]:
                    with st.expander("Pensamiento del Sherpa"):
                        st.write(r["reasoning"])
                
                # Mostrar respuesta final
                st.write(r["response"])
                
                # Guardar en el historial
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": r["response"],
                    "reasoning": r["reasoning"]
                })
            except Exception as e:
                st.error("Error de conexión con el servidor.")