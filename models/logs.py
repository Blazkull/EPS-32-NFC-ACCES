from datetime import datetime
from typing import Optional
from sqlmodel import Relationship, SQLModel, Field

class Log(SQLModel, table=True):
    __tablename__ = "logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    event: str = Field(max_length=255)
    
    # Claves Foráneas
    id_device: int = Field(foreign_key="devices.id")
    id_user: Optional[int] = Field(default=None, foreign_key="users.id")
    id_action: Optional[int] = Field(default=None, foreign_key="actions_devices.id")
    access_type: str = Field(default="remote")  # nfc, pin, remote

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Relaciones Bidireccionales
    device: "Device" = Relationship(back_populates="logs")
    user: Optional["User"] = Relationship(back_populates="logs")
    action_device: Optional["ActionDevice"] = Relationship(back_populates="logs") 

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .devices import Device
    from .users import User
    from .actions_devices import ActionDevice