from datetime import datetime

from pydantic import ConfigDict
from sqlmodel import Field, SQLModel


class ChatRoomOut(SQLModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Room id.")
    slug: str = Field(description="Stable room slug.")
    title: str = Field(description="Display title.")
    description: str | None = Field(default=None, description="Optional room description.")


class ChatMessageOut(SQLModel):
    id: int = Field(description="Message id.")
    room_slug: str = Field(description="Room slug.")
    author_id: int | None = Field(default=None, description="Sending user id when known.")
    author_name: str = Field(description="Display name for the sender.")
    body: str = Field(description="Plain-text message body.")
    created_at: datetime = Field(description="Creation timestamp.")


class ChatEvent(SQLModel):
    type: str = Field(description="Event type such as `message`, `error`, or `system`.")
    payload: dict = Field(default_factory=dict, description="Event body.")
