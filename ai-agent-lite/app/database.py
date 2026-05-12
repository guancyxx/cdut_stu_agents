"""Database connection pool and initialization for ai-agent-lite.

Uses the dedicated cdut-postgres instance with a separate schema.
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
    from app.models.submission import Submission  # noqa: F401 — ensure table registered
    from app.models.local_user import LocalUser  # noqa: F401 — ensure table registered

    _apply_schema(Base)

    async with engine.begin() as conn:
        import sqlalchemy
        await conn.execute(sqlalchemy.text(f"CREATE SCHEMA IF NOT EXISTS {settings.db_schema}"))
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Dependency: yield an async DB session."""
    async with async_session() as session:
        yield session
