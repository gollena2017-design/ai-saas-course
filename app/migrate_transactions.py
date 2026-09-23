import asyncio

from sqlalchemy import text

from .db import engine


async def migrate() -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                """
                ALTER TABLE transactions
                ADD COLUMN IF NOT EXISTS type VARCHAR(20)
                NOT NULL DEFAULT 'expense'
                """
            )
        )

        await connection.execute(
            text(
                """
                ALTER TABLE transactions
                ADD COLUMN IF NOT EXISTS transaction_date DATE
                """
            )
        )

        await connection.execute(
            text(
                """
                UPDATE transactions
                SET transaction_date = created_at::date
                WHERE transaction_date IS NULL
                """
            )
        )

        await connection.execute(
            text(
                """
                ALTER TABLE transactions
                ALTER COLUMN transaction_date SET NOT NULL
                """
            )
        )

        await connection.execute(
            text(
                """
                ALTER TABLE transactions
                ALTER COLUMN user_id DROP NOT NULL
                """
            )
        )

    print("Transactions migration completed successfully")


if __name__ == "__main__":
    asyncio.run(migrate())