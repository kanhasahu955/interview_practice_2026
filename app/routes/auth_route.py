from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings
from app.constant.constants import RateLimitRule
from app.db import get_db
from app.deps import get_current_user
from app.middlewares.rate_limit import limiter
from app.modules.auth.model import User
from app.openapi_common import R_401, R_403, R_409, merge_responses
from app.schema.auth import TokenOut, UserCreate, UserPublic
from app.services.auth_service import PASSWORD_TOO_LONG_CODE, PASSWORD_TOO_LONG_MESSAGE, get_auth_service


class AuthRoutes:
    """HTTP surface for auth; wires rate limits and service calls."""

    def __init__(self) -> None:
        self.router = APIRouter()
        self._svc = get_auth_service()
        self._settings = get_settings()
        self._register()

    def _register(self) -> None:
        r = self.router
        svc = self._svc
        s = self._settings

        @r.post(
            "/register",
            response_model=UserPublic,
            summary="Register a new user",
            description=(
                "### Purpose\n"
                "Onboard a new account for the learning platform.\n\n"
                "### Request body\n"
                "JSON matching **UserCreate** (see schema below for every field). "
                "**email** must be new; **password** ≥ 8 characters.\n\n"
                "### What this endpoint does\n"
                "Hashes the password, inserts the user (default **reader** role), returns **UserPublic**.\n\n"
                "### Errors\n"
                "**409** if the email is already registered."
            ),
            responses=merge_responses(R_409),
            response_description="Public user profile (no password or internal fields).",
        )
        @limiter.limit(s.rate_limit_default)
        async def register(
            request: Request,
            body: UserCreate,
            session: AsyncSession = Depends(get_db),
        ) -> User:
            try:
                return await svc.register_user(session, body)
            except ValueError as e:
                if str(e) == "email_taken":
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered") from e
                if str(e) == PASSWORD_TOO_LONG_CODE:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_TOO_LONG_MESSAGE) from e
                raise

        @r.post(
            "/token",
            response_model=TokenOut,
            summary="OAuth2 password login (JWT)",
            description=(
                "### Purpose\n"
                "Exchange email + password for a short-lived **JWT** used on protected routes.\n\n"
                "### Request body (form, not JSON)\n"
                "Content-Type: **application/x-www-form-urlencoded**.\n\n"
                "| Field | Required | Meaning |\n"
                "| --- | --- | --- |\n"
                "| `username` | yes | Your **email** (same as registered) |\n"
                "| `password` | yes | Account password |\n"
                "| `scope` | no | Optional OAuth2 scope string |\n"
                "| `client_id` / `client_secret` | no | Not used by this API |\n\n"
                "### What this endpoint does\n"
                "Validates credentials, checks **is_active**, returns **TokenOut** with **access_token**.\n\n"
                "### After login\n"
                "Call other endpoints with header `Authorization: Bearer <access_token>` or use Swagger **Authorize**.\n\n"
                "### Errors\n"
                "**401** invalid credentials; **403** inactive user."
            ),
            responses=merge_responses(R_401, R_403),
            response_description="Access token and `token_type` (typically `bearer`).",
        )
        @limiter.limit(RateLimitRule.LOGIN)
        async def login(
            request: Request,
            form: Annotated[OAuth2PasswordRequestForm, Depends()],
            session: AsyncSession = Depends(get_db),
        ) -> TokenOut:
            try:
                return await svc.login_token(session, username=form.username, password=form.password)
            except ValueError as e:
                msg = str(e)
                if msg == "invalid_credentials":
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials") from e
                if msg == "inactive":
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user") from e
                if msg == PASSWORD_TOO_LONG_CODE:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_TOO_LONG_MESSAGE) from e
                raise

        @r.get(
            "/me",
            response_model=UserPublic,
            summary="Current authenticated user",
            description=(
                "### Purpose\n"
                "Who am I? Returns the profile for the JWT currently sent.\n\n"
                "### Authentication\n"
                "Requires `Authorization: Bearer <access_token>` from **POST …/auth/token**.\n\n"
                "### What this endpoint does\n"
                "Decodes JWT **sub** (user id), loads the user from DB, returns **UserPublic**.\n\n"
                "### Errors\n"
                "**401** if token missing, invalid, or user inactive."
            ),
            responses=merge_responses(R_401),
            response_description="Public profile for the token subject.",
        )
        async def me(user: User = Depends(get_current_user)) -> User:
            return user
