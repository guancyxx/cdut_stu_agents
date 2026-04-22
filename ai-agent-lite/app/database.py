"""
Database connection pool and initialization for ai-agent-lite.
Reuses the existing QDUOJ PostgreSQL instance with a separate schema.
"""
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_SCHEMA = os.getenv("LITE_DB_SCHEMA", "ai_agent")
_DATABASE_URL = os.getenv(
    "LITE_DATABASE_URL",
    "postgresql+asyncpg://onlinejudge:onlinejudge@oj-postgres:5432/onlinejudge",
)

engine = create_async_engine(
    _DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def _apply_schema(base):
    """Set schema on all tables before create_all."""
    base.metadata.schema = _SCHEMA


async def init_db() -> None:
    """Create schema and tables if they do not exist."""
    from app.models import Base

    # Set schema BEFORE create_all
    _apply_schema(Base)

    # Ensure schema exists
    async with engine.begin() as conn:
        import sqlalchemy
        await conn.execute(sqlalchemy.text(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA}"))
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Dependency: yield an async DB session."""
    async with async_session() as session:
        yield session