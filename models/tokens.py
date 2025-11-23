from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class Token(SQLModel, table=True):
    __tablename__ = "tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    id_user: int = Field(foreign_key="users.id")
    token: str
    status_token: bool = Field(default=True)
    date_token: datetime = Field(default_factory=datetime.utcnow)
    expiration: datetime

    user: "User" = Relationship(back_populates="tokens")

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .users import User