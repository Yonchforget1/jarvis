"""Scheduled tasks API – create, list, update, delete recurring tasks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import UserInfo, get_current_user

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


class CreateScheduleReq(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    cron: str = Field(..., min_length=1, max_length=50)
    task_type: str = Field(..., pattern="^(shell|conversation|tool)$")
    payload: dict = Field(default_factory=dict)


class UpdateScheduleReq(BaseModel):
    enabled: bool | None = None
    name: str | None = Field(None, min_length=1, max_length=200)
    cron: str | None = Field(None, min_length=1, max_length=50)


def _get_scheduler():
    from api.main import scheduler
    return scheduler


@router.post("")
async def create_schedule(
    req: CreateScheduleReq,
    user: UserInfo = Depends(get_current_user),
):
    sched_mgr = _get_scheduler()
    user_schedules = sched_mgr.get_user_schedules(user.id)
    if len(user_schedules) >= 20:
        raise HTTPException(400, "Maximum 20 schedules per user")

    try:
        sched = sched_mgr.create_schedule(
            user_id=user.id,
            name=req.name,
            cron=req.cron,
            task_type=req.task_type,
            payload=req.payload,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return sched.to_dict()


@router.get("")
async def list_schedules(user: UserInfo = Depends(get_current_user)):
    sched_mgr = _get_scheduler()
    schedules = sched_mgr.get_user_schedules(user.id)
    return [s.to_dict() for s in schedules]


@router.get("/cron-aliases")
async def list_cron_aliases(user: UserInfo = Depends(get_current_user)):
    from api.scheduler import CRON_ALIASES
    return {
        "aliases": {k: v for k, v in CRON_ALIASES.items()},
        "examples": [
            {"cron": "*/5 * * * *", "description": "Every 5 minutes"},
            {"cron": "0 * * * *", "description": "Every hour"},
            {"cron": "0 9 * * 1-5", "description": "Weekdays at 9 AM"},
            {"cron": "0 0 * * *", "description": "Daily at midnight"},
            {"cron": "0 0 1 * *", "description": "Monthly on the 1st"},
        ],
    }


@router.get("/{schedule_id}")
async def get_schedule(
    schedule_id: str,
    user: UserInfo = Depends(get_current_user),
):
    sched_mgr = _get_scheduler()
    sched = sched_mgr.get_schedule(schedule_id)
    if not sched or sched.user_id != user.id:
        raise HTTPException(404, "Schedule not found")
    return sched.to_dict()


@router.patch("/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    req: UpdateScheduleReq,
    user: UserInfo = Depends(get_current_user),
):
    sched_mgr = _get_scheduler()
    sched = sched_mgr.get_schedule(schedule_id)
    if not sched or sched.user_id != user.id:
        raise HTTPException(404, "Schedule not found")

    try:
        updated = sched_mgr.update_schedule(
            schedule_id,
            enabled=req.enabled,
            name=req.name,
            cron=req.cron,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    return updated.to_dict() if updated else None


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    user: UserInfo = Depends(get_current_user),
):
    sched_mgr = _get_scheduler()
    sched = sched_mgr.get_schedule(schedule_id)
    if not sched or sched.user_id != user.id:
        raise HTTPException(404, "Schedule not found")

    sched_mgr.delete_schedule(schedule_id)
    return {"status": "deleted"}
