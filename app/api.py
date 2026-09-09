from fastapi import FastAPI
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .db import async_session
from .models import Transaction

app = FastAPI(title="Finance SaaS API")


@app.get("/")
async def root():
    return {"message": "Finance API is running"}


@app.get("/api/transactions")
async def get_transactions():
    async with async_session() as session:
        result = await session.execute(
            select(Transaction)
            .options(selectinload(Transaction.category))
            .order_by(Transaction.created_at.desc())
        )

        transactions = result.scalars().all()

        return [
            {
                "date": transaction.created_at,
                "type": "expense",
                "amount": float(transaction.amount),
                "category": (
                    transaction.category.name
                    if transaction.category
                    else "Без категорії"
                ),
                "description": transaction.description or "",
            }
            for transaction in transactions
        ]


@app.get("/api/summary")
async def get_summary():
    async with async_session() as session:
        result = await session.execute(select(Transaction))
        transactions = result.scalars().all()

        total_expense = sum(
            float(transaction.amount)
            for transaction in transactions
        )

        total_income = 0.0

        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": total_income - total_expense,
        }