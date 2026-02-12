"""Stats router – server health and session stats."""

from __future__ import annotations

import platform
import sys

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
async def stats():
    from api.main import session_mgr

    return {
        "uptime_seconds": round(session_mgr.uptime_seconds, 1),
        "active_sessions": session_mgr.active_session_count,
        "memory_entries": session_mgr.memory.count,
    }


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/detailed")
async def health_detailed():
    """Detailed system health with metrics for the status dashboard."""
    import os
    import psutil

    from api.main import session_mgr, scheduler, usage_tracker

    proc = psutil.Process(os.getpid())
    mem = proc.memory_info()

    # Check backend connectivity
    backend_status = "unknown"
    try:
        from jarvis.config import Config
        config = Config.load()
        backend_status = f"{config.backend}:{config.model}"
    except Exception:
        backend_status = "error"

    return {
        "status": "ok",
        "uptime_seconds": round(session_mgr.uptime_seconds, 1),
        "python_version": sys.version.split()[0],
        "platform": platform.system(),
        "process": {
            "pid": os.getpid(),
            "memory_mb": round(mem.rss / 1024 / 1024, 1),
            "memory_percent": round(proc.memory_percent(), 1),
            "cpu_percent": round(proc.cpu_percent(interval=0.1), 1),
            "threads": proc.num_threads(),
        },
        "sessions": {
            "active": session_mgr.active_session_count,
            "memory_entries": session_mgr.memory.count,
        },
        "scheduler": {
            "running": scheduler._running,
            "schedules_count": len(scheduler.schedules),
            "enabled_count": sum(1 for s in scheduler.schedules.values() if s.enabled),
        },
        "backend": backend_status,
        "usage": usage_tracker.get_total_stats(),
    }
