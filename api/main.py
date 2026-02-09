"""Jarvis AI Agent API Server."""

import logging
import sys
import os
import time

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

log = logging.getLogger("jarvis.api")

from api.session_manager import SessionManager
from api.routers import auth, chat, tools, stats, learnings, conversation, settings

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
session_manager = SessionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    session_manager.initialize()

    # Inject session manager into routers that need it
    chat.set_session_manager(session_manager)
    tools.set_session_manager(session_manager)
    stats.set_session_manager(session_manager)
    learnings.set_session_manager(session_manager)
    conversation.set_session_manager(session_manager)
    settings.set_session_manager(session_manager)

    yield
    session_manager.shutdown()


app = FastAPI(
    title="Jarvis AI Agent API",
    description="API for the Jarvis AI Agent Platform",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all HTTP requests with method, path, status, and duration."""
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    # Skip noisy health checks at INFO level
    path = request.url.path
    if path == "/api/health" and response.status_code == 200:
        log.debug("%s %s %d %.0fms", request.method, path, response.status_code, duration_ms)
    else:
        log.info("%s %s %d %.0fms", request.method, path, response.status_code, duration_ms)
    return response


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(tools.router, prefix="/api", tags=["tools"])
app.include_router(stats.router, prefix="/api", tags=["stats"])
app.include_router(learnings.router, prefix="/api", tags=["learnings"])
app.include_router(conversation.router, prefix="/api/conversation", tags=["conversation"])
app.include_router(settings.router, prefix="/api", tags=["settings"])


@app.get("/api/health")
async def health(deep: bool = False):
    """Health check endpoint.

    Pass ?deep=true to verify backend API connectivity (slower).
    """
    result = {
        "status": "ok",
        "service": "jarvis-api",
        "uptime_seconds": round(session_manager.uptime_seconds, 1),
        "active_sessions": session_manager.active_session_count,
    }
    if deep:
        try:
            from jarvis.backends import create_backend

            backend = create_backend(session_manager.config)
            backend_ok = backend.ping()
        except Exception:
            backend_ok = False
        result["backend"] = {
            "name": session_manager.config.backend,
            "model": session_manager.config.model,
            "connected": backend_ok,
        }
        if not backend_ok:
            result["status"] = "degraded"
    return result
