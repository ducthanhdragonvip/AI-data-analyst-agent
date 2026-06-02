import asyncio

from sqlalchemy import text

from app.database import Base, engine
from app import models  # noqa: F401


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE datasets ALTER COLUMN table_schema DROP NOT NULL"))
        await conn.execute(text("ALTER TABLE datasets ALTER COLUMN table_name DROP NOT NULL"))


if __name__ == "__main__":
    asyncio.run(init_db())
