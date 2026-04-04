"""Shared OpenAPI `responses=` fragments for consistent Swagger / Scalar docs."""

from __future__ import annotations

from typing import Any

# Short descriptions only (no response body schema) to keep the UI scannable.

R_400: dict[int, dict[str, Any]] = {400: {"description": "Bad request (e.g. invalid `topic_id`)."}}
R_401: dict[int, dict[str, Any]] = {401: {"description": "Not authenticated — send `Authorization: Bearer <JWT>`."}}
R_403: dict[int, dict[str, Any]] = {403: {"description": "Authenticated but this role cannot perform the action."}}
R_404: dict[int, dict[str, Any]] = {404: {"description": "Resource not found."}}
R_409: dict[int, dict[str, Any]] = {409: {"description": "Conflict with existing data (e.g. duplicate slug or email)."}}


def merge_responses(*parts: dict[int, dict[str, Any]]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    for p in parts:
        out.update(p)
    return out
