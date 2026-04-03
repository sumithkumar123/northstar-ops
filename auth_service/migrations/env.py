import os
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy import text
from alembic import context

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from models import Base

target_metadata = Base.metadata
DATABASE_URL = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+asyncpg://", 1)
DB_SCHEMA = os.environ.get("DB_SCHEMA", "auth")


async def run_migrations_online():
    engine = create_async_engine(
        DATABASE_URL,
        poolclass=NullPool,
        connect_args={"server_settings": {"search_path": DB_SCHEMA}},
    )
    async with engine.connect() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
        await conn.commit()
        await conn.run_sync(
            lambda sync_conn: context.configure(
                connection=sync_conn,
                target_metadata=target_metadata,
                include_schemas=True,
                version_table_schema=DB_SCHEMA,
            )
        )
        async with conn.begin():
            await conn.run_sync(lambda _: context.run_migrations())
    await engine.dispose()


asyncio.run(run_migrations_online())
