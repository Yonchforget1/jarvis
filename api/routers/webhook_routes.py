"""Webhook management endpoints."""

import ipaddress
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl

from api.deps import get_current_user
from api.models import UserInfo
from api.webhooks import add_webhook, get_user_webhooks, remove_webhook

router = APIRouter()

VALID_EVENTS = ["chat.complete", "tool.error", "tool.complete", "session.created", "*"]

# Private/reserved IP ranges that webhook URLs must not resolve to (SSRF prevention)
_BLOCKED_HOSTNAMES = {"localhost", "0.0.0.0"}


def _is_private_ip(hostname: str) -> bool:
    """Check if a hostname is a private/reserved IP address."""
    try:
        addr = ipaddress.ip_address(hostname)
        return addr.is_private or addr.is_reserved or addr.is_loopback
    except ValueError:
        return False


def _validate_webhook_url(url: str) -> str:
    """Validate that a webhook URL is safe (no SSRF vectors)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(400, "Webhook URL must use http or https scheme")
    hostname = parsed.hostname or ""
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        raise HTTPException(400, "Webhook URL cannot point to localhost")
    if _is_private_ip(hostname):
        raise HTTPException(400, "Webhook URL cannot point to a private IP address")
    return url


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
    _validate_webhook_url(body.url)
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
