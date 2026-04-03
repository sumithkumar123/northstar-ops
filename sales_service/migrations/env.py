import os, asyncio, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from alembic import context
from models import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
DATABASE_URL = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+asyncpg://", 1)
DB_SCHEMA = os.environ.get("DB_SCHEMA", "sales")


async def run_migrations_online():
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"server_settings": {"search_path": DB_SCHEMA}},
    )
    async with engine.connect() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
        await conn.commit()
        await conn.run_sync(
            lambda c: context.configure(
                connection=c,
                target_metadata=target_metadata,
                include_schemas=True,
                version_table_schema=DB_SCHEMA,
            )
        )
        async with conn.begin():
            await conn.run_sync(lambda _: context.run_migrations())
    await engine.dispose()


asyncio.run(run_migrations_online())
