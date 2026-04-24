"""Database connection pool and initialization for ai-agent-lite.

Reuses the existing QDUOJ PostgreSQL instance with a separate schema.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.db_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _apply_schema(base):
    """Set schema on all tables before create_all."""
    base.metadata.schema = settings.db_schema


async def init_db() -> None:
    """Create schema and tables if they do not exist."""
    from app.models.orm import Base

    # Set schema BEFORE create_all
    _apply_schema(Base)

    # Ensure schema exists
    async with engine.begin() as conn:
        import sqlalchemy
        await conn.execute(sqlalchemy.text(f"CREATE SCHEMA IF NOT EXISTS {settings.db_schema}"))
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Dependency: yield an async DB session."""
    async with async_session() as session:
        yield session