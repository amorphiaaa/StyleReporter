from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


def create_engine() -> AsyncEngine:
    """Create the future database engine; no connection is opened at import time."""
    return create_async_engine(get_settings().database_url, pool_pre_ping=True)


def create_session_factory(
    engine: AsyncEngine | None = None,
) -> async_sessionmaker[AsyncSession]:
    """Create a future request-scoped session factory."""
    return async_sessionmaker(engine or create_engine(), expire_on_commit=False)
