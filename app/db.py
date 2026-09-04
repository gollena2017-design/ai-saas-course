from __future__ import annotations

import os
import ssl
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("Set DATABASE_URL in .env")


# Convert PostgreSQL URL to SQLAlchemy asyncpg format.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql+asyncpg://",
        1,
    )
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+asyncpg://",
        1,
    )


# Neon may add libpq-specific query parameters such as:
# ?sslmode=require&channel_binding=require
# asyncpg does not accept these parameters directly,
# so remove them from the URL.
url_parts = urlsplit(DATABASE_URL)

query_params = [
    (key, value)
    for key, value in parse_qsl(url_parts.query)
    if key not in {"sslmode", "channel_binding"}
]

DATABASE_URL = urlunsplit(
    (
        url_parts.scheme,
        url_parts.netloc,
        url_parts.path,
        urlencode(query_params),
        url_parts.fragment,
    )
)


# Neon requires an encrypted SSL/TLS connection.
ssl_context = ssl.create_default_context()

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args={
        "ssl": ssl_context,
    },
)

async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def test_connection() -> bool:
    """Check database availability using SELECT 1."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        return True

    except Exception as exc:
        print(f"Database error: {type(exc).__name__}: {exc}")
        return False


__all__ = [
    "engine",
    "async_session",
    "test_connection",
]