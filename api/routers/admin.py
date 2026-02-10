"""Admin endpoints: system management, user listing, config reload."""

import logging
import os
import platform
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.audit import audit_log
from api.deps import get_current_user
from api.models import UserInfo

limiter = Limiter(key_func=get_remote_address)

log = logging.getLogger("jarvis.api.admin")

router = APIRouter()

_session_manager = None

# Simple admin check: first registered user or env-configured admin
ADMIN_USERS = set(os.getenv("JARVIS_ADMIN_USERS", "admin").split(","))


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


def _require_admin(user: UserInfo):
    if user.username not in ADMIN_USERS:
        log.warning("Non-admin user '%s' attempted admin access", user.username)
        raise HTTPException(403, "Admin access required")


@router.get("/admin/system")
@limiter.limit("10/minute")
async def system_info(request: Request, user: UserInfo = Depends(get_current_user)):
    """Get detailed system information (admin only)."""
    _require_admin(user)

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
async def list_all_sessions(request: Request, user: UserInfo = Depends(get_current_user)):
    """List all active sessions across all users (admin only)."""
    _require_admin(user)

    sessions = _session_manager.get_all_sessions() if _session_manager else []
    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "user_id": s.user_id,
                "created_at": s.created_at.isoformat(),
                "last_active": s.last_active.isoformat(),
                "message_count": s.message_count,
            }
            for s in sessions
        ],
        "total": len(sessions),
    }


@router.post("/admin/config/reload")
@limiter.limit("3/minute")
async def reload_config(request: Request, user: UserInfo = Depends(get_current_user)):
    """Reload configuration from disk (admin only)."""
    _require_admin(user)

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
    _require_admin(user)

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
