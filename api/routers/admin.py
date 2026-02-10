"""Admin endpoints: system management, user listing, config reload."""

import logging
import os
import platform
import time

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.audit import audit_log, get_recent_entries
from api.auth import authenticate_user
from api.deps import get_current_user
from api.models import UserInfo


class AdminConfirmRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)

limiter = Limiter(key_func=get_remote_address)

log = logging.getLogger("jarvis.api.admin")

router = APIRouter()

_session_manager = None

# Simple admin check: first registered user or env-configured admin
ADMIN_USERS = set(os.getenv("JARVIS_ADMIN_USERS", "admin").split(","))


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


def _require_admin(user: UserInfo, action: str = "admin_access", request: Request | None = None):
    ip = request.client.host if request and request.client else ""
    if user.username not in ADMIN_USERS:
        log.warning("Non-admin user '%s' attempted admin access", user.username)
        audit_log(user_id=user.id, username=user.username, action=f"{action}_denied",
                  detail="Unauthorized admin access attempt", ip=ip)
        raise HTTPException(403, "Admin access required")
    audit_log(user_id=user.id, username=user.username, action=action, ip=ip)


@router.get("/admin/system")
@limiter.limit("10/minute")
async def system_info(request: Request, user: UserInfo = Depends(get_current_user)):
    """Get detailed system information (admin only)."""
    _require_admin(user, "admin_system_info", request)

    info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "uptime_seconds": round(_session_manager.uptime_seconds, 1) if _session_manager else 0,
        "active_sessions": _session_manager.active_session_count if _session_manager else 0,
        "config": {
            "backend": _session_manager.config.backend,
            "model": _session_manager.config.model,
            "max_tokens": _session_manager.config.max_tokens,
            "tool_timeout": _session_manager.config.tool_timeout,
        } if _session_manager else {},
    }

    try:
        import psutil
        info["memory"] = {
            "total_mb": round(psutil.virtual_memory().total / 1024 / 1024, 1),
            "available_mb": round(psutil.virtual_memory().available / 1024 / 1024, 1),
            "percent_used": psutil.virtual_memory().percent,
        }
        info["cpu"] = {
            "count": psutil.cpu_count(),
            "percent": psutil.cpu_percent(interval=None),
        }
        info["disk"] = {
            "total_gb": round(psutil.disk_usage("/").total / 1024 / 1024 / 1024, 1),
            "free_gb": round(psutil.disk_usage("/").free / 1024 / 1024 / 1024, 1),
        }
    except ImportError:
        pass

    return info


@router.get("/admin/sessions")
@limiter.limit("10/minute")
async def list_all_sessions(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: UserInfo = Depends(get_current_user),
):
    """List all active sessions across all users with pagination (admin only)."""
    _require_admin(user, "admin_list_sessions", request)

    sessions = _session_manager.get_all_sessions() if _session_manager else []
    sessions = sorted(sessions, key=lambda s: s.last_active, reverse=True)
    total = len(sessions)
    page = sessions[offset:offset + limit]
    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "user_id": s.user_id,
                "created_at": s.created_at.isoformat(),
                "last_active": s.last_active.isoformat(),
                "message_count": s.message_count,
                "archived": getattr(s, "archived", False),
            }
            for s in page
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/admin/config/reload")
@limiter.limit("3/minute")
async def reload_config(request: Request, body: AdminConfirmRequest, user: UserInfo = Depends(get_current_user)):
    """Reload configuration from disk (admin only). Requires password confirmation."""
    _require_admin(user, "admin_config_reload", request)

    # Verify admin password before allowing config change
    if not authenticate_user(user.username, body.password):
        audit_log(user_id=user.id, username=user.username, action="config_reload_denied",
                  detail="Invalid password confirmation",
                  ip=request.client.host if request.client else "")
        raise HTTPException(403, "Invalid password confirmation")

    try:
        from jarvis.config import Config
        new_config = Config.load()
        if _session_manager:
            _session_manager.config = new_config
        audit_log(user_id=user.id, username=user.username, action="config_reload",
                  detail=f"backend={new_config.backend} model={new_config.model}")
        log.info("Config reloaded by admin '%s': backend=%s model=%s",
                 user.username, new_config.backend, new_config.model)
        return {
            "status": "reloaded",
            "config": {
                "backend": new_config.backend,
                "model": new_config.model,
                "max_tokens": new_config.max_tokens,
            },
        }
    except Exception as e:
        log.error("Config reload failed: %s", e)
        raise HTTPException(500, "Configuration reload failed. Check server logs.")


@router.get("/admin/tools/stats")
@limiter.limit("10/minute")
async def tool_stats(request: Request, user: UserInfo = Depends(get_current_user)):
    """Get tool usage statistics across all sessions (admin only)."""
    _require_admin(user, "admin_tool_stats", request)

    # Aggregate stats from all sessions
    all_stats = {}
    if _session_manager:
        for session in _session_manager.get_all_sessions():
            registry = session.conversation.registry
            for name, stat in registry.get_stats().items():
                if name not in all_stats:
                    all_stats[name] = {"calls": 0, "errors": 0, "total_ms": 0}
                all_stats[name]["calls"] += stat.call_count
                all_stats[name]["errors"] += stat.error_count
                all_stats[name]["total_ms"] += stat.total_duration_ms

    stats_list = [
        {
            "name": name,
            "calls": s["calls"],
            "errors": s["errors"],
            "avg_ms": round(s["total_ms"] / s["calls"], 1) if s["calls"] else 0,
        }
        for name, s in all_stats.items()
    ]
    return {"tools": sorted(stats_list, key=lambda x: x["calls"], reverse=True)}


@router.get("/admin/audit-logs")
@limiter.limit("10/minute")
async def view_audit_logs(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    action: str | None = Query(default=None, max_length=50),
    username: str | None = Query(default=None, max_length=50),
    user: UserInfo = Depends(get_current_user),
):
    """View recent audit log entries with optional filtering (admin only)."""
    _require_admin(user, "admin_view_audit_logs", request)

    entries = get_recent_entries(limit=min(limit * 2, 1000))  # Over-fetch for filtering
    if action:
        entries = [e for e in entries if e.get("action") == action]
    if username:
        entries = [e for e in entries if e.get("username") == username]
    return {"entries": entries[:limit], "total": len(entries)}


@router.delete("/admin/sessions/{session_id}")
@limiter.limit("10/minute")
async def terminate_session(
    request: Request,
    session_id: str = Path(..., min_length=8, max_length=64),
    user: UserInfo = Depends(get_current_user),
):
    """Force-terminate any session (admin only)."""
    _require_admin(user, "admin_terminate_session", request)

    if not _session_manager:
        raise HTTPException(500, "Session manager not available")

    # Find the session regardless of user
    session = None
    for s in _session_manager.get_all_sessions():
        if s.session_id == session_id:
            session = s
            break
    if not session:
        raise HTTPException(404, "Session not found")

    _session_manager.remove_session(session_id, session.user_id)
    audit_log(
        user_id=user.id, username=user.username, action="admin_session_terminate",
        detail=f"session={session_id} owner={session.user_id}",
        ip=request.client.host if request.client else "",
    )
    return {"status": "terminated", "session_id": session_id}
