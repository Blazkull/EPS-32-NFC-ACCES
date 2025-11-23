from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional

class ActionDevice(SQLModel, table=True):
    __tablename__ = "actions_devices"

    id: Optional[int] = Field(default=None, primary_key=True)
    id_device: int = Field(foreign_key="devices.id")
    action: str = Field(max_length=100)
    executed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    device: "Device" = Relationship(back_populates="actions")
    logs: List["Log"] = Relationship(back_populates="action_device")

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .devices import Device
    from .logs import Log