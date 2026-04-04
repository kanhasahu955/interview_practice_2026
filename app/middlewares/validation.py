"""Request validation hooks (extend for body size limits, JSON sanity checks, etc.)."""

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """Passthrough placeholder: attach custom checks before route handlers run."""

    async def dispatch(self, request: Request, call_next):
        return await call_next(request)


def register_validation_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestValidationMiddleware)
