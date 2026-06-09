try:
    # SQLAlchemy 2.0+
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    _use_new_sessionmaker = True
except ImportError:
    # SQLAlchemy 1.4 fallback
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    _use_new_sessionmaker = False

from app.core.config import settings

# Create database engine
connect_args = {"check_same_thread": False} if settings.async_database_url.startswith("sqlite") else {}

engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    future=True,
    connect_args=connect_args,
)

if _use_new_sessionmaker:
    AsyncSessionLocal = async_sessionmaker(  # type: ignore[assignment]
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
else:
    AsyncSessionLocal = sessionmaker(  # type: ignore[assignment]
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

async def get_db():
    """Dependency generator for database sessions in FastAPI routes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
