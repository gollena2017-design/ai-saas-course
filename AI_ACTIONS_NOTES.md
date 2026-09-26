# Controlled AI actions

## Flow

`AI intent -> pending action -> user confirmation -> backend validation -> Neon -> audit log`

The chat can propose only one action type: `create_transaction`. It never adds a
transaction immediately. The response contains `pending_action`; React renders
its exact payload and provides **Підтвердити** and **Скасувати** buttons.

## API

- `POST /api/ai/chat` returns an optional pending action.
- `POST /api/ai/actions/{action_id}/confirm` validates the stored payload again,
  rejects duplicate operations, then creates the transaction.
- `POST /api/ai/actions/{action_id}/cancel` marks a pending action cancelled.

An action can move out of `pending` only once. Repeated confirm/cancel requests
return `409 Conflict` and do not modify financial data.

## Safety

- The LLM receives no database URL, API keys, SQL, or write access.
- Backend validation forbids extra payload fields and requires a positive amount,
  valid type, non-empty category, and ISO date.
- `pending_actions` stores proposals; `ai_action_audit_logs` stores create,
  confirm, cancel, and validation-failure events without secrets.
