"""Jarvis AI Agent API Server."""

import logging
import platform
import sys
import os
import time
import uuid

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
from api.routers import auth, chat, tools, stats, learnings, conversation, settings, files, websocket

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
session_manager = SessionManager()


_shutting_down = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _shutting_down
    _shutting_down = False
    log.info("Jarvis API starting up...")
    session_manager.initialize()

    # Inject session manager into routers that need it
    chat.set_session_manager(session_manager)
    tools.set_session_manager(session_manager)
    stats.set_session_manager(session_manager)
    learnings.set_session_manager(session_manager)
    conversation.set_session_manager(session_manager)
    settings.set_session_manager(session_manager)
    websocket.set_session_manager(session_manager)

    log.info("Jarvis API ready (backend=%s, model=%s)",
             session_manager.config.backend, session_manager.config.model)
    yield

    log.info("Jarvis API shutting down...")
    _shutting_down = True
    session_manager.shutdown()
    log.info("Jarvis API shutdown complete.")


API_VERSION = "1.0.0"

app = FastAPI(
    title="Jarvis AI Agent API",
    description="API for the Jarvis AI Agent Platform",
    version=API_VERSION,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log all HTTP requests with method, path, status, and duration.

    Rejects non-health requests during shutdown with 503.
    """
    path = request.url.path
    if _shutting_down and path != "/api/health":
        return JSONResponse(
            status_code=503,
            content={"detail": "Server is shutting down"},
        )
    # Assign a correlation ID for request tracing
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    response.headers["X-API-Version"] = API_VERSION
    if path == "/api/health" and response.status_code == 200:
        log.debug("[%s] %s %s %d %.0fms", request_id, request.method, path, response.status_code, duration_ms)
    else:
        log.info("[%s] %s %s %d %.0fms", request_id, request.method, path, response.status_code, duration_ms)
    return response


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(tools.router, prefix="/api", tags=["tools"])
app.include_router(stats.router, prefix="/api", tags=["stats"])
app.include_router(learnings.router, prefix="/api", tags=["learnings"])
app.include_router(conversation.router, prefix="/api/conversation", tags=["conversation"])
app.include_router(settings.router, prefix="/api", tags=["settings"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(websocket.router, prefix="/api", tags=["websocket"])


@app.get("/api/health")
async def health(deep: bool = False):
    """Health check endpoint.

    Pass ?deep=true to verify backend API connectivity (slower).
    """
    result = {
        "status": "ok",
        "service": "jarvis-api",
        "version": app.version,
        "uptime_seconds": round(session_manager.uptime_seconds, 1),
        "active_sessions": session_manager.active_session_count,
        "system": {
            "python_version": platform.python_version(),
            "platform": platform.system(),
            "architecture": platform.machine(),
        },
        "config": {
            "backend": session_manager.config.backend,
            "model": session_manager.config.model,
        },
    }

    # Add memory info if psutil is available
    try:
        import psutil
        process = psutil.Process()
        mem_info = process.memory_info()
        result["system"]["memory_mb"] = round(mem_info.rss / 1024 / 1024, 1)
        result["system"]["cpu_percent"] = process.cpu_percent(interval=None)
    except ImportError:
        pass

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
