from datetime import date
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .db import async_session, engine
from .models import Category, Transaction
from .llm import call_gemini_analyze, extract_json_from_text
import logging
import asyncio
import time
import anyio
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
from .settings import AGGREGATE_TX_THRESHOLD
from .models import ChatThread, ChatMessage
from .tools import get_transactions_summary, get_top_expenses, get_category_totals
import json as _json
from typing import Any

logger = logging.getLogger(__name__)

from sqlalchemy.exc import InterfaceError as SAInterfaceError


async def _commit_with_retry(session, retries: int = 8, delay: float = 0.05):
    for attempt in range(retries):
        try:
            await session.commit()
            return
        except Exception as e:
            msg = str(e).lower()
            transient = (
                isinstance(e, SAInterfaceError)
                or "another operation is in progress" in msg
                or "task .* got future attached to a different loop" in msg
            )
            try:
                await session.rollback()
            except Exception:
                pass

            if not transient or attempt + 1 == retries:
                logging.exception("Commit failed and will not retry")
                raise

            backoff = delay * (1 + attempt * 0.5)
            logging.warning("Transient DB commit error, retrying in %.3fs (attempt %d)", backoff, attempt + 1)
            await asyncio.sleep(backoff)


async def _execute_with_retry(session, statement, retries: int = 8, delay: float = 0.05):
    for attempt in range(retries):
        try:
            return await session.execute(statement)
        except Exception as e:
            msg = str(e).lower()
            transient = (
                isinstance(e, SAInterfaceError)
                or "another operation is in progress" in msg
                or "task .* got future attached to a different loop" in msg
            )
            try:
                await session.rollback()
            except Exception:
                pass

            if not transient or attempt + 1 == retries:
                logging.exception("Execute failed and will not retry")
                raise

            backoff = delay * (1 + attempt * 0.5)
            logging.warning("Transient DB execute error, retrying in %.3fs (attempt %d)", backoff, attempt + 1)
            await asyncio.sleep(backoff)


def _log_db_event(event: str, **kwargs):
    ts = time.time()
    info = {"t": ts, **kwargs}
    logging.debug("DB_EVENT %s %s", event, info)


# Serialize critical DB operations to avoid asyncpg "another operation in progress"
# Use anyio.Lock which works across different event loops/threads used by TestClient
_db_op_lock: anyio.Lock | None = None

def _ensure_db_lock():
    global _db_op_lock
    if _db_op_lock is None:
        _db_op_lock = anyio.Lock()
    return _db_op_lock

# Allowed tools and simple arg schemas for validation
TOOL_SPECS = {
    "get_transactions_summary": {"period_days": int},
    "get_top_expenses": {"limit": int, "period_days": int},
    "get_category_totals": {"period_days": int, "top_n": int},
}


def validate_tool_args(tool_name: str, args: dict) -> None:
    spec = TOOL_SPECS.get(tool_name)
    if spec is None:
        raise ValueError(f"unknown tool {tool_name}")

    # only allow keys present in spec
    for k in args.keys():
        if k not in spec:
            raise ValueError(f"unexpected arg '{k}' for tool {tool_name}")

    # type checks for provided args
    for k, t in spec.items():
        if k in args and args[k] is not None:
            if not isinstance(args[k], t):
                # allow numeric strings that can be cast to int
                if t is int and isinstance(args[k], str) and args[k].isdigit():
                    args[k] = int(args[k])
                else:
                    raise ValueError(f"arg '{k}' must be {t.__name__}")

    limits = {"period_days": (1, 3660), "limit": (1, 20), "top_n": (1, 20)}
    for key, (minimum, maximum) in limits.items():
        if key in args and not minimum <= args[key] <= maximum:
            raise ValueError(f"arg '{key}' must be between {minimum} and {maximum}")
from sqlalchemy import insert


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
    # to reduce token usage. Threshold can be controlled via `AGGREGATE_TX_THRESHOLD`.
    mode = "aggregated" if len(txs) > AGGREGATE_TX_THRESHOLD else "full"

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


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2_000)
    thread_id: int | None = Field(default=None, gt=0)


@app.post("/api/ai/chat")
async def ai_chat_endpoint(req: ChatRequest):
    """Continue a conversation using persisted short-term memory and read-only tools."""
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Message must not be blank")

    async with async_session() as session:
        if req.thread_id is None:
            thread = ChatThread()
            session.add(thread)
            await session.flush()
        else:
            thread = await session.get(ChatThread, req.thread_id)
            if thread is None:
                raise HTTPException(status_code=404, detail="Thread not found")

        thread_id = thread.id
        session.add(ChatMessage(thread_id=thread_id, role="user", content=message))
        await session.commit()

    async with async_session() as session:
        result = await session.execute(
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
            .limit(20)
        )
        recent = list(reversed(result.scalars().all()))

    conversation = [{"role": item.role, "content": item.content} for item in recent]
    tool_data = {
        "summary": await get_transactions_summary(),
        "categories": await get_category_totals(),
        "top_expenses": await get_top_expenses(limit=3),
    }
    prompt_input = {"conversation": conversation, "tool_data": tool_data, "tool_result": None}

    try:
        loop = asyncio.get_running_loop()
        call = functools.partial(call_gemini_analyze, prompt_input, mode="aggregated")
        res = await asyncio.wait_for(loop.run_in_executor(None, call), timeout=45)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="LLM request timed out")
    except Exception as exc:
        logger.exception("Chat LLM request failed")
        raise HTTPException(status_code=502, detail="AI service is unavailable") from exc

    if isinstance(res, dict) and res.get("error"):
        raise HTTPException(status_code=502, detail="AI service is unavailable")
    raw_text = res.get("raw") if isinstance(res, dict) else ""

    # Try to parse a tool call from the LLM response
    parsed_llm = extract_json_from_text(raw_text) if raw_text else None
    tool_result: Any | None = None
    if parsed_llm and isinstance(parsed_llm, dict) and parsed_llm.get("tool_call"):
        tc = parsed_llm["tool_call"]
        tool_name = tc.get("name")
        tool_args = tc.get("args", {}) or {}

        # validate args
        try:
            validate_tool_args(tool_name, tool_args)
        except Exception as e:
            logger.warning("Tool args validation failed: %s", e)
            tool_result = {"error": f"invalid tool args: {e}"}
        else:
            try:
                # tool functions may perform DB reads; run them fully before calling LLM again
                if tool_name == "get_transactions_summary":
                    tool_result = await get_transactions_summary(**tool_args)
                elif tool_name == "get_top_expenses":
                    tool_result = await get_top_expenses(**tool_args)
                elif tool_name == "get_category_totals":
                    tool_result = await get_category_totals(**tool_args)
                else:
                    tool_result = {"error": f"unknown tool {tool_name}"}
            except Exception as e:
                logger.exception("Tool execution error for %s", tool_name)
                tool_result = {"error": f"tool error: {e}"}

        # call LLM again providing the tool result
        followup_input = {
            "conversation": conversation,
            "tool_data": tool_data,
            "tool_result": tool_result,
        }

        try:
            call_fn2 = functools.partial(call_gemini_analyze, followup_input, mode="aggregated")
            res2 = await asyncio.wait_for(loop.run_in_executor(None, call_fn2), timeout=45)
        except asyncio.TimeoutError:
            raise HTTPException(status_code=504, detail="LLM follow-up timed out")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"LLM follow-up error: {e}")

        raw_text = res2.get("raw") if isinstance(res2, dict) else None
    answer = raw_text or "Не вдалося сформувати відповідь. Спробуйте ще раз."
    checkpoint_messages = conversation + [{"role": "assistant", "content": answer}]
    new_checkpoint = {
        "messages": checkpoint_messages,
        "last_tool": tool_result,
        "last_user": message,
        "last_assistant": answer,
    }

    async with async_session() as session:
        thread = await session.get(ChatThread, thread_id)
        if thread is None:  # defensive: a thread might have been removed concurrently
            raise HTTPException(status_code=404, detail="Thread not found")
        session.add(ChatMessage(thread_id=thread_id, role="assistant", content=answer))
        thread.checkpoint = _json.dumps(new_checkpoint, ensure_ascii=False)
        await session.commit()

    return {"thread_id": thread_id, "answer": answer, "checkpoint": new_checkpoint}


@app.get("/api/ai/thread/{thread_id}")
async def get_thread(thread_id: int):
    async with async_session() as session:
        th = await session.get(ChatThread, thread_id)
        if th is None:
            raise HTTPException(status_code=404, detail="Thread not found")

        result = await session.execute(
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread_id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        )
        return {
            "thread_id": th.id,
            "messages": [{"role": item.role, "content": item.content} for item in result.scalars()],
        }
