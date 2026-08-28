import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dotenv import load_dotenv


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
        "/help — коротка довідка про бота"
    )


async def main() -> None:
    token = os.getenv("BOT_TOKEN")

    if not token:
        raise RuntimeError("Задайте BOT_TOKEN у файлі .env")

    logger.info("bot started")

    dispatcher = Dispatcher()

    dispatcher.message.register(start_command, CommandStart())
    dispatcher.message.register(help_command, Command("help"))

    async with Bot(token=token) as bot:
        await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())