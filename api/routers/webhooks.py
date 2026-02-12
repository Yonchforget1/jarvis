"""Webhooks router – register and manage webhook subscriptions."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import get_current_user
from api.models import UserInfo

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class WebhookCreateRequest(BaseModel):
    url: str = Field(min_length=10, description="Webhook callback URL")
    events: list[str] = Field(min_length=1, description="Events to subscribe to")


@router.post("", status_code=201)
async def create_webhook(
    req: WebhookCreateRequest,
    user: UserInfo = Depends(get_current_user),
):
    from api.main import webhook_mgr

    # Validate events
    invalid = [e for e in req.events if e not in webhook_mgr.VALID_EVENTS]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid events: {invalid}. Valid: {webhook_mgr.VALID_EVENTS}",
        )

    # Limit webhooks per user
    existing = webhook_mgr.get_user_webhooks(user.id)
    if len(existing) >= 10:
        raise HTTPException(status_code=400, detail="Maximum 10 webhooks per user")

    wh = webhook_mgr.register(user.id, req.url, req.events)
    return wh.to_dict()


@router.get("")
async def list_webhooks(user: UserInfo = Depends(get_current_user)):
    from api.main import webhook_mgr

    hooks = webhook_mgr.get_user_webhooks(user.id)
    return [wh.to_dict() for wh in hooks]


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    user: UserInfo = Depends(get_current_user),
):
    from api.main import webhook_mgr

    # Verify ownership
    wh = webhook_mgr.webhooks.get(webhook_id)
    if not wh or wh.user_id != user.id:
        raise HTTPException(status_code=404, detail="Webhook not found")

    webhook_mgr.delete(webhook_id)
    return {"status": "deleted", "webhook_id": webhook_id}


@router.get("/events")
async def list_events(user: UserInfo = Depends(get_current_user)):
    from api.main import webhook_mgr

    return {"events": webhook_mgr.VALID_EVENTS}
