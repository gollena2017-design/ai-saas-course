# Repository guide for AI agents

## Architecture

- Backend: FastAPI in `app/`; entry point is `app.api:app`.
- Frontend: React/Vite in `frontend/`.
- Database: Neon PostgreSQL in production; PostgreSQL service in CI.
- AI: Gemini, called only by backend code.
- Production: Render uses `Dockerfile.render` and `render.yaml`.

## Local commands

```bash
uvicorn app.api:app --reload
npm run dev --prefix frontend
python scripts/preflight.py
```

## Production contract

- Render starts FastAPI on `0.0.0.0` and the port supplied in `PORT`.
- The React production build is `frontend/dist` and is built by `Dockerfile.render`.
- Health endpoint: `GET /healthz` returns HTTP 200.
- Do not modify `Dockerfile.render`, `render.yaml`, or deployment settings unless
  the task explicitly concerns deployment.

## Security

Never commit `.env`, `DATABASE_URL`, `GEMINI_API_KEY`, `BOT_TOKEN`,
`ADMIN_PASSWORD`, passwords, tokens, or private keys. Keep only `.env.example`
in Git. The LLM must not receive secrets or arbitrary SQL access.

## Git workflow

- Work in a task-specific `feature/`, `fix/`, or `maintenance/` branch, never
  directly in `main`.
- Before committing, inspect `git diff` and run `python scripts/preflight.py`.
- Report changed files and the result of preflight. Push a branch and use a Pull
  Request; merge only after GitHub Actions passes.
