from datetime import datetime

from pydantic import ConfigDict, EmailStr
from sqlmodel import Field, SQLModel

from app.modules.auth.model import UserRole


class UserCreate(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "description": (
                "### Purpose\n"
                "Register a **new user** so they can log in and call protected endpoints.\n\n"
                "### Request body\n"
                "JSON object matching the fields below. **email** must not already exist.\n\n"
                "### What the API does\n"
                "Validates input, hashes **password**, stores the user (default role **reader**), "
                "and returns a **UserPublic** profile (no secrets)."
            ),
        }
    )

    email: EmailStr = Field(description="Unique login email; used as OAuth2 `username` on the token endpoint.")
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Plain password (never stored raw; hashed server-side).",
    )
    full_name: str | None = Field(default=None, description="Optional display name.")


class UserPublic(SQLModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "description": (
                "### Purpose\n"
                "Safe, public view of a user — returned after **register**, from **GET /me**, "
                "and embedded where authors are exposed.\n\n"
                "### Notes\n"
                "Never includes password or internal flags beyond **is_active**."
            ),
        },
    )

    id: int = Field(description="Primary key.")
    email: str = Field(description="Account email.")
    full_name: str | None = Field(description="Display name if set.")
    role: UserRole = Field(description="Access role: reader, author, or admin.")
    is_active: bool = Field(description="Inactive users cannot obtain tokens.")
    created_at: datetime = Field(description="UTC creation timestamp.")


class TokenOut(SQLModel):
    model_config = ConfigDict(
        json_schema_extra={
            "description": (
                "### Purpose\n"
                "Credentials returned by **POST …/auth/token** (OAuth2 password flow).\n\n"
                "### Usage\n"
                "Send **access_token** as header `Authorization: Bearer <token>` on protected routes. "
                "Swagger **Authorize** expects the raw token only."
            ),
        }
    )

    access_token: str = Field(description="JWT to send as `Authorization: Bearer …`.")
    token_type: str = Field(default="bearer", description="Always `bearer` for this API.")
