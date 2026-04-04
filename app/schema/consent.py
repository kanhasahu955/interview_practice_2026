"""Cookie / privacy consent payloads (browser banner + API)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class CookieConsentUpdate(BaseModel):
    """Body for POST — preset actions or custom toggles."""

    model_config = {"json_schema_extra": {"examples": [{"action": "accept_all"}, {"action": "reject_optional"}]}}

    action: Literal["accept_all", "reject_optional", "save"] = Field(
        default="save",
        description="`accept_all` / `reject_optional` override toggles; `save` uses `analytics` and `functional`.",
    )
    analytics: bool = Field(default=False, description="Optional analytics / measurement cookies.")
    functional: bool = Field(default=False, description="Optional functional cookies (preferences, UI state).")


class CookieConsentState(BaseModel):
    """Stored consent snapshot (cookie + localStorage + API response)."""

    essential: Literal[True] = Field(True, description="Always true — required for the site to work.")
    analytics: bool = Field(description="User allowed analytics cookies.")
    functional: bool = Field(description="User allowed functional cookies.")
    version: int = Field(default=1, description="Bump when categories change.")
    decided_at: str = Field(description="ISO-8601 UTC timestamp when the user decided.")

    @classmethod
    def from_action(cls, body: CookieConsentUpdate) -> CookieConsentState:
        if body.action == "accept_all":
            analytics = functional = True
        elif body.action == "reject_optional":
            analytics = functional = False
        else:
            analytics = body.analytics
            functional = body.functional
        return cls(
            analytics=analytics,
            functional=functional,
            decided_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )
