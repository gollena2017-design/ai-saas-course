from typing import List, Dict
from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from .db import async_session
from .models import Transaction, Category


async def get_transactions_summary(period_days: int = 30) -> Dict[str, float]:
    """Return total income, total expense and balance for the last `period_days` days."""
    since = date.today() - timedelta(days=period_days)

    async with async_session() as session:
        stmt = select(Transaction).where(Transaction.transaction_date >= since)
        res = await session.execute(stmt)
        txs = res.scalars().all()

    total_income = sum(float(t.amount) for t in txs if t.type == "income")
    total_expense = sum(float(t.amount) for t in txs if t.type == "expense")

    return {"total_income": total_income, "total_expense": total_expense, "balance": total_income - total_expense}


async def get_category_totals(period_days: int = 30, top_n: int = 10) -> List[Dict]:
    """Return category totals for the last `period_days` days, ordered by expense desc."""
    since = date.today() - timedelta(days=period_days)

    async with async_session() as session:
        stmt = (
            select(Category.name, func.sum(Transaction.amount).label("total"))
            .join(Transaction, Transaction.category_id == Category.id)
            .where(Transaction.transaction_date >= since)
            .where(Transaction.type == "expense")
            .group_by(Category.name)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(top_n)
        )

        res = await session.execute(stmt)
        rows = res.all()

    return [{"category": r[0], "total": float(r[1] or 0)} for r in rows]


async def get_top_expenses(limit: int = 5, period_days: int = 90):
    """Return top expense transactions in the last `period_days` days."""
    since = date.today() - timedelta(days=period_days)

    async with async_session() as session:
        stmt = (
            select(Transaction).options(selectinload(Transaction.category))
            .where(Transaction.transaction_date >= since)
            .where(Transaction.type == "expense")
            .order_by(Transaction.amount.desc())
            .limit(limit)
        )

        res = await session.execute(stmt)
        txs = res.scalars().all()

    return [
        {"id": t.id, "date": t.transaction_date.isoformat(), "amount": float(t.amount), "category": (t.category.name if t.category else None), "description": t.description or ""}
        for t in txs
    ]


__all__ = ["get_transactions_summary", "get_category_totals", "get_top_expenses"]
