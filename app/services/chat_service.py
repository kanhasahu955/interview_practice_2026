from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.auth.model import User
from app.modules.chat.model import ChatMessage, ChatRoom
from app.schema.chat import ChatMessageOut


class ChatService:
    DEFAULT_ROOM_SLUG = "python-help"
    DEFAULT_ROOM_TITLE = "Python Help Room"
    DEFAULT_ROOM_DESCRIPTION = "Live room for Python questions, debugging help, and study discussion."

    @staticmethod
    def _unwrap_model(result: Any) -> Any:
        if result is None:
            return None
        if hasattr(result, "_mapping"):
            values = list(result._mapping.values())
            if values:
                return values[0]
        if isinstance(result, (tuple, list)) and result:
            return result[0]
        return result

    async def get_or_create_room(self, session: AsyncSession, slug: str = DEFAULT_ROOM_SLUG) -> ChatRoom:
        stmt = select(ChatRoom).where(ChatRoom.slug == slug)
        room = self._unwrap_model((await session.exec(stmt)).first())
        if room:
            return room

        room = ChatRoom(
            slug=slug,
            title=self.DEFAULT_ROOM_TITLE,
            description=self.DEFAULT_ROOM_DESCRIPTION,
        )
        session.add(room)
        await session.commit()
        await session.refresh(room)
        return room

    async def list_messages(
        self,
        session: AsyncSession,
        *,
        room_slug: str = DEFAULT_ROOM_SLUG,
        limit: int = 50,
    ) -> tuple[ChatRoom, list[ChatMessage]]:
        room = await self.get_or_create_room(session, slug=room_slug)
        stmt = (
            select(ChatMessage)
            .options(selectinload(ChatMessage.author))
            .where(ChatMessage.room_id == room.id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(limit)
        )
        rows = [self._unwrap_model(row) for row in (await session.exec(stmt)).all()]
        rows.reverse()
        return room, rows

    async def create_message(
        self,
        session: AsyncSession,
        *,
        room_slug: str = DEFAULT_ROOM_SLUG,
        body: str,
        author: User,
    ) -> ChatMessage:
        clean_body = (body or "").strip()
        if not clean_body:
            raise ValueError("empty_message")
        if len(clean_body) > 2000:
            raise ValueError("message_too_long")

        room = await self.get_or_create_room(session, slug=room_slug)
        message = ChatMessage(room_id=room.id, author_id=author.id, body=clean_body)
        session.add(message)
        await session.commit()

        stmt = (
            select(ChatMessage)
            .options(selectinload(ChatMessage.author), selectinload(ChatMessage.room))
            .where(ChatMessage.id == message.id)
        )
        saved = self._unwrap_model((await session.exec(stmt)).first())
        if saved is None:
            raise ValueError("message_not_saved")
        return saved

    def serialize_message(self, message: ChatMessage, *, room_slug: str | None = None) -> ChatMessageOut:
        created_at = message.created_at
        if created_at is None:
            raise ValueError("message_missing_created_at")
        return ChatMessageOut(
            id=message.id or 0,
            room_slug=room_slug or (message.room.slug if message.room else self.DEFAULT_ROOM_SLUG),
            author_id=message.author_id,
            author_name=self.display_name(message.author),
            body=message.body,
            created_at=created_at,
        )

    @staticmethod
    def display_name(user: User | None) -> str:
        if user is None:
            return "Anonymous learner"
        return (user.full_name or user.email).strip()


_chat: ChatService | None = None


def get_chat_service() -> ChatService:
    global _chat
    if _chat is None:
        _chat = ChatService()
    return _chat
