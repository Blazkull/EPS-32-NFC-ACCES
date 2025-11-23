from datetime import datetime
from typing import Optional
from pydantic import BaseModel, validator
from .users_schema import UserRead

class AccessPinBase(BaseModel):
    pin_code: str
    status: bool = True

    @validator('pin_code')
    def validate_pin_code(cls, v):
        if len(v) != 6 or not v.isdigit():
            raise ValueError('El PIN debe tener exactamente 6 dígitos')
        return v

class AccessPinCreate(AccessPinBase):
    id_user: int

class AccessPinUpdate(BaseModel):
    pin_code: Optional[str]
    status: Optional[bool]

    @validator('pin_code')
    def validate_pin_code(cls, v):
        if v and (len(v) != 6 or not v.isdigit()):
            raise ValueError('El PIN debe tener exactamente 6 dígitos')
        return v

class AccessPinRead(AccessPinBase):
    id: int
    id_user: int
    created_at: datetime
    updated_at: datetime
    user: Optional[UserRead] = None

    class Config:
        from_attributes = True

class PinValidation(BaseModel):
    valid: bool
    pin: Optional[AccessPinRead] = None
    user: Optional[UserRead] = None
    message: str

class PinVerification(BaseModel):
    pin_code: str
    current_pin: Optional[str] = None  # Para verificación antes de cambiar