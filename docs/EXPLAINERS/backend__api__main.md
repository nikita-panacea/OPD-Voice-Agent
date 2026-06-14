# Explainer — `backend/api/main.py`

## Purpose
The FastAPI application that serves the browser client's token endpoint (and, in later phases,
staff report reads). Separate process from the agent worker.

## Dependencies & data in/out
- **Imports:** `fastapi`, CORS middleware, `api.tokens` router, `logging_setup`, `store.db.init_db`.

## Walkthrough
- **`lifespan(app)`** — async context manager that calls `init_db()` on startup (creates tables).
- **`app`** — `FastAPI(title=..., lifespan=lifespan)`.
- **CORS** — allows the Vite dev origin (`localhost:5173`). Tighten for production.
- **`app.include_router(tokens.router)` / `app.include_router(sessions.router)`** — mounts
  `/api/token` and the staff `/api/sessions` report endpoints.
- **`health()`** (`GET /health`) — liveness probe.

## Gotchas / TODOs
- CORS is dev-permissive; lock down origins/methods for production.
- Run with `uvicorn api.main:app --reload --port 8000` from `backend/`.
