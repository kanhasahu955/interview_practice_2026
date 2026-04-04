"""Fan-out log lines to WebSocket subscribers (live tail)."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_hub_lock = threading.RLock()
_hub_loop: asyncio.AbstractEventLoop | None = None
_hub_queues: list[asyncio.Queue[str]] = []


def attach_log_stream_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _hub_loop
    with _hub_lock:
        _hub_loop = loop


def detach_log_stream_loop() -> None:
    global _hub_loop
    with _hub_lock:
        _hub_loop = None


def subscribe_log_stream(*, maxsize: int = 400) -> asyncio.Queue[str]:
    q: asyncio.Queue[str] = asyncio.Queue(maxsize=maxsize)
    with _hub_lock:
        _hub_queues.append(q)
    return q


def unsubscribe_log_stream(q: asyncio.Queue[str]) -> None:
    with _hub_lock:
        if q in _hub_queues:
            _hub_queues.remove(q)


def _snapshot_queues() -> list[asyncio.Queue[str]]:
    with _hub_lock:
        return list(_hub_queues)


def publish_log_line(line: str) -> None:
    loop = _hub_loop
    if loop is None or not line:
        return

    def _fan_out() -> None:
        for q in _snapshot_queues():
            try:
                q.put_nowait(line)
            except asyncio.QueueFull:
                try:
                    while not q.empty():
                        q.get_nowait()
                except Exception:
                    pass
                try:
                    q.put_nowait(line)
                except Exception:
                    pass
            except Exception:
                pass

    try:
        loop.call_soon_threadsafe(_fan_out)
    except RuntimeError:
        pass


class WebSocketLogHandler(logging.Handler):
    """Emits formatted log records to all WebSocket subscribers (plain text, one line)."""

    def __init__(self, level: int = logging.NOTSET) -> None:
        super().__init__(level)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            if msg and not msg.endswith("\n"):
                msg = msg + "\n"
            publish_log_line(msg)
        except Exception:
            self.handleError(record)
