import logging
import re
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None

_PASSWORD_RE = re.compile(r"://[^:]+:([^@]+)@")


def _mask_url(url: str) -> str:
    """Replace password in a database URL with '***'."""
    return _PASSWORD_RE.sub(lambda m: m.group(0).replace(m.group(1), "***"), url)


async def init_db(database_url: str) -> None:
    """Create the async engine and session factory.

    Schema creation is handled by Alembic migrations (``alembic upgrade head``).
    Tests may call ``Base.metadata.create_all`` directly for speed.
    """
    global _engine, _session_factory
    _engine = create_async_engine(database_url)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    logger.info("Database engine initialized: %s", _mask_url(database_url))


async def close_db() -> None:
    """Dispose the engine and reset module state."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        logger.info("Database engine disposed")
    _engine = None
    _session_factory = None


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the session factory for use outside of FastAPI dependencies."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized — call init_db() first")
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized — call init_db() first")
    async with _session_factory() as session:
        yield session
