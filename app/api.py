from datetime import date
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .db import async_session
from .models import Category, Transaction
from .llm import call_gemini_analyze, extract_json_from_text
import asyncio
from pydantic import ValidationError
from typing import List


class LLMCatItem(BaseModel):
    name: str
    total: float


class LLMParsedModel(BaseModel):
    summary: str
    categories: List[LLMCatItem]
    risks: List[str]
    recommendations: List[str]
from pydantic import BaseModel
from typing import Any, Dict
import functools


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


class AIAnalyzeRequest(BaseModel):
    limit: int | None = 100
    # future: filters, date ranges, etc.


@app.post("/api/ai/analyze-transactions", response_model=None)
async def analyze_transactions_endpoint(data: AIAnalyzeRequest):
    """Read transactions from DB, call Gemini, return raw structured response."""
    async with async_session() as session:
        stmt = select(Transaction).options(selectinload(Transaction.category)).order_by(Transaction.transaction_date.desc()).limit(data.limit)
        result = await session.execute(stmt)
        transactions = result.scalars().all()

        txs = [
            {
                "id": t.id,
                "date": t.transaction_date.isoformat(),
                "type": t.type,
                "amount": float(t.amount),
                "category": (t.category.name if t.category else None),
                "description": t.description or "",
            }
            for t in transactions
        ]

    # Choose prompt mode: use aggregated mode for larger numbers of transactions
    # to reduce token usage. Threshold chosen empirically (5 transactions).
    mode = "aggregated" if len(txs) > 5 else "full"

    # Call Gemini in a thread to avoid blocking the event loop and DB pool.
    try:
        loop = asyncio.get_running_loop()
        call_fn = functools.partial(call_gemini_analyze, txs, mode=mode)
        call_coro = loop.run_in_executor(None, call_fn)
        res = await asyncio.wait_for(call_coro, timeout=45)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="LLM request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {e}")

    # If helper returned an error tuple/dict, surface it
    if isinstance(res, dict) and res.get("error"):
        raise HTTPException(status_code=502, detail=f"LLM service error: {res.get('error')}")

    # Try to parse structured JSON from the LLM text
    parsed = None
    raw_text = res.get("raw") if isinstance(res, dict) else None
    if raw_text:
        parsed = extract_json_from_text(raw_text)

    if parsed is None:
        # return raw and indicate parsing failed
        return {"ok": True, "llm": {"raw": raw_text, "parsed": None}}

    # Validate with Pydantic
    try:
        validated = LLMParsedModel.parse_obj(parsed)
    except ValidationError as ve:
        return {"ok": True, "llm": {"raw": raw_text, "parsed": parsed, "validation_error": ve.errors()}}

    return {"ok": True, "llm": {"raw": raw_text, "parsed": validated.dict()}}