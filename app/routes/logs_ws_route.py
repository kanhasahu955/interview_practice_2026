"""WebSocket endpoint: stream formatted log lines (matches `logs/app.log`)."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import get_settings
from app.logging.stream_hub import subscribe_log_stream, unsubscribe_log_stream

router = APIRouter(tags=["INTERNAL"])


@router.websocket(
    "/ws/logs",
    name="websocket_logs",
)
async def websocket_logs(websocket: WebSocket) -> None:
    """Stream **plain-text** log lines (same format as `logs/app.log`). Disabled when `LOG_WS_ENABLED=false`."""
    settings = get_settings()
    if not settings.log_ws_enabled:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    q = subscribe_log_stream()
    try:
        while True:
            line = await q.get()
            await websocket.send_text(line.rstrip("\n"))
    except WebSocketDisconnect:
        pass
    finally:
        unsubscribe_log_stream(q)
