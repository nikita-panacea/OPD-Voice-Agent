"""FastAPI app: serves the browser client's LiveKit token (and, later, staff report reads).

This process is separate from the LiveKit agent worker. Run (from `backend/`):
    uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import dashboard, sessions, tokens
from config.settings import ENV_FILE
from logging_setup import configure_logging, get_logger
from store.db import init_db

# Load .env into os.environ (consistent with the worker; harmless for the API).
load_dotenv(ENV_FILE)
configure_logging()
log = get_logger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables on startup."""
    init_db()
    log.info("api_startup_complete")
    yield


app = FastAPI(title="OPD Intelligence API (POC)", lifespan=lifespan)

# Dev CORS: allow the Vite dev server. Tighten for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tokens.router)
app.include_router(sessions.router)
app.include_router(dashboard.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}
