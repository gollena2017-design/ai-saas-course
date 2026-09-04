import asyncio

from sqlalchemy import text

from .db import engine


async def main() -> None:
    query = text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """)

    async with engine.connect() as connection:
        result = await connection.execute(query)

        tables = result.scalars().all()

    print("Tables:")
    for table in tables:
        print(f"- {table}")


if __name__ == "__main__":
    asyncio.run(main())