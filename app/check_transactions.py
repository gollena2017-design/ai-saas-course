import asyncio

from sqlalchemy import select

from .db import async_session
from .models import Transaction


async def main() -> None:
    async with async_session() as session:
        result = await session.execute(
            select(Transaction).order_by(Transaction.id.desc())
        )

        transactions = result.scalars().all()

    if not transactions:
        print("No transactions found")
        return

    print("Transactions:")

    for transaction in transactions:
        print(
            f"id={transaction.id} | "
            f"user_id={transaction.user_id} | "
            f"category_id={transaction.category_id} | "
            f"amount={transaction.amount} | "
            f"description={transaction.description} | "
            f"created_at={transaction.created_at}"
        )


if __name__ == "__main__":
    asyncio.run(main())