from fastapi import FastAPI, Request

from app.constant.constants import HttpHeader


def register_security_headers(app: FastAPI) -> None:
    @app.middleware("http")
    async def _security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault(HttpHeader.X_CONTENT_TYPE_OPTIONS, "nosniff")
        response.headers.setdefault(HttpHeader.X_FRAME_OPTIONS, "DENY")
        response.headers.setdefault(HttpHeader.REFERRER_POLICY, "strict-origin-when-cross-origin")
        return response
