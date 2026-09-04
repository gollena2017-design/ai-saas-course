import asyncio

from .db import engine
from .models import Base


async def create_tables() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    print("Database tables created successfully")


if __name__ == "__main__":
    asyncio.run(create_tables())