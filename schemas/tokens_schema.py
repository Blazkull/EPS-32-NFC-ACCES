from pydantic import BaseModel
from datetime import datetime

class TokenBase(BaseModel):
    token: str
    expiration: datetime

class TokenRead(TokenBase):
    id: int
    id_user: int
    status_token: bool
    date_token: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime