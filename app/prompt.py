from typing import Any, Dict, List
import json


def aggregate_by_category(transactions: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
    """Aggregate expense totals by category and return top_n categories sorted by total."""
    totals: Dict[str, float] = {}
    for t in transactions:
        cat = t.get("category") or "unknown"
        amt = float(t.get("amount") or 0)
        # treat income as negative when aggregating expenses only if needed elsewhere
        totals[cat] = totals.get(cat, 0.0) + amt

    items = [{"name": k, "total": v} for k, v in totals.items()]
    items.sort(key=lambda x: x["total"], reverse=True)
    return items[:top_n]


def build_prompt(transactions: List[Dict[str, Any]], mode: str = "aggregated") -> str:
    """
    Build a strict prompt for the LLM.

    mode: 'aggregated' (default) - pass an aggregated summary of transactions to save tokens
          'full' - include the full transactions JSON

    The prompt requires the model to return a single valid JSON object with the
    contract keys: `summary`, `top_expense_categories`, `risks`, `advice`.

    Important rules embedded in prompt:
    - Use ONLY the provided transactions (or the provided aggregation).
    - Do NOT invent transactions, sums, categories, or facts.
    - Return ONLY a single JSON object (no markdown, no surrounding text).
    - If unable to comply or not enough data, return an empty JSON object: {}.
    - All human-readable values must be in Ukrainian.
    """
    # Header / role
    header = (
        "Ви — асистент для аналізу фінансових операцій. "
        "Отримайте вхідні дані і поверніть строго один валідний JSON-об'єкт згідно контракту."
    )

    # Schema description (in Ukrainian to guide language of output)
    schema = (
        "ЗАВДАННЯ: Поверніть ОДИН JSON з ключами:\n"
        "- summary: короткий підсумок (рядок, українською)\n"
        "- top_expense_categories: масив об'єктів {name: рядок (укр.), total: число}\n"
        "- risks: масив рядків (укр.) — потенційні ризики або підозрілі шаблони\n"
        "- advice: масив рядків (укр.) — практичні рекомендації\n"
    )

    constraints = (
        "ОБОВ'ЯЗКОВО: Використовуйте ТІЛЬКИ передані операції або їх агреговану зведену інформацію. "
        "Не вигадуйте категорій, сум або фактичних тверджень. Якщо даних недостатньо — поверніть {}. "
        "НЕ додавати додаткові ключі, НЕ повертати текст поза JSON, НЕ використовувати маркдаун чи кодові блоки."
    )

    if mode == "full":
        payload = json.dumps(transactions, ensure_ascii=False)
        body = f"Вхідні операції (повний список): {payload}"
    else:
        # aggregated mode: send brief summary per category and counts to reduce tokens
        agg = aggregate_by_category(transactions, top_n=10)
        agg_payload = json.dumps(agg, ensure_ascii=False)
        count = len(transactions)
        body = (
            f"Агрегована інформація: total_transactions={count}; top_categories={agg_payload}."
            " Якщо потрібні деталі — повідомте, але не вигадуйте нічого." 
        )

    # Provide a concrete minimal example to reduce hallucinations and enforce schema
    example_response = (
        '{'
        '"summary": "Короткий підсумок українською", '
        '"top_expense_categories": [{"name": "groceries", "total": 120.5}], '
        '"risks": ["висока частота дрібних витрат"], '
        '"advice": ["зменшити підписок", "переглянути витрати на доставку"]'
        '}'
    )

    # Final strict instruction in Ukrainian but keep schema keys English for frontend mapping
    final = (
        header
        + "\n"
        + schema
        + "\n"
        + constraints
        + "\n"
        + body
        + "\n"
        + "ДОДАТКОВО: Поверніть числові підсумки як числа з максимум двома десятковими (round to 2 decimals). "
        + "Обмежте `top_expense_categories` до максимум 5 елементів. Обмежте довжину `risks` і `advice` до максимум 5 рядків кожен. "
        + "Приклад очікуваної відповіді (використовуйте лише як приклад структури, не копіюйте тексти): "
        + example_response
        + "\nВІДПОВІДЬ: Поверніть тільки один валідний JSON-об'єкт згідно вказаної схеми. Якщо не можете — поверніть {}."
    )

    return final
