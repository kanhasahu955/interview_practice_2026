"""Rich OpenAPI metadata and modern Swagger UI defaults for `/docs` and `/openapi.json`."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from app.config.settings import Settings

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def read_package_version() -> str:
    try:
        with open(_PROJECT_ROOT / "pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        return str(data.get("project", {}).get("version", "0.1.0"))
    except OSError:
        return "0.1.0"


def _listen_url(settings: Settings) -> str:
    host = settings.uvicorn_host
    if host in ("0.0.0.0", "::", "[::]"):
        host = "127.0.0.1"
    return f"http://{host}:{settings.uvicorn_port}"


def build_openapi_description(settings: Settings) -> str:
    v1 = settings.api_v1_prefix.rstrip("/") or "/api/v1"
    token_path = f"{v1}/auth/token"
    return f"""
## Overview

REST API for a learning platform: **blog**, **syllabus**, **topics**, **coding problems**, **Q&A**, and **references**.
Schemas are generated from Pydantic / SQLModel; try requests from **Swagger UI** (`/docs`) or the **Scalar** reference (`/reference`).

## Base URL

Versioned JSON API lives under **`{v1}`** (configurable via `API_V1_PREFIX`). Static files, HTML pages, and `/health` are outside that prefix.

## Authentication

1. Obtain a JWT with **`POST {token_path}`** using **form** fields `username` (your **email**) and `password`.
2. On protected routes, send header **`Authorization: Bearer`** followed by your JWT string.

In Swagger UI, use **Authorize** and paste only the token value (not the word `Bearer`).

## Roles

| Role | Typical use |
|------|-----------|
| **reader** | Browse public content |
| **author** | Create posts, topics, syllabus items, coding problems, references |
| **admin** | Full access |

## Rate limiting

Sensitive endpoints (e.g. login) use stricter limits. Watch **`429`** and **`Retry-After`** / response body when experimenting.

## Errors

Handled failures return **`StandardErrorResponse`** (see Schemas): `success=false`, **`message`** (readable text), **`error_code`**, **`severity`** (`low` / `medium` / `high` / `critical`), **`detail`** (string or validation list), optional **`debug`** when `API_EXPOSE_INTERNAL_ERRORS=true`.

Starlette **`HTTPException`** responses (e.g. route `404`) may still use a plain `{{"detail": "..."}}` body.
""".strip()


def openapi_tags_metadata() -> list[dict[str, Any]]:
    """Ordered tag list (ALL CAPS) with long descriptions for the docs sidebars."""
    return [
        {
            "name": "AUTH",
            "description": (
                "Registration, OAuth2 password flow (**form** `username` + `password`), and current user profile. "
                "Use the returned **access_token** as a Bearer JWT."
            ),
        },
        {
            "name": "META",
            "description": "Service introspection: lightweight health payload and a map of mounted API areas.",
        },
        {
            "name": "BLOG",
            "description": "Blog posts: public listing and detail; **author** or **admin** required to create. Optional user context may affect visibility.",
        },
        {
            "name": "TOPICS",
            "description": "Topic taxonomy used to relate content (blog, coding, references, Q&A). **Author**/**admin** for creates.",
        },
        {
            "name": "SYLLABUS",
            "description": "Syllabus **modules** and nested **items**. **Author**/**admin** to create modules and items.",
        },
        {
            "name": "CODING",
            "description": "Coding **problems** linked to topics. **Author**/**admin** to create.",
        },
        {
            "name": "QA",
            "description": "Interview **questions** and **answers**; authenticated users may post; **accept** marks the best answer (question owner).",
        },
        {
            "name": "REFERENCES",
            "description": "Curated **references** (links, notes) per topic. **Author**/**admin** to create.",
        },
        {
            "name": "CONSENT",
            "description": (
                "Privacy / **cookie consent** for the browser: read and save choices under **`/consent/cookies`**. "
                "Used by the Jinja site banner; responses set a small **`mo_cookie_consent`** cookie."
            ),
        },
        {
            "name": "PAGES",
            "description": "Server-rendered HTML (Jinja2) for the browser — not consumed by typical API clients.",
        },
        {
            "name": "HEALTH",
            "description": "Process liveness for load balancers and orchestrators.",
        },
        {
            "name": "INTERNAL",
            "description": "Operational or developer utilities (e.g. live log stream). May be disabled in production.",
        },
    ]


def openapi_servers(settings: Settings) -> list[dict[str, str]]:
    return [
        {"url": "/", "description": "Same origin as this documentation page"},
        {"url": _listen_url(settings), "description": "Typical local dev (see `UVICORN_HOST` / `UVICORN_PORT`)"},
    ]


def swagger_ui_modern_parameters() -> dict[str, Any]:
    """Swagger UI 5-friendly options: readable, searchable, persistent auth, timing."""
    return {
        "deepLinking": True,
        "displayOperationId": False,
        "displayRequestDuration": True,
        "docExpansion": "list",
        "defaultModelsExpandDepth": 10,
        "defaultModelExpandDepth": 10,
        "defaultModelRendering": "model",
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True,
        "syntaxHighlight": {"activate": True, "theme": "obsidian"},
        "tryItOutEnabled": True,
        "persistAuthorization": True,
        "operationsSorter": "alpha",
        "tagsSorter": "alpha",
    }


def openapi_contact() -> dict[str, str]:
    return {"name": "API support"}


def openapi_license() -> dict[str, str]:
    return {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }


def attach_standard_error_openapi_schema(app: Any) -> None:
    """
    Inject `StandardErrorResponse` into OpenAPI components so Swagger lists a single reusable error model.
    """
    from fastapi import FastAPI

    if not isinstance(app, FastAPI) or getattr(app.state, "_standard_error_openapi_attached", False):
        return
    app.state._standard_error_openapi_attached = True

    original_openapi = app.openapi

    def openapi_with_standard_errors() -> dict[str, Any]:
        schema = original_openapi()
        try:
            from app.schema.api_envelope import StandardErrorResponse

            full = StandardErrorResponse.model_json_schema(ref_template="#/components/schemas/{model}")
            defs = full.pop("$defs", None)
            comp = schema.setdefault("components", {}).setdefault("schemas", {})
            if isinstance(defs, dict):
                for key, val in defs.items():
                    comp.setdefault(key, val)
            comp["StandardErrorResponse"] = full
        except Exception:
            pass
        return schema

    app.openapi = openapi_with_standard_errors  # type: ignore[method-assign]
