from pydantic import BaseModel, EmailStr
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    thread_id: str
    tarkov_token: Optional[str] = None
    user_id: Optional[int] = None

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    faction: str
    level: int
    hideout_progress: str
    playstyle: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ConversationSave(BaseModel):
    title: str
    messages: list
    thread_id: str

class UserUpdate(BaseModel):
    level: Optional[int] = None
    playstyle: Optional[str] = None
    hideout_progress: Optional[str] = None
