from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr

# 🔥 NUEVA CLASE UserData AÑADIDA
class UserData(BaseModel):
    id: int
    username: str
    name: str
    email: str

class UserBase(BaseModel):
    username: str
    email: EmailStr
    name: Optional[str] = None
    status: bool = True

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str]
    email: Optional[EmailStr]
    name: Optional[str]
    password: Optional[str]
    status: Optional[bool]

class UserRead(UserBase):
    id: int
    created_at: datetime
    last_connection: Optional[datetime]

    class Config:
        from_attributes = True

class UserWithCards(UserRead):
    nfc_cards: List["NFCCardRead"] = []
    access_pins: List["AccessPinRead"] = []

class UserLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime

# Importaciones circulares al final
from .nfc_schema import NFCCardRead
from .pins_schema import AccessPinRead
UserWithCards.update_forward_refs()