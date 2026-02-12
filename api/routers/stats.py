"""Stats router – server health and session stats."""

from __future__ import annotations

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
