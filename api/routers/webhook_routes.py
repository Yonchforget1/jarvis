"""Webhook management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl

from api.deps import get_current_user
from api.models import UserInfo
from api.webhooks import add_webhook, get_user_webhooks, remove_webhook

router = APIRouter()

VALID_EVENTS = ["chat.complete", "tool.error", "tool.complete", "session.created", "*"]


class WebhookCreate(BaseModel):
    url: str
    events: list[str]
    secret: str = ""


@router.get("/webhooks")
async def list_webhooks(user: UserInfo = Depends(get_current_user)):
    """List all webhooks for the current user."""
    hooks = get_user_webhooks(user.id)
    # Don't expose secrets in listing
    safe_hooks = []
    for h in hooks:
        safe = dict(h)
        safe.pop("secret", None)
        safe["has_secret"] = bool(h.get("secret"))
        safe_hooks.append(safe)
    return {"webhooks": safe_hooks}


@router.post("/webhooks")
async def create_webhook(
    body: WebhookCreate,
    user: UserInfo = Depends(get_current_user),
):
    """Register a new webhook URL for event notifications."""
    for event in body.events:
        if event not in VALID_EVENTS:
            raise HTTPException(400, f"Invalid event '{event}'. Valid: {VALID_EVENTS}")

    hook = add_webhook(user.id, str(body.url), body.events, body.secret)
    safe = dict(hook)
    safe.pop("secret", None)
    safe["has_secret"] = bool(body.secret)
    return {"webhook": safe}


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """Delete a webhook."""
    if not remove_webhook(user.id, webhook_id):
        raise HTTPException(404, "Webhook not found")
    return {"status": "deleted", "webhook_id": webhook_id}
