"""App-wide constants (paths, header names, defaults)."""


class ApiConstants:
    """API surface defaults; align with `Settings.api_v1_prefix` in config."""

    DEFAULT_V1_PREFIX: str = "/api/v1"
    DOCUMENTS_MOUNT_PATH: str = "/content"
    HEALTH_PATH: str = "/health"
    STATIC_MOUNT_PATH: str = "/static"
    MEDIA_MOUNT_PATH: str = "/media"
    # Markdown / notes under repo `topics/` (not the JSON API `/api/v1/topics`)
    STUDY_TOPICS_MOUNT_PATH: str = "/study/topics"


class HttpHeader:
    REQUEST_ID: str = "X-Request-ID"
    X_CONTENT_TYPE_OPTIONS: str = "X-Content-Type-Options"
    X_FRAME_OPTIONS: str = "X-Frame-Options"
    REFERRER_POLICY: str = "Referrer-Policy"


class RateLimitRule:
    LOGIN: str = "30/minute"


class CookieConsentConstants:
    """Browser cookie written by `POST /api/v1/consent/cookies` (name must stay in sync with front-end)."""

    COOKIE_NAME: str = "mo_cookie_consent"
    MAX_AGE_SECONDS: int = 365 * 24 * 60 * 60


def oauth2_token_url(api_v1_prefix: str) -> str:
    return f"{api_v1_prefix.rstrip('/')}/auth/token"
