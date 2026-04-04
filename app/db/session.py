from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings

_s = get_settings()
_async_url = _s.database_url_async
_engine_kw: dict = {"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20}
if _async_url.split("://", 1)[0].startswith("mysql"):
    _engine_kw["connect_args"] = {"charset": "utf8mb4"}

engine: AsyncEngine = create_async_engine(_async_url, **_engine_kw)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def create_db_and_tables() -> None:
    from app.modules import import_all_models

    import_all_models()

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
