from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class NFCCard(SQLModel, table=True):
    __tablename__ = "nfc_cards"

    id: Optional[int] = Field(default=None, primary_key=True)
    card_uid: str = Field(unique=True, max_length=255)
    id_user: int = Field(foreign_key="users.id")
    card_name: str = Field(max_length=255)
    status: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    user: "User" = Relationship(back_populates="nfc_cards")

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .users import User