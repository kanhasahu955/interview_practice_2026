"""Cross-cutting auth-related request metadata (not a substitute for route-level JWT)."""

import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.constant.constants import HttpHeader


class RequestIdentityMiddleware(BaseHTTPMiddleware):
    """Ensures each request has a stable `X-Request-ID` for tracing."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get(HttpHeader.REQUEST_ID) or str(uuid.uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        response.headers.setdefault(HttpHeader.REQUEST_ID, rid)
        return response


def register_request_identity(app: FastAPI) -> None:
    app.add_middleware(RequestIdentityMiddleware)
