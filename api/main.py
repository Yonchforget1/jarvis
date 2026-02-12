"""Jarvis API – FastAPI application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.session_manager import SessionManager

log = logging.getLogger("jarvis.api")

session_mgr = SessionManager()

limiter = Limiter(key_func=get_remote_address)

_STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Jarvis API starting up")
    yield
    expired = session_mgr.cleanup_expired()
    log.info("Jarvis API shutting down – cleaned %d expired sessions", expired)


app = FastAPI(
    title="Jarvis AI Agent",
    version="2.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Routers ----------
from api.routers.auth import router as auth_router  # noqa: E402
from api.routers.chat import router as chat_router  # noqa: E402
from api.routers.sessions import router as sessions_router  # noqa: E402
from api.routers.stats import router as stats_router  # noqa: E402
from api.routers.tools import router as tools_router  # noqa: E402

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(sessions_router)
app.include_router(tools_router)
app.include_router(stats_router)

# ---------- Static files ----------
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/")
async def root():
    index = _STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"message": "Jarvis API v2.0.0", "docs": "/docs"})


def start():
    """Entry point for running the server."""
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=3000)


if __name__ == "__main__":
    start()
