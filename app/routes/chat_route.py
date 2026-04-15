from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db import AsyncSessionLocal, get_db
from app.deps import get_websocket_user_optional
from app.modules.auth.model import User
from app.schema.chat import ChatEvent, ChatMessageOut
from app.services.chat_service import get_chat_service


class _ChatConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, room_slug: str) -> None:
        await websocket.accept()
        self._rooms[room_slug].add(websocket)

    def disconnect(self, websocket: WebSocket, room_slug: str) -> None:
        room_connections = self._rooms.get(room_slug)
        if not room_connections:
            return
        room_connections.discard(websocket)
        if not room_connections:
            self._rooms.pop(room_slug, None)

    async def broadcast(self, room_slug: str, event: ChatEvent) -> None:
        stale: list[WebSocket] = []
        for websocket in tuple(self._rooms.get(room_slug, set())):
            try:
                await websocket.send_json(event.model_dump(mode="json"))
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(websocket, room_slug)


class ChatRoutes:
    def __init__(self) -> None:
        self.router = APIRouter()
        self._svc = get_chat_service()
        self._manager = _ChatConnectionManager()
        self._register()

    def _register(self) -> None:
        r = self.router
        svc = self._svc
        manager = self._manager

        @r.get(
            "/rooms/{room_slug}/messages",
            response_model=list[ChatMessageOut],
            summary="Recent chat messages",
            description="Returns the newest persisted chat messages for a room.",
        )
        async def list_room_messages(room_slug: str, session: AsyncSession = Depends(get_db)):
            room, messages = await svc.list_messages(session, room_slug=room_slug)
            return [svc.serialize_message(message, room_slug=room.slug) for message in messages]

        @r.websocket("/ws/rooms/{room_slug}")
        async def room_socket(
            websocket: WebSocket,
            room_slug: str,
            user: User | None = Depends(get_websocket_user_optional),
        ) -> None:
            await manager.connect(websocket, room_slug)
            welcome = ChatEvent(
                type="system",
                payload={
                    "message": (
                        f"Connected as {svc.display_name(user)}."
                        if user
                        else "Connected in read-only mode. Log in to send messages."
                    )
                },
            )
            await websocket.send_json(welcome.model_dump())

            try:
                while True:
                    payload = await websocket.receive_json()
                    if payload.get("type") != "message":
                        continue
                    if user is None:
                        await websocket.send_json(
                            ChatEvent(
                                type="error",
                                payload={"message": "Please log in to send chat messages."},
                            ).model_dump()
                        )
                        continue

                    async with AsyncSessionLocal() as session:
                        try:
                            message = await svc.create_message(
                                session,
                                room_slug=room_slug,
                                body=str(payload.get("body", "")),
                                author=user,
                            )
                        except ValueError as exc:
                            message_text = "Message could not be sent."
                            if str(exc) == "empty_message":
                                message_text = "Message cannot be empty."
                            elif str(exc) == "message_too_long":
                                message_text = "Message is too long."
                            await websocket.send_json(
                                ChatEvent(type="error", payload={"message": message_text}).model_dump()
                            )
                            continue

                    outbound = ChatEvent(
                        type="message",
                        payload=svc.serialize_message(message, room_slug=room_slug).model_dump(mode="json"),
                    )
                    await manager.broadcast(room_slug, outbound)
            except WebSocketDisconnect:
                manager.disconnect(websocket, room_slug)


router = ChatRoutes().router
