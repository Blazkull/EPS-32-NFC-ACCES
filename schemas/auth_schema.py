from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from .users_schema import UserData

class LoginResponse(BaseModel):
    success: bool
    message: str
    access_token: str
    token_type: str
    expires_at: datetime
    user: UserData

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenValidation(BaseModel):
    valid: bool
    user: Optional[UserData] = None

# ✅ ELIMINAR CONTENIDO DUPLICADO DE actions_schema