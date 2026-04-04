"""Stable labels for access logs: HTTP reason phrase, static message, response kind."""

from __future__ import annotations

from http import HTTPStatus
from typing import Final

# One-line, stable explanations for logs and operators (not user-facing i18n).
_STATIC_MESSAGES: Final[dict[int, str]] = {
    100: "Continue — client should send request body.",
    101: "Switching protocols (e.g. WebSocket upgrade).",
    200: "Request succeeded; response body returned.",
    201: "Resource created successfully.",
    202: "Request accepted for asynchronous processing.",
    204: "Success with no content body.",
    301: "Resource moved permanently — new URL in Location.",
    302: "Temporary redirect.",
    304: "Not modified — use cached representation.",
    400: "Bad request — malformed or invalid input.",
    401: "Authentication required or token invalid.",
    403: "Authenticated but not permitted for this action.",
    404: "No resource exists for this URL.",
    405: "HTTP method not allowed on this path.",
    409: "Conflict with current state (e.g. duplicate unique field).",
    422: "Validation failed — see error details in response body.",
    429: "Rate limit exceeded — retry after a short wait.",
    500: "Unexpected server error.",
    502: "Bad gateway — upstream error.",
    503: "Service temporarily unavailable (e.g. database).",
    504: "Gateway timeout.",
}


def status_phrase(code: int) -> str:
    """RFC 7231 reason phrase (e.g. 200 → OK)."""
    try:
        return HTTPStatus(code).phrase
    except ValueError:
        return "Unknown"


def static_message_for_status(code: int) -> str:
    """Fixed operator-facing sentence; falls back to the official phrase."""
    if code in _STATIC_MESSAGES:
        return _STATIC_MESSAGES[code]
    return status_phrase(code)


def response_kind_label(content_type: str | None) -> str:
    """
    Short bucket for the response entity (for logs).
    Uses the raw Content-Type header when present (primary type/subtype only).
    """
    if not content_type or not content_type.strip():
        return "none"
    primary = content_type.split(";", 1)[0].strip().lower()
    if not primary:
        return "none"
    if primary == "application/json" or primary.endswith("+json"):
        return "json"
    if primary == "text/html":
        return "html"
    if primary == "text/event-stream":
        return "sse"
    if primary.startswith("text/"):
        return "text"
    if primary.startswith("multipart/"):
        return "multipart"
    if primary.startswith("image/"):
        return "image"
    if primary.startswith("application/pdf"):
        return "pdf"
    return primary.replace("/", "_")


def response_summary(*, content_type: str | None, bytes_out: str) -> str:
    """Single log field: kind + declared size (e.g. `json bytes=128`)."""
    kind = response_kind_label(content_type)
    b = (bytes_out or "-").strip()
    return f"{kind} bytes={b}"


def http_access_visual(status_code: int) -> dict[str, str]:
    """
    Emoji + severity tier for Rich (TTY) and file logs.
    Tiers: success/redirect = low; client 4xx = medium; server 5xx = high.
    """
    sc = int(status_code)
    if 200 <= sc < 300:
        return {
            "emoji_tty": "😊",
            "emoji_file": "✅",
            "tier": "low",
            "outcome": "success",
            "priority": "happy",
        }
    if 300 <= sc < 400:
        return {
            "emoji_tty": "↪️",
            "emoji_file": "↪",
            "tier": "low",
            "outcome": "redirect",
            "priority": "info",
        }
    if 400 <= sc < 500:
        return {
            "emoji_tty": "🟡",
            "emoji_file": "⚠",
            "tier": "medium",
            "outcome": "client_error",
            "priority": "medium",
        }
    return {
        "emoji_tty": "🔴",
        "emoji_file": "✖",
        "tier": "high",
        "outcome": "server_error",
        "priority": "high",
    }
