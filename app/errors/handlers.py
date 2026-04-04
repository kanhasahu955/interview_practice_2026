"""Map database and unexpected failures to readable JSON; log details server-side."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from app.config import Settings
from app.errors.db_messages import (
    generic_database_user_message,
    integrity_user_message,
    operational_user_message,
)
from app.errors.origin import error_origin, origin_for_json, origin_log_extra
from app.schema.api_envelope import standard_error_json

log = logging.getLogger("app.errors")


def _maybe_debug(settings: Settings, exc: BaseException) -> dict[str, Any] | None:
    if not settings.api_expose_internal_errors:
        return None
    out: dict[str, Any] = {
        "exception": exc.__class__.__name__,
        "message": str(exc)[:2000],
    }
    where = origin_for_json(error_origin(exc))
    if where:
        out["where"] = where
    return out


def _validation_message(errors: list[dict[str, Any]]) -> str:
    if not errors:
        return "The request could not be validated."
    parts: list[str] = []
    for e in errors[:6]:
        loc = e.get("loc") or ()
        path = " → ".join(str(x) for x in loc)
        msg = str(e.get("msg", "invalid")).strip()
        if path:
            parts.append(f"{path}: {msg}")
        else:
            parts.append(msg)
    extra = len(errors) - 6
    suffix = f" ({extra} more issue(s))" if extra > 0 else ""
    return "Invalid input — " + "; ".join(parts) + suffix


def register_exception_handlers(app: FastAPI, settings: Settings) -> None:
    """Register handlers after `FastAPI()` construction; HTTPException stays FastAPI default."""

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        msg = _validation_message(errors)
        dbg = _maybe_debug(settings, exc)
        body = standard_error_json(
            message=msg,
            error_code="validation_error",
            detail=errors,
            debug=dbg,
        )
        vo = error_origin(exc)
        log.info(
            "validation_error path=%s errors=%s",
            request.url.path,
            len(errors),
            extra=origin_log_extra(vo),
        )
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=body)

    @app.exception_handler(IntegrityError)
    async def integrity_handler(request: Request, exc: IntegrityError) -> JSONResponse:
        io = error_origin(exc)
        log.warning(
            "integrity_error path=%s",
            request.url.path,
            exc_info=exc,
            extra=origin_log_extra(io),
        )
        msg = integrity_user_message(exc)
        dbg = _maybe_debug(settings, exc)
        body = standard_error_json(
            message=msg,
            error_code="integrity_conflict",
            detail=msg,
            debug=dbg,
        )
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=body)

    @app.exception_handler(OperationalError)
    async def operational_handler(request: Request, exc: OperationalError) -> JSONResponse:
        oo = error_origin(exc)
        log.error(
            "operational_error path=%s",
            request.url.path,
            exc_info=exc,
            extra=origin_log_extra(oo),
        )
        msg = operational_user_message(exc)
        dbg = _maybe_debug(settings, exc)
        body = standard_error_json(
            message=msg,
            error_code="database_unavailable",
            detail=msg,
            debug=dbg,
        )
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=body)

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        so = error_origin(exc)
        log.error(
            "sqlalchemy_error path=%s",
            request.url.path,
            exc_info=exc,
            extra=origin_log_extra(so),
        )
        msg = generic_database_user_message()
        dbg = _maybe_debug(settings, exc)
        body = standard_error_json(
            message=msg,
            error_code="database_error",
            detail=msg,
            debug=dbg,
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body)

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        uo = error_origin(exc)
        log.error(
            "unhandled_error path=%s",
            request.url.path,
            exc_info=exc,
            extra=origin_log_extra(uo),
        )
        msg = "Something went wrong on the server. Please try again later."
        dbg = _maybe_debug(settings, exc)
        body = standard_error_json(
            message=msg,
            error_code="internal_error",
            detail=msg,
            debug=dbg,
        )
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=body)
