from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings
from app.constant.constants import oauth2_token_url
from app.db import get_db
from app.modules.auth.model import User, UserRole
from app.services.auth_service import decode_token

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=oauth2_token_url(get_settings().api_v1_prefix),
    auto_error=False,
)


async def get_current_user_optional(
    session: AsyncSession = Depends(get_db),
    token: str | None = Depends(oauth2_scheme),
) -> User | None:
    if not token:
        return None
    try:
        payload = decode_token(token)
        uid = int(payload["sub"])
    except (ValueError, KeyError, TypeError):
        return None
    r = await session.exec(select(User).where(User.id == uid))
    return r.first()


async def get_current_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def require_roles(*roles: UserRole):
    async def _inner(user: User = Depends(get_current_user)) -> User:
        if user.role == UserRole.admin:
            return user
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return _inner


async def require_author_or_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.author, UserRole.admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Author or admin required")
    return user
