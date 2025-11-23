from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from .users_schema import UserRead

class NFCCardBase(BaseModel):
    card_uid: str
    card_name: str
    status: bool = True

class NFCCardCreate(NFCCardBase):
    id_user: int

class NFCCardUpdate(BaseModel):
    card_name: Optional[str]
    status: Optional[bool]

class NFCCardRead(NFCCardBase):
    id: int
    id_user: int
    created_at: datetime
    updated_at: datetime
    user: Optional[UserRead] = None

    class Config:
        from_attributes = True

class NFCCardValidation(BaseModel):
    valid: bool
    card: Optional[NFCCardRead] = None
    user: Optional[UserRead] = None
    message: str

class NFCRegistrationRequest(BaseModel):
    user_id: int
    card_name: str