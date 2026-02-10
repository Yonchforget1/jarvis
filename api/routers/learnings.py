"""Learnings endpoint: view agent learnings."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_current_user
from api.models import LearningEntry, LearningsResponse, UserInfo

log = logging.getLogger("jarvis.api.learnings")

router = APIRouter()

_session_manager = None


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


@router.get("/learnings", response_model=LearningsResponse)
async def get_learnings(
    topic: str | None = Query(None),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    user: UserInfo = Depends(get_current_user),
):
    try:
        memory = _session_manager.memory

        if topic:
            raw = memory.get_relevant(topic)
        else:
            raw = memory.all_learnings

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
