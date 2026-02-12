"""Usage router – token consumption tracking and billing data."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_current_user
from api.models import UserInfo

router = APIRouter(prefix="/api", tags=["usage"])


@router.get("/usage")
async def get_my_usage(user: UserInfo = Depends(get_current_user)):
    """Get current user's token usage statistics."""
    from api.main import usage_tracker

    record = usage_tracker.get_user_usage(user.id)
    if not record:
        return {
            "user_id": user.id,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_requests": 0,
            "estimated_cost_usd": 0.0,
        }
    return record.to_dict()


@router.get("/admin/usage")
async def get_all_usage(user: UserInfo = Depends(get_current_user)):
    """Admin: Get usage stats for all users."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    from api.main import usage_tracker

    records = usage_tracker.get_all_usage()
    return {
        "users": [r.to_dict() for r in records],
        "totals": usage_tracker.get_total_stats(),
    }
