import asyncio

from sqlalchemy import select

from .db import async_session
from .models import User


async def main() -> None:
    async with async_session() as session:
        result = await session.execute(
            select(User).order_by(User.id.desc())
        )

        users = result.scalars().all()

    if not users:
        print("No users found")
        return

    print("Users:")

    for user in users:
        print(
            f"id={user.id} | "
            f"telegram_id={user.telegram_id} | "
            f"username={user.username} | "
            f"created_at={user.created_at}"
        )


if __name__ == "__main__":
    asyncio.run(main())