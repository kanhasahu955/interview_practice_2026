from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings
from app.modules.auth.model import User, UserRole
from app.schema.auth import TokenOut, UserCreate
from app.utils.concurrency import run_in_thread

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_sync(plain: str) -> str:
    return _pwd.hash(plain)


def _verify_sync(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


class AuthService:
    """JWT + bcrypt; blocking crypto runs in a thread pool."""

    async def hash_password(self, plain: str) -> str:
        return await run_in_thread(_hash_sync, plain)

    async def verify_password(self, plain: str, hashed: str) -> bool:
        return await run_in_thread(_verify_sync, plain, hashed)

    def create_access_token(self, *, subject: str, role: str, expires_delta: timedelta | None = None) -> str:
        s = get_settings()
        expire = datetime.now(UTC) + (
            expires_delta if expires_delta else timedelta(minutes=s.access_token_expire_minutes)
        )
        payload = {"sub": subject, "role": role, "exp": expire}
        return jwt.encode(payload, s.jwt_secret_key, algorithm=s.jwt_algorithm)

    def decode_token(self, token: str) -> dict:
        s = get_settings()
        try:
            return jwt.decode(token, s.jwt_secret_key, algorithms=[s.jwt_algorithm])
        except JWTError as e:
            raise ValueError("invalid token") from e

    async def register_user(self, session: AsyncSession, body: UserCreate) -> User:
        r = await session.exec(select(User).where(User.email == str(body.email)))
        if r.first():
            raise ValueError("email_taken")
        hashed = await self.hash_password(body.password)
        user = User(
            email=str(body.email),
            hashed_password=hashed,
            full_name=body.full_name,
            role=UserRole.learner,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    async def login_token(self, session: AsyncSession, *, username: str, password: str) -> TokenOut:
        r = await session.exec(select(User).where(User.email == username))
        user = r.first()
        if not user:
            raise ValueError("invalid_credentials")
        if not await self.verify_password(password, user.hashed_password):
            raise ValueError("invalid_credentials")
        if not user.is_active:
            raise ValueError("inactive")
        token = self.create_access_token(subject=str(user.id), role=user.role.value)
        return TokenOut(access_token=token)

    async def seed_admin_if_needed(self, session: AsyncSession, *, email: str, password: str) -> None:
        r = await session.exec(select(User).where(User.email == email))
        if r.first():
            return
        hashed = await self.hash_password(password)
        session.add(
            User(
                email=email,
                hashed_password=hashed,
                full_name="Seed Admin",
                role=UserRole.admin,
            )
        )
        await session.commit()


# Decode used from deps synchronously (fast); expose module-level helper using singleton logic
_default_auth: AuthService | None = None


def get_auth_service() -> AuthService:
    global _default_auth
    if _default_auth is None:
        _default_auth = AuthService()
    return _default_auth


def decode_token(token: str) -> dict:
    return get_auth_service().decode_token(token)
