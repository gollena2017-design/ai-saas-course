AI Prompt notes

- Purpose: make LLM prompt stricter, more token-efficient, and Ukrainian-friendly.
- New file: `app/prompt.py` with `build_prompt()` and `aggregate_by_category()` helpers.
- Modes supported: `aggregated` (default) and `full`.
- Aggregated mode sends top categories and count to reduce tokens.
- Requirements enforced by prompt:
  - Only use provided data.
  - Do not invent facts, categories, amounts.
  - Return one valid JSON object only.
  - If insufficient data, return {}.
- Testing: `scripts/prompt_token_test.py` uses `tiktoken` to compare token counts.
- Next steps: run token tests on multiple real-world samples and refine schema if needed.
