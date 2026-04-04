"""Cookie consent API — persists choice in a browser cookie and returns JSON for live UI sync."""

from __future__ import annotations

import base64
import json
from typing import Any

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from app.constant.constants import CookieConsentConstants
from app.schema.consent import CookieConsentState, CookieConsentUpdate

router = APIRouter()


def _encode_consent(state: CookieConsentState) -> str:
    raw = json.dumps(state.model_dump(), separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_consent(raw: str) -> CookieConsentState | None:
    try:
        pad = "=" * (-len(raw) % 4)
        data = base64.urlsafe_b64decode(raw + pad)
        obj: dict[str, Any] = json.loads(data.decode("utf-8"))
        return CookieConsentState.model_validate(obj)
    except Exception:
        return None


@router.get(
    "/cookies",
    response_model=CookieConsentState | None,
    summary="Read saved cookie consent",
    description="Returns the current consent object from the `mo_cookie_consent` cookie, or `null` if unset.",
    responses={200: {"description": "Current consent or null"}},
)
async def get_cookie_consent(request: Request) -> CookieConsentState | None:
    raw = request.cookies.get(CookieConsentConstants.COOKIE_NAME)
    if not raw:
        return None
    return _decode_consent(raw)


@router.post(
    "/cookies",
    response_model=CookieConsentState,
    status_code=status.HTTP_200_OK,
    summary="Save cookie consent",
    description=(
        "Applies **accept_all**, **reject_optional**, or **save** with toggles. "
        "Sets `mo_cookie_consent` and returns the saved state for immediate UI updates."
    ),
)
async def set_cookie_consent(request: Request, body: CookieConsentUpdate) -> Response:
    state = CookieConsentState.from_action(body)
    token = _encode_consent(state)
    secure = request.url.scheme == "https"
    payload = state.model_dump()
    response = JSONResponse(content=payload)
    response.set_cookie(
        key=CookieConsentConstants.COOKIE_NAME,
        value=token,
        max_age=CookieConsentConstants.MAX_AGE_SECONDS,
        path="/",
        httponly=False,
        samesite="lax",
        secure=secure,
    )
    return response


@router.delete(
    "/cookies",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear cookie consent (testing / withdraw)",
    description="Removes the consent cookie so the banner can show again.",
)
async def delete_cookie_consent() -> Response:
    r = Response(status_code=status.HTTP_204_NO_CONTENT)
    r.delete_cookie(CookieConsentConstants.COOKIE_NAME, path="/")
    return r
