import asyncio
import sys
import logging

from .db import test_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


async def main() -> int:
    logger.info("Checking database connection...")
    ok = await test_connection()
    if ok:
        logger.info("Database is available")
        return 0
    else:
        logger.error("Database is NOT available")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
