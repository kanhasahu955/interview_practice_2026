"""Shared JSON shapes for API errors (OpenAPI + runtime). Success bodies stay route-specific `response_model`s."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ErrorSeverity = Literal["low", "medium", "high", "critical"]


class StandardErrorResponse(BaseModel):
    """
    Handled API errors share this shape. Success responses keep using each route’s `response_model`.

    - **message** — text safe to show to end users.
    - **detail** — either the same string as **message** (simple errors) or the validation issue list (422).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": False,
                    "message": "That email is already registered.",
                    "error_code": "integrity_conflict",
                    "severity": "medium",
                    "detail": "That email is already registered.",
                }
            ]
        }
    )

    success: Literal[False] = Field(False, description="Always `false` for this schema.")
    message: str = Field(description="Primary human-readable explanation.")
    error_code: str = Field(description="Stable code for clients and support (e.g. `validation_error`).")
    severity: ErrorSeverity = Field(
        description="`low` hint, `medium` client/fixable, `high` server or dependency, `critical` severe failure."
    )
    detail: str | list[dict[str, Any]] = Field(
        description="String (usually same as `message`) or, for validation, the list of field errors.",
    )
    debug: dict[str, Any] | None = Field(default=None, description="Present only when `API_EXPOSE_INTERNAL_ERRORS=true`.")


def error_severity_for_code(error_code: str) -> ErrorSeverity:
    mapping: dict[str, ErrorSeverity] = {
        "validation_error": "medium",
        "integrity_conflict": "medium",
        "database_unavailable": "high",
        "database_error": "high",
        "internal_error": "critical",
    }
    return mapping.get(error_code, "high")


def standard_error_json(
    *,
    message: str,
    error_code: str,
    detail: str | list[dict[str, Any]] | None = None,
    debug: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical error JSON dict (used by global exception handlers)."""
    return StandardErrorResponse(
        message=message,
        error_code=error_code,
        severity=error_severity_for_code(error_code),
        detail=detail if detail is not None else message,
        debug=debug,
    ).model_dump(exclude_none=True)
