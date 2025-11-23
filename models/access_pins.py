from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class AccessPin(SQLModel, table=True):
    __tablename__ = "access_pins"

    id: Optional[int] = Field(default=None, primary_key=True)
    id_user: int = Field(foreign_key="users.id")
    pin_code: str = Field(max_length=6)
    status: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    user: "User" = Relationship(back_populates="access_pins")

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .users import User