import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator

# AI service is read-only — no search_path override, uses fully-qualified schema names in SQL
engine = create_async_engine(
    os.environ["DATABASE_URL"],
    echo=False,
    pool_size=5,
    max_overflow=10,
)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
