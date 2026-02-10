"""Learnings endpoint: view agent learnings."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.deps import get_current_user
from api.models import LearningEntry, LearningsResponse, UserInfo

log = logging.getLogger("jarvis.api.learnings")

router = APIRouter()
_limiter = Limiter(key_func=get_remote_address)

_session_manager = None


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


@router.get("/learnings", response_model=LearningsResponse)
@_limiter.limit("30/minute")
async def get_learnings(
    request: Request,
    response: Response,
    topic: str | None = Query(None, description="Semantic topic search"),
    search: str | None = Query(None, max_length=200, description="Full-text search across insight, context, task"),
    sort: str = Query("newest", pattern="^(newest|oldest|category)$", description="Sort order: newest, oldest, category"),
    category: str | None = Query(None, max_length=64, description="Filter by category"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    user: UserInfo = Depends(get_current_user),
):
    response.headers["Cache-Control"] = "private, max-age=300"
    if _session_manager is None:
        raise HTTPException(status_code=503, detail="Service initializing")
    try:
        memory = _session_manager.memory

        if topic:
            raw = memory.get_relevant(topic)
        else:
            raw = list(memory.all_learnings)

        # Full-text search filter
        if search:
            q = search.lower()
            raw = [
                e for e in raw
                if q in e.get("insight", "").lower()
                or q in e.get("context", "").lower()
                or q in e.get("task_description", "").lower()
            ]

        # Category filter
        if category:
            raw = [e for e in raw if e.get("category", "") == category]

        # Sort
        if sort == "newest":
            raw.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        elif sort == "oldest":
            raw.sort(key=lambda e: e.get("timestamp", ""))
        elif sort == "category":
            raw.sort(key=lambda e: e.get("category", ""))

        total = len(raw)
        start = (page - 1) * page_size
        end = start + page_size
        page_items = raw[start:end]

        entries = [
            LearningEntry(
                timestamp=e.get("timestamp", ""),
                category=e.get("category", ""),
                insight=e.get("insight", ""),
                context=e.get("context", ""),
                task_description=e.get("task_description", ""),
            )
            for e in page_items
        ]

        return LearningsResponse(
            learnings=entries,
            count=len(entries),
            total=total,
            page=page,
            page_size=page_size,
        )
    except Exception as e:
        log.exception("Failed to get learnings for user %s", user.id)
        raise HTTPException(status_code=500, detail="Failed to retrieve learnings")
