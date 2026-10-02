# Deploy to Render — Checklist and Steps

This document describes how to deploy the full-stack Finance SaaS to Render.

Production URL: https://ai-saas-course-j85m.onrender.com

Preflight (before creating Render service)

- Ensure `main` branch contains latest code.
- App runs locally: frontend and backend.
- Docker image builds locally with `Dockerfile.render`.
- `.env` is NOT committed to Git.
- `.env.example` contains all required environment variable names.
- Backend has `/health` endpoint returning 200 JSON.
- `Dockerfile.render` exists and builds both frontend and backend.
- `render.yaml` exists if you want to use a Blueprint.

Dockerfile.render notes

- Builds the frontend in a first stage (`node:22-alpine`) and copies `frontend/dist` into the final image.
- Installs Python deps and copies `app/`.
- Entrypoint uses `uvicorn app.api:app --host 0.0.0.0 --port $PORT`.

Render manual steps

1. Open Render dashboard and connect GitHub.
2. New -> Web Service (or Blueprint if `render.yaml` present).
3. Select repository and `main` branch.
4. Runtime: Docker. Set Dockerfile path to `./Dockerfile.render` if not auto-detected.
5. Add environment variables (Database URL, API keys, BOT_TOKEN, ADMIN_PASSWORD, etc.).
6. Health check path: `/health`.
7. Create service and watch deploy logs.

Common failures and how to debug

- Docker build error: inspect the build logs for failing steps.
- npm build error: ensure frontend dependencies are correct locally.
- pip install error: check `requirements.txt` and Python version.
- PORT binding: make sure server listens on `0.0.0.0` and `$PORT` is used.
- Frontend not found: verify `frontend/dist` exists in final image and backend serves static files.

Homework checklist (deliverables)

- Create branch `deploy/render`.
- Create branch `deploy/render` and commit changes:
	```bash
	git checkout -b deploy/render
	git add Dockerfile.render render.yaml .env.example docs/deploy.md app/api.py
	git commit -m "Add Render deployment files: Dockerfile.render, render.yaml, health endpoint, docs"
	git push --set-upstream origin deploy/render
	```
- Add or verify `Dockerfile.render` builds frontend and backend.
- Add `render.yaml`.
- Add `/health` endpoint.
- Update `.env.example`.
- Do NOT commit real secrets.
- Create Render Web Service or Blueprint and configure env vars.
- Complete a successful deploy and verify public URL.
- Add `docs/deploy.md` to repo and open a PR.

Final verification (after deploy)

- Confirm public URL loads and React UI renders.
- Confirm `GET /health` and `GET /healthz` return 200.
- Confirm `GET /assets/*` and `/favicon.svg` return 200.
- Create a test transaction via `POST /api/transactions` and verify it appears in `GET /api/transactions`.
- Run `POST /api/ai/analyze-transactions` with a small `limit` to verify AI integration (needs `GEMINI_API_KEY`).
- Ensure `DATABASE_URL`, `GEMINI_API_KEY`, `ADMIN_PASSWORD` are set in Render Dashboard (do NOT commit real values to Git).

Final notes

- Keep `render.yaml` and `Dockerfile.render` in Git so deployment is reproducible from the repository.
- Use the Render Dashboard to manage secrets and redeploys; do not commit production secrets. 
- After verification, remove any remaining debug endpoints and merge `deploy/render` into `main`.

