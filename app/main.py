import asyncio
import logging
import os
from decimal import Decimal, InvalidOperation

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv
from sqlalchemy import select

from .db import async_session
from .models import Transaction, User


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

load_dotenv()


async def start_command(message: Message) -> None:
    """Відповідає на команду /start."""

    logger.info("received /start command")

    await message.answer(
        "Вітаю! 👋\n"
        "Я навчальний Telegram-бот на aiogram.\n\n"
        "Надішліть /help, щоб побачити доступні команди."
    )


async def help_command(message: Message) -> None:
    """Відповідає на команду /help."""

    logger.info("received /help command")

    await message.answer(
        "ℹ️ Я мінімальний бот навчального проєкту.\n\n"
        "Доступні команди:\n"
        "/start — привітання\n"
        "/help — коротка довідка про бота\n"
        "/expense 120 кава — зберегти витрату"
    )


async def expense_command(message: Message) -> None:
    """Зберігає витрату користувача у базі даних."""

    logger.info("received /expense command")

    if not message.text:
        await message.answer("Формат команди: /expense 120 кава")
        return

    parts = message.text.split(maxsplit=2)

    if len(parts) < 3:
        await message.answer(
            "Неправильний формат.\n"
            "Використовуйте: /expense 120 кава"
        )
        return

    amount_text = parts[1]
    description = parts[2].strip()

    try:
        amount = Decimal(amount_text)
    except InvalidOperation:
        await message.answer(
            "Сума має бути числом.\n"
            "Наприклад: /expense 120 кава"
        )
        return

    if amount <= 0:
        await message.answer("Сума має бути більшою за 0.")
        return

    if not description:
        await message.answer(
            "Додайте опис витрати.\n"
            "Наприклад: /expense 120 кава"
        )
        return

    if not message.from_user:
        await message.answer("Не вдалося визначити користувача Telegram.")
        return

    async with async_session() as session:
        result = await session.execute(
            select(User).where(
                User.telegram_id == message.from_user.id
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
            )

            session.add(user)

            # Потрібно отримати user.id до створення transaction.
            await session.flush()

        transaction = Transaction(
            user_id=user.id,
            category_id=None,
            amount=amount,
            description=description,
        )

        session.add(transaction)
        await session.commit()

    await message.answer(
        f"✅ Витрату збережено.\n"
        f"Сума: {amount:.2f}\n"
        f"Опис: {description}"
    )


async def income_command(message: Message) -> None:
    """Зберігає дохід користувача у базі даних."""

    logger.info("received /income command")

    if not message.text:
        await message.answer("Формат команди: /income 5000 зарплата")
        return

    parts = message.text.split(maxsplit=2)

    if len(parts) < 3:
        await message.answer(
            "Неправильний формат.\n"
            "Використовуйте: /income 5000 зарплата"
        )
        return

    amount_text = parts[1]
    description = parts[2].strip()

    try:
        amount = Decimal(amount_text)
    except InvalidOperation:
        await message.answer(
            "Сума має бути числом.\n"
            "Наприклад: /income 5000 зарплата"
        )
        return

    if amount <= 0:
        await message.answer("Сума має бути більшою за 0.")
        return

    if not description:
        await message.answer(
            "Додайте опис доходу.\n"
            "Наприклад: /income 5000 зарплата"
        )
        return

    if not message.from_user:
        await message.answer("Не вдалося визначити користувача Telegram.")
        return

    async with async_session() as session:
        result = await session.execute(
            select(User).where(
                User.telegram_id == message.from_user.id
            )
        )

        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
            )

            session.add(user)
            await session.flush()

        transaction = Transaction(
            user_id=user.id,
            category_id=None,
            type='income',
            amount=amount,
            description=description,
        )

        session.add(transaction)
        await session.commit()

    await message.answer(
        f"✅ Дохід збережено.\n"
        f"Сума: {amount:.2f}\n"
        f"Опис: {description}"
    )


async def main() -> None:
    token = os.getenv("BOT_TOKEN")

    if not token:
        raise RuntimeError("Задайте BOT_TOKEN у файлі .env")

    logger.info("bot started")

    dispatcher = Dispatcher()

    dispatcher.message.register(start_command, CommandStart())
    dispatcher.message.register(help_command, Command("help"))
    dispatcher.message.register(income_command, Command("income"))
    dispatcher.message.register(expense_command, Command("expense"))

    async with Bot(token=token) as bot:
        await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())