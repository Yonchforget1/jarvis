"""Jarvis AI Agent API Server."""

import asyncio
import contextvars
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
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

log = logging.getLogger("jarvis.api")

# Context variable for request-scoped tracing ID
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

from api.session_manager import SessionManager
from api.routers import admin, auth, chat, compliance, dashboard, tools, stats, learnings, conversation, settings, files, metrics, websocket, webhook_routes, whatsapp, logs

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
    admin.set_session_manager(session_manager)
    metrics.set_session_manager(session_manager)
    dashboard.set_session_manager(session_manager)
    compliance.set_session_manager(session_manager)
    whatsapp.set_session_manager(session_manager)

    session_manager.start_cleanup_timer(interval_seconds=3600)  # Cleanup expired sessions every hour
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
    description=(
        "## Jarvis AI Agent Platform API\n\n"
        "Jarvis is an AI agent platform that executes tasks using configurable AI backends "
        "(Claude, OpenAI, Gemini) with 30+ tools for filesystem, web, shell, and more.\n\n"
        "### Authentication\n"
        "Most endpoints require a JWT bearer token obtained via `POST /api/auth/login`.\n\n"
        "### Real-time\n"
        "- **SSE**: `POST /api/chat/stream` for server-sent events\n"
        "- **WebSocket**: `WS /api/ws/chat` for bidirectional real-time chat\n\n"
        "### Rate Limits\n"
        "- General: 60 requests/minute\n"
        "- Chat: 20 requests/minute"
    ),
    version=API_VERSION,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "auth", "description": "User authentication and registration"},
        {"name": "chat", "description": "Send messages and receive AI responses"},
        {"name": "tools", "description": "List and inspect available AI tools"},
        {"name": "stats", "description": "System and usage statistics"},
        {"name": "learnings", "description": "AI learning memory management"},
        {"name": "conversation", "description": "Session and conversation management"},
        {"name": "settings", "description": "User preferences and configuration"},
        {"name": "files", "description": "File upload and management"},
        {"name": "websocket", "description": "Real-time WebSocket chat"},
        {"name": "voice", "description": "Voice input and transcription"},
    ],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return structured 400 with field-level error details."""
    req_id = request.headers.get("X-Request-ID", "?")
    log.warning("[%s] Validation error on %s %s: %s", req_id, request.method, request.url.path, exc.errors())
    errors = []
    for err in exc.errors()[:5]:
        loc = err.get("loc", ())
        field = ".".join(str(x) for x in loc[1:]) if len(loc) > 1 else str(loc[0]) if loc else "unknown"
        errors.append({"field": field, "message": err.get("msg", "Invalid value")})
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid request", "errors": errors},
    )

_cors_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Accept"],
)

# GZip compression for responses >= 500 bytes
app.add_middleware(GZipMiddleware, minimum_size=500)


MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB


@app.middleware("http")
async def body_size_limit_middleware(request: Request, call_next):
    """Reject request bodies larger than MAX_BODY_SIZE."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_SIZE:
        return JSONResponse(
            status_code=413,
            content={"detail": f"Request body too large (max {MAX_BODY_SIZE // (1024 * 1024)} MB)"},
        )
    return await call_next(request)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(self), geolocation=()"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    # CSP: allow self + API + inline styles (needed for Next.js) + media from self
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self'; "
        "connect-src 'self' ws: wss: http://localhost:8000 http://localhost:3000; "
        "media-src 'self' blob:; "
        "frame-ancestors 'none'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    response.headers["Content-Security-Policy"] = csp
    return response


REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "120"))
# Paths exempt from the general timeout (streaming, WebSocket, etc.)
_TIMEOUT_EXEMPT = {"/api/chat/stream", "/api/chat/batch", "/api/ws/chat", "/api/compliance/export"}


@app.middleware("http")
async def request_timeout_middleware(request: Request, call_next):
    """Abort non-streaming requests that exceed REQUEST_TIMEOUT seconds."""
    path = request.url.path
    if any(path.startswith(p) for p in _TIMEOUT_EXEMPT):
        return await call_next(request)
    try:
        return await asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT)
    except asyncio.TimeoutError:
        log.warning("Request timeout: %s %s (>%ds)", request.method, path, REQUEST_TIMEOUT)
        return JSONResponse(status_code=504, content={"detail": "Request timed out"})


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
    request_id_var.set(request_id)
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
app.include_router(webhook_routes.router, prefix="/api", tags=["webhooks"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
app.include_router(metrics.router, prefix="/api", tags=["monitoring"])
app.include_router(dashboard.router, prefix="/api", tags=["monitoring"])
app.include_router(compliance.router, prefix="/api", tags=["compliance"])
app.include_router(whatsapp.router, prefix="/api", tags=["whatsapp"])
app.include_router(logs.router, prefix="/api", tags=["monitoring"])

# Integration routes (voice transcription, etc.)
from jarvis.integrations import register_integration_routes
register_integration_routes(app)


@app.get("/api/health")
@limiter.limit("60/minute")
async def health(request: Request, deep: bool = False):
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
        subsystems = {}
        overall_status = "ok"

        # Backend connectivity
        try:
            from jarvis.backends import create_backend
            backend = create_backend(session_manager.config)
            backend_ok = backend.ping()
        except Exception:
            backend_ok = False
        subsystems["backend"] = {
            "name": session_manager.config.backend,
            "model": session_manager.config.model,
            "status": "ok" if backend_ok else "unhealthy",
        }
        if not backend_ok:
            overall_status = "degraded"

        # Memory health
        try:
            import psutil
            mem = psutil.virtual_memory()
            mem_status = "ok" if mem.percent < 80 else "warning" if mem.percent < 95 else "unhealthy"
            subsystems["memory"] = {"percent_used": mem.percent, "status": mem_status}
            if mem_status == "unhealthy":
                overall_status = "degraded"
        except ImportError:
            subsystems["memory"] = {"status": "unknown"}

        # Sessions health
        active = session_manager.active_session_count
        subsystems["sessions"] = {"active": active, "status": "ok" if active < 500 else "warning"}

        # Reaction analytics (if available)
        try:
            from api.routers.chat import get_reaction_counts
            subsystems["reactions"] = get_reaction_counts()
        except Exception:
            pass

        result["subsystems"] = subsystems
        result["status"] = overall_status
    return result


# --- Web Chat UI ---

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

@app.get("/")
async def root():
    """Serve the web chat UI."""
    return FileResponse(os.path.join(_STATIC_DIR, "index.html"))

app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
