import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv


load_dotenv()


async def start_command(message: Message) -> None:
    """Відповідає на команду /start."""
    await message.answer(
        "Вітаю! 👋\n"
        "Я навчальний Telegram-бот на aiogram."
    )


async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Задайте BOT_TOKEN у файлі .env")

    dispatcher = Dispatcher()
    dispatcher.message.register(start_command, CommandStart())

    async with Bot(token=token) as bot:
        await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
