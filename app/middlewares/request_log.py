"""HTTP access logging: detailed fields + structured records for Rich console + file."""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import Settings
from app.utils.http_access_labels import (
    http_access_visual,
    response_summary,
    static_message_for_status,
    status_phrase,
)
from app.utils.route_service import infer_route_service

log = logging.getLogger("app.request")


def _skip_access_log_path(path_without_query: str) -> bool:
    """Do not log Swagger, ReDoc, OpenAPI JSON, or Scalar — keeps request logs readable."""
    p = path_without_query if path_without_query.startswith("/") else f"/{path_without_query}"
    if p == "/openapi.json":
        return True
    if p == "/reference" or p.startswith("/reference/"):
        return True
    if p.startswith("/docs"):
        return True
    if p.startswith("/redoc"):
        return True
    return False


def _client_ip(request: Request) -> str:
    if request.client:
        return request.client.host
    return "-"


def _bytes_out(response: Response) -> str:
    h = response.headers.get("content-length")
    if h is not None:
        return h
    # Streaming / some ASGI responses omit length
    body = getattr(response, "body", None)
    if body is not None and isinstance(body, (bytes, bytearray)):
        return str(len(body))
    return "-"


def register_request_logging(app, settings: Settings) -> None:
    if not settings.log_http_access:
        return

    slow_ms = settings.log_http_slow_warning_ms

    class RequestLoggingMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next) -> Response:
            start = time.perf_counter()
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start) * 1000

            if _skip_access_log_path(request.url.path):
                return response

            path = request.url.path
            if request.url.query:
                path = f"{path}?{request.url.query}"

            ua = (request.headers.get("user-agent") or "-").replace("\n", " ").strip()
            if len(ua) > 160:
                ua = ua[:157] + "…"

            rid = getattr(request.state, "request_id", "-")
            application = settings.service_display_name.strip() or settings.app_name
            route_service = infer_route_service(
                path=request.url.path,
                api_v1_prefix=settings.api_v1_prefix,
            )

            code = response.status_code
            ct_header = response.headers.get("content-type")
            bytes_out = _bytes_out(response)
            vis = http_access_visual(code)

            detail = {
                "application": application,
                "route_service": route_service,
                "method": request.method,
                "path": path,
                "status": code,
                "status_code": code,
                "status_phrase": status_phrase(code),
                "static_message": static_message_for_status(code),
                "response": response_summary(content_type=ct_header, bytes_out=bytes_out),
                "content_type": (ct_header.split(";", 1)[0].strip() if ct_header else "-"),
                "ms": elapsed_ms,
                "client": _client_ip(request),
                "request_id": rid,
                "user_agent": ua,
                "bytes_out": bytes_out,
                "slow": bool(slow_ms and elapsed_ms >= slow_ms),
                "log_emoji_tty": vis["emoji_tty"],
                "log_emoji_file": vis["emoji_file"],
                "log_severity_tier": vis["tier"],
                "log_outcome": vis["outcome"],
                "log_priority": vis["priority"],
            }

            is_slow = detail["slow"]
            if is_slow:
                log.warning(
                    "http_request",
                    extra={"http_access": detail},
                )
            else:
                log.info(
                    "http_request",
                    extra={"http_access": detail},
                )
            return response

    app.add_middleware(RequestLoggingMiddleware)
