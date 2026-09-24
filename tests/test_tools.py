import asyncio
import pytest

from app.tools import get_transactions_summary, get_category_totals, get_top_expenses


@pytest.mark.asyncio
async def test_tools_no_data(monkeypatch):
    # Ensure DB returns empty lists by mocking async_session execute flows if needed.
    # For now, just call the functions — they should return numeric zeros when no rows.
    summary = await get_transactions_summary(period_days=1)
    assert isinstance(summary, dict)
    assert "total_income" in summary

    cats = await get_category_totals(period_days=1)
    assert isinstance(cats, list)

    top = await get_top_expenses(limit=3, period_days=1)
    assert isinstance(top, list)
