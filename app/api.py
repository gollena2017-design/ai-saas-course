from datetime import date, datetime
from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .db import async_session, engine
from .models import AIActionAuditLog, Category, ChatMessage, ChatThread, PendingAction, Transaction
from .llm import call_gemini_analyze, extract_json_from_text
import logging
import asyncio
import time
import anyio
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


class CreateTransactionPayload(BaseModel):
    """Strict backend contract for the single allowed action tool."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    type: str
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    category: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    date: date

    def validated_type(self) -> str:
        transaction_type = self.type.lower()
        if transaction_type not in {"income", "expense"}:
            raise ValueError("type must be income or expense")
        return transaction_type


def _serialize_action(action: PendingAction) -> dict[str, Any]:
    return {
        "action_id": action.id,
        "thread_id": action.thread_id,
        "action_type": action.action_type,
        "payload": _json.loads(action.payload),
        "status": action.status,
        "created_at": action.created_at.isoformat(),
    }


async def _write_action_audit(
    session, action: PendingAction, event: str, status: str, detail: str | None = None
) -> None:
    session.add(AIActionAuditLog(
        action_id=action.id,
        thread_id=action.thread_id,
        event=event,
        status=status,
        detail=detail,
    ))


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
    prompt_input = {
        "conversation": conversation,
        "tool_data": tool_data,
        "tool_result": None,
        "today": date.today().isoformat(),
    }

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
    proposed_payload: CreateTransactionPayload | None = None
    if isinstance(parsed_llm, dict) and parsed_llm.get("action_proposal"):
        proposal = parsed_llm["action_proposal"]
        if proposal.get("action_type") != "create_transaction":
            raw_text = "Я можу лише підготувати створення однієї операції для підтвердження."
        else:
            try:
                proposed_payload = CreateTransactionPayload.model_validate(proposal.get("payload", {}))
                proposed_payload.validated_type()
                raw_text = proposal.get("reply") or "Я підготував дію. Перевірте дані й підтвердьте її."
            except (ValidationError, ValueError):
                raw_text = "Не можу підготувати дію: перевірте суму, тип, категорію та дату."
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

    pending_action: PendingAction | None = None
    async with async_session() as session:
        thread = await session.get(ChatThread, thread_id)
        if thread is None:  # defensive: a thread might have been removed concurrently
            raise HTTPException(status_code=404, detail="Thread not found")
        session.add(ChatMessage(thread_id=thread_id, role="assistant", content=answer))
        thread.checkpoint = _json.dumps(new_checkpoint, ensure_ascii=False)
        if proposed_payload is not None:
            pending_action = PendingAction(
                thread_id=thread_id,
                action_type="create_transaction",
                payload=proposed_payload.model_dump_json(),
                status="pending",
            )
            session.add(pending_action)
            await session.flush()
            await _write_action_audit(session, pending_action, "created", "pending")
        await session.commit()

    return {
        "thread_id": thread_id,
        "answer": answer,
        "checkpoint": new_checkpoint,
        "pending_action": _serialize_action(pending_action) if pending_action else None,
    }


@app.post("/api/ai/actions/{action_id}/confirm")
async def confirm_pending_action(action_id: int):
    """Execute the single allowed action only after explicit confirmation."""
    async with async_session() as session:
        action = await session.get(PendingAction, action_id)
        if action is None:
            raise HTTPException(status_code=404, detail="Action not found")
        if action.status != "pending":
            raise HTTPException(status_code=409, detail="Action is no longer pending")
        if action.action_type != "create_transaction":
            raise HTTPException(status_code=400, detail="Action type is not allowed")

        try:
            payload = CreateTransactionPayload.model_validate_json(action.payload)
            transaction_type = payload.validated_type()
        except (ValidationError, ValueError) as exc:
            action.status = "failed"
            action.error = "Stored payload failed validation"
            await _write_action_audit(session, action, "validation_failed", "failed")
            await session.commit()
            raise HTTPException(status_code=422, detail="Action payload is invalid") from exc

        category_result = await session.execute(
            select(Category).where(Category.name == payload.category)
        )
        category = category_result.scalar_one_or_none()
        if category is None:
            category = Category(name=payload.category)
            session.add(category)
            await session.flush()

        # Prevent a double click/retry from creating an identical record.
        duplicate = await session.execute(
            select(Transaction.id)
            .where(Transaction.type == transaction_type)
            .where(Transaction.amount == payload.amount)
            .where(Transaction.category_id == category.id)
            .where(Transaction.transaction_date == payload.date)
            .where(Transaction.description == payload.description)
            .limit(1)
        )
        if duplicate.scalar_one_or_none() is not None:
            action.status = "failed"
            action.error = "Duplicate transaction"
            await _write_action_audit(session, action, "duplicate_rejected", "failed")
            await session.commit()
            raise HTTPException(status_code=409, detail="Duplicate transaction")

        transaction = Transaction(
            category_id=category.id,
            type=transaction_type,
            transaction_date=payload.date,
            amount=payload.amount,
            description=payload.description,
        )
        session.add(transaction)
        action.status = "confirmed"
        action.confirmed_at = datetime.utcnow()
        await session.flush()
        await _write_action_audit(session, action, "confirmed", "confirmed")
        await session.commit()

        return {
            "action": _serialize_action(action),
            "transaction": {
                "id": transaction.id,
                "type": transaction.type,
                "amount": float(transaction.amount),
                "category": category.name,
                "date": transaction.transaction_date.isoformat(),
                "description": transaction.description or "",
            },
        }


@app.post("/api/ai/actions/{action_id}/cancel")
async def cancel_pending_action(action_id: int):
    async with async_session() as session:
        action = await session.get(PendingAction, action_id)
        if action is None:
            raise HTTPException(status_code=404, detail="Action not found")
        if action.status != "pending":
            raise HTTPException(status_code=409, detail="Action is no longer pending")

        action.status = "cancelled"
        action.cancelled_at = datetime.utcnow()
        await _write_action_audit(session, action, "cancelled", "cancelled")
        await session.commit()
        return {"action": _serialize_action(action)}


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
