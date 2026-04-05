from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings

# Gunicorn runs multiple workers; each runs FastAPI lifespan → create_all. Serialize DDL.
_SCHEMA_INIT_PG_LOCK_ID = 827_364_215_019
_SCHEMA_INIT_MYSQL_LOCK = "moapril_schema_init"

_s = get_settings()
_async_url = _s.database_url_async
_engine_kw: dict = {"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20}
_scheme = _async_url.split("://", 1)[0].lower()
if "mysql" in _scheme:
    _engine_kw["connect_args"] = {"charset": "utf8mb4"}
elif "postgresql" in _scheme or _scheme.startswith("postgres"):
    # Supabase requires TLS; asyncpg ignores psycopg2-style sslmode in many URLs.
    _low = _async_url.lower()
    if "supabase.co" in _low and "ssl=" not in _low and "sslmode" not in _low:
        _engine_kw["connect_args"] = {"ssl": True}

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


def _async_url_backend(url: str) -> str:
    scheme = url.split("://", 1)[0].lower()
    if "postgresql" in scheme or scheme == "postgres":
        return "postgresql"
    if "mysql" in scheme:
        return "mysql"
    return "other"


async def create_db_and_tables() -> None:
    from app.modules import import_all_models

    import_all_models()

    backend = _async_url_backend(_async_url)

    async with engine.begin() as conn:
        if backend == "postgresql":
            await conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _SCHEMA_INIT_PG_LOCK_ID})
        elif backend == "mysql":
            await conn.execute(text("SELECT GET_LOCK(:name, 120)"), {"name": _SCHEMA_INIT_MYSQL_LOCK})

        await conn.run_sync(SQLModel.metadata.create_all)

        if backend == "mysql":
            await conn.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": _SCHEMA_INIT_MYSQL_LOCK})
