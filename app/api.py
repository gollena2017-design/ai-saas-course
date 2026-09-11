from datetime import date
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .db import async_session
from .models import Category, Transaction


app = FastAPI(title="Finance SaaS API")


class TransactionCreate(BaseModel):
    type: str
    amount: Decimal = Field(gt=0)
    category: str = Field(min_length=1)
    description: str | None = None
    date: date


@app.get("/")
async def root():
    return {"message": "Finance API is running"}


@app.get("/api/transactions")
async def get_transactions(type: str | None = None):
    """Return transactions, optionally filtered by type (income|expense)."""
    allowed = {"income", "expense"}

    if type is not None:
        t = type.strip().lower()
        if t not in allowed and t != "all":
            raise HTTPException(status_code=400, detail="Invalid filter")
        type_filter = None if t == "all" else t
    else:
        type_filter = None

    async with async_session() as session:
        stmt = select(Transaction).options(selectinload(Transaction.category))

        if type_filter:
            stmt = stmt.where(Transaction.type == type_filter)

        stmt = stmt.order_by(Transaction.transaction_date.desc())

        result = await session.execute(stmt)
        transactions = result.scalars().all()

        return [
            {
                "id": transaction.id,
                "date": transaction.transaction_date,
                "type": transaction.type,
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


@app.post("/api/transactions")
async def create_transaction(data: TransactionCreate):
    transaction_type = data.type.strip().lower()

    if transaction_type not in {"income", "expense"}:
        raise HTTPException(
            status_code=400,
            detail="Type must be income or expense",
        )

    category_name = data.category.strip()

    if not category_name:
        raise HTTPException(
            status_code=400,
            detail="Category is required",
        )

    async with async_session() as session:
        category_result = await session.execute(
            select(Category).where(Category.name == category_name)
        )

        category = category_result.scalar_one_or_none()

        if category is None:
            category = Category(name=category_name)
            session.add(category)
            await session.flush()

        transaction = Transaction(
            user_id=None,
            category_id=category.id,
            type=transaction_type,
            transaction_date=data.date,
            amount=data.amount,
            description=(
                data.description.strip()
                if data.description
                else None
            ),
        )

        session.add(transaction)
        await session.commit()
        await session.refresh(transaction)

        return {
            "id": transaction.id,
            "date": transaction.transaction_date,
            "type": transaction.type,
            "amount": float(transaction.amount),
            "category": category.name,
            "description": transaction.description or "",
        }


@app.get("/api/summary")
async def get_summary():
    async with async_session() as session:
        result = await session.execute(select(Transaction))
        transactions = result.scalars().all()

        total_income = sum(
            float(transaction.amount)
            for transaction in transactions
            if transaction.type == "income"
        )

        total_expense = sum(
            float(transaction.amount)
            for transaction in transactions
            if transaction.type == "expense"
        )

        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "balance": total_income - total_expense,
        }



    @app.delete("/api/transactions/{transaction_id}")
    async def delete_transaction(transaction_id: int):
        async with async_session() as session:
            transaction = await session.get(Transaction, transaction_id)

            if transaction is None:
                raise HTTPException(status_code=404, detail="Transaction not found")

            await session.delete(transaction)
            await session.commit()

            return {"status": "deleted"}