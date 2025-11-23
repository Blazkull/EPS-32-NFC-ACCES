from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class ActionDeviceCreate(BaseModel):
    id_device: int
    action: str
    description: Optional[str] = None

class ActionDeviceRead(BaseModel):
    id: int
    id_device: int
    action: str
    executed: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ActionDeviceUpdate(BaseModel):
    executed: Optional[bool] = None

    class Config:
        from_attributes = True

class ActionDeviceReport(BaseModel):
    id_device: int
    total_actions: int
    executed: int
    pending: int
    failed: int

    class Config:
        from_attributes = True