from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, DateTime, String, Text, UniqueConstraint, func
from sqlmodel import Field, Relationship, SQLModel

from app.db.columns import fk_bigint, pk_bigint
from app.modules.auth.model import User


class ChatRoom(SQLModel, table=True):
    __tablename__ = "chat_rooms"
    __table_args__ = (UniqueConstraint("slug", name="uq_chat_room_slug"),)

    id: int | None = Field(default=None, sa_column=pk_bigint())
    slug: str = Field(sa_column=Column(String(120), nullable=False, index=True))
    title: str = Field(sa_column=Column(String(255), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    messages: List["ChatMessage"] = Relationship(
        back_populates="room",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "ChatMessage.created_at",
        },
    )


class ChatMessage(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: int | None = Field(default=None, sa_column=pk_bigint())
    room_id: int = Field(sa_column=fk_bigint("chat_rooms.id", nullable=False, ondelete="CASCADE"))
    author_id: int | None = Field(default=None, sa_column=fk_bigint("users.id", nullable=True, ondelete="SET NULL"))
    body: str = Field(sa_column=Column(Text, nullable=False))
    created_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )

    room: Optional[ChatRoom] = Relationship(back_populates="messages")
    author: Optional[User] = Relationship(sa_relationship_kwargs={"lazy": "selectin"})
