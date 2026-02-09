"""Learnings endpoint: view agent learnings."""

from fastapi import APIRouter, Depends, Query

from api.deps import get_current_user
from api.models import LearningEntry, LearningsResponse, UserInfo

router = APIRouter()

_session_manager = None


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


@router.get("/learnings", response_model=LearningsResponse)
async def get_learnings(
    topic: str | None = Query(None),
    user: UserInfo = Depends(get_current_user),
):
    memory = _session_manager.memory

    if topic:
        raw = memory.get_relevant(topic)
    else:
        raw = memory._learnings

    entries = [
        LearningEntry(
            timestamp=e.get("timestamp", ""),
            category=e.get("category", ""),
            insight=e.get("insight", ""),
            context=e.get("context", ""),
            task_description=e.get("task_description", ""),
        )
        for e in raw
    ]

    return LearningsResponse(learnings=entries, count=len(entries))
