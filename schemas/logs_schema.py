from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel

class LogBase(BaseModel):
    id_device: int
    id_user: Optional[int] = None
    id_action: Optional[int] = None
    event: str
    access_type: str = "remote"

class LogCreate(LogBase):
    pass

class LogRead(LogBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class LogFilterParams(BaseModel):
    id_device: Optional[int] = None
    id_action: Optional[int] = None
    access_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = 1
    limit: int = 10

class LogReadPaginated(BaseModel):
    total: int
    page: int
    limit: int
    pages: int
    data: List[LogRead]
    counts_by_device: Dict[str, int]
    counts_by_status: Dict[str, int]
    counts_by_action_type: Dict[str, int]
    counts_by_access_type: Dict[str, int]
    
    class Config:
        from_attributes = True