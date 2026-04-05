"""Application settings; loaded from repo-root `.env` and environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(
        default="My Application",
        description="Product name: OpenAPI title, startup/access log application=…",
    )
    service_display_name: str = Field(
        default="",
        description="Optional override for log application=…; empty uses app_name.",
    )
    api_v1_prefix: str = "/api/v1"

    # Repo-relative directories (under project root)
    static_dir: str = "static"
    templates_dir: str = "templates"
    media_dir: str = "media"
    upload_dir: str = "upload"
    logs_dir: str = "logs"
    topics_dir: str = "topics"

    database_url: str = Field(
        default="mysql+pymysql://root:changeme@localhost:3306/auto_forge",
        description=(
            "Sync-style URL; runtime uses database_url_async. "
            "MySQL: mysql+pymysql or mysql+aiomysql. "
            "Postgres / Supabase: postgresql+psycopg2://… (Supabase: deploy/supabase/README.md). "
            "Hosts *.supabase.co get TLS for asyncpg unless ssl/sslmode is already in the URL."
        ),
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url_async(self) -> str:
        u = self.database_url.strip()
        if "+psycopg2" in u:
            return u.replace("postgresql+psycopg2", "postgresql+asyncpg", 1)
        if u.startswith("postgresql://"):
            return u.replace("postgresql://", "postgresql+asyncpg://", 1)
        if "+pymysql" in u:
            return u.replace("mysql+pymysql", "mysql+aiomysql", 1)
        if u.startswith("mysql://"):
            return u.replace("mysql://", "mysql+aiomysql://", 1)
        # Already async (e.g. mysql+aiomysql://..., postgresql+asyncpg://...)
        return u

    jwt_secret_key: str = Field(default="change-me-in-production-use-openssl-rand-hex-32")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    bcrypt_rounds: int = 12
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080,http://127.0.0.1:8000",
    )
    rate_limit_default: str = "60/minute"

    seed_admin_email: str | None = None
    seed_admin_password: str | None = None

    uvicorn_host: str = "0.0.0.0"
    uvicorn_port: int = 8000

    log_level: str = "INFO"

    # Logging behaviour (all timestamps use Asia/Kolkata in formatters)
    log_compact: bool = Field(
        default=True,
        description="Short logs: startup summary, one line per HTTP request. False = verbose Rich panels.",
    )
    log_config_banner: bool = Field(
        default=False,
        description="Dump all settings (only when log_compact=false).",
    )
    log_lifecycle: bool = Field(
        default=True,
        description="Application start/stop, server ready, DB status lines.",
    )
    log_http_access: bool = Field(default=True, description="Per-request method, path, status, duration.")
    log_http_slow_warning_ms: float = Field(
        default=2000.0,
        description="Log WARNING for requests slower than this (0 = disabled).",
    )
    log_rich_http_panel: bool = Field(
        default=True,
        description="Console: draw a Rich panel per HTTP request (false = one compact line).",
    )
    log_ws_enabled: bool = Field(
        default=True,
        description="WebSocket /ws/logs streams the same formatted lines as logs/app.log. Disable on untrusted networks.",
    )
    api_expose_internal_errors: bool = Field(
        default=False,
        description="If true, JSON error responses may include a `debug` field (unsafe in production).",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def project_root(self) -> Path:
        return _PROJECT_ROOT

    @computed_field  # type: ignore[prop-decorator]
    @property
    def static_root(self) -> Path:
        return (self.project_root / self.static_dir).resolve()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def templates_root(self) -> Path:
        return (self.project_root / self.templates_dir).resolve()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def media_root(self) -> Path:
        return (self.project_root / self.media_dir).resolve()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def upload_root(self) -> Path:
        return (self.project_root / self.upload_dir).resolve()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def logs_root(self) -> Path:
        return (self.project_root / self.logs_dir).resolve()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def topics_root(self) -> Path:
        return (self.project_root / self.topics_dir).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()


def parse_cors_origins(raw: str) -> list[str]:
    return [o.strip() for o in raw.split(",") if o.strip()]
