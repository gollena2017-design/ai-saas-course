Admin manual

- Use the frontend at `/` to add transactions via the form.
- Supported types: `income`, `expense`.
- Filters: `all`, `income`, `expense` using the buttons in the UI.
- To delete an operation, press `Видалити` and confirm the browser prompt.
- Endpoints:
  - `GET /api/transactions?type=all|income|expense`
  - `POST /api/transactions` `{ type, amount, category, description, date }`
  - `DELETE /api/transactions/{id}`
- After create/delete the UI refreshes summary and transactions list automatically.
