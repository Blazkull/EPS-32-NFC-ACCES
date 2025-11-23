from pydantic import BaseModel
from typing import Optional

class AccessLogCreate(BaseModel):
    id_device: int
    action: str
    id_user: Optional[int] = None
    access_type: str = "local"
    user_name: str