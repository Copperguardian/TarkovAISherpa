# --- IMPORTS ---
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
import json
import os
from dotenv import load_dotenv

# Locales
from database import get_db, User, Conversation
from schemas import (
    ChatRequest, UserRegister, UserLogin, 
    ConversationSave, UserUpdate
)
import auth
from agent_setup import init_agent
from langchain.messages import HumanMessage

# Carga de variables de entorno
load_dotenv()

# --- GLOBAL AGENT ---
agente = None

# --- LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global agente
    agente = await init_agent()
    yield  # App runs here

# --- SETUP FASTAPI ---
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- AUTH DEPENDENCY ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token no contiene el sujeto (sub)")
    except auth.JWTError as e:
        raise HTTPException(status_code=401, detail=f"Error al decodificar token: {str(e)}")
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail=f"Usuario {email} no encontrado en la base de datos")
    return user

# --- ENDPOINTS DE USUARIO ---
@app.post("/register")
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    if not auth.validate_email(user_data.email):
        raise HTTPException(status_code=400, detail="Email inválido")
    if not auth.validate_password(user_data.password):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres, una mayúscula, una minúscula y un número")
    
    db_user = db.query(User).filter(User.email == user_data.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    hashed_password = auth.get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email, 
        hashed_password=hashed_password,
        faction=user_data.faction,
        level=user_data.level,
        hideout_progress=user_data.hideout_progress,
        playstyle=user_data.playstyle
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Usuario registrado con éxito"}

@app.post("/login")
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email).first()
    if not user or not auth.verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
    
    access_token = auth.create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "user_id": user.id,
        "profile": {
            "faction": user.faction,
            "level": user.level,
            "hideout_progress": user.hideout_progress,
            "playstyle": user.playstyle
        }
    }

@app.put("/profile")
def update_profile(profile_data: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if profile_data.level is not None:
        current_user.level = profile_data.level
    if profile_data.playstyle is not None:
        current_user.playstyle = profile_data.playstyle
    if profile_data.hideout_progress is not None:
        current_user.hideout_progress = profile_data.hideout_progress
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "Perfil actualizado",
        "profile": {
            "faction": current_user.faction,
            "level": current_user.level,
            "hideout_progress": current_user.hideout_progress,
            "playstyle": current_user.playstyle
        }
    }

# --- ENDPOINTS DE CONVERSACIONES ---
@app.post("/conversations")
def save_conversation(conv_data: ConversationSave, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_conv = Conversation(
        user_id=current_user.id,
        title=conv_data.title,
        messages=json.dumps(conv_data.messages),
        thread_id=conv_data.thread_id
    )
    db.add(new_conv)
    db.commit()
    db.refresh(new_conv)
    return {"id": new_conv.id, "message": "Conversación guardada"}

@app.get("/conversations")
def get_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversations = db.query(Conversation).filter(Conversation.user_id == current_user.id).all()
    return [{
        "id": c.id,
        "title": c.title,
        "created_at": c.created_at,
        "messages": json.loads(c.messages),
        "thread_id": c.thread_id
    } for c in conversations]

@app.post("/chat")
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    user_profile = {}
    if req.user_id:
        user = db.query(User).filter(User.id == req.user_id).first()
        if user:
            user_profile = {
                "faction": user.faction,
                "level": user.level,
                "hideout_progress": user.hideout_progress,
                "playstyle": user.playstyle
            }

    config = {
        "configurable": {
            "thread_id": req.thread_id,
            "user_profile": user_profile
        }
    }

    message_content = req.message
    if user_profile:
        message_content = f"[USER_PROFILE:{json.dumps(user_profile)}] {req.message}"

    input_data = {"messages": [HumanMessage(content=message_content)]}
    
    final_response = ""
    reasoning = ""

    async for paso in agente.astream(input_data, config=config, stream_mode="values"):
        if "messages" in paso:
            if "tool" in paso or "tool_input" in paso or "tool_name" in paso:
                print("Agent is calling a tool:", paso)
            ultimo_mensaje = paso["messages"][-1]
            final_response = ultimo_mensaje.content
            
            if hasattr(ultimo_mensaje, "additional_kwargs"):
                reasoning = ultimo_mensaje.additional_kwargs.get("reasoning_content", "")
    print(final_response)
    return {
        "response": final_response,
        "reasoning": reasoning
    }

# Endpoint proxy (sin uso actual en el chat)
def get_tarkov_tracker_progress(token: str):
    import requests as req_lib
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        r = req_lib.get("https://tarkovtracker.io/api/v2/progress", headers=headers, timeout=10)
        if r.status_code == 401:
            raise HTTPException(status_code=401, detail="Token de TarkovTracker inválido o expirado.")
        r.raise_for_status()
        return r.json()
    except req_lib.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Error al conectar con TarkovTracker: {str(e)}")