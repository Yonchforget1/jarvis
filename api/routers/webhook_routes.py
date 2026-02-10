"""Webhook management endpoints."""

import ipaddress
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, HttpUrl
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.deps import get_current_user
from api.models import UserInfo
from api.webhooks import add_webhook, get_user_webhooks, remove_webhook

router = APIRouter()
_limiter = Limiter(key_func=get_remote_address)

VALID_EVENTS = ["chat.complete", "tool.error", "tool.complete", "session.created", "*"]
MAX_WEBHOOKS_PER_USER = 10
MAX_URL_LENGTH = 2048

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
@_limiter.limit("30/minute")
async def list_webhooks(request: Request, user: UserInfo = Depends(get_current_user)):
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
@_limiter.limit("10/minute")
async def create_webhook(
    request: Request,
    body: WebhookCreate,
    user: UserInfo = Depends(get_current_user),
):
    """Register a new webhook URL for event notifications."""
    # URL length validation
    if len(body.url) > MAX_URL_LENGTH:
        raise HTTPException(400, f"Webhook URL too long (max {MAX_URL_LENGTH} characters)")

    _validate_webhook_url(body.url)

    for event in body.events:
        if event not in VALID_EVENTS:
            raise HTTPException(400, f"Invalid event '{event}'. Valid: {VALID_EVENTS}")
    if not body.events:
        raise HTTPException(400, "At least one event must be specified")
    if len(body.events) > len(VALID_EVENTS):
        raise HTTPException(400, f"Too many events (max {len(VALID_EVENTS)})")

    # Per-user webhook limit
    existing = get_user_webhooks(user.id)
    if len(existing) >= MAX_WEBHOOKS_PER_USER:
        raise HTTPException(400, f"Maximum {MAX_WEBHOOKS_PER_USER} webhooks per user")

    hook = add_webhook(user.id, str(body.url), body.events, body.secret)
    safe = dict(hook)
    safe.pop("secret", None)
    safe["has_secret"] = bool(body.secret)
    return {"webhook": safe}


@router.post("/webhooks/{webhook_id}/test")
@_limiter.limit("5/minute")
async def test_webhook(
    request: Request,
    webhook_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """Send a test event to a specific webhook to verify it's reachable."""
    from api.webhooks import _deliver
    import time as _time

    hooks = get_user_webhooks(user.id)
    hook = next((h for h in hooks if h.get("id") == webhook_id), None)
    if not hook:
        raise HTTPException(404, "Webhook not found")

    test_data = {
        "message": "This is a test event from Jarvis.",
        "webhook_id": webhook_id,
        "timestamp": _time.time(),
    }
    payload = {
        "event": "test",
        "data": test_data,
        "timestamp": _time.time(),
        "webhook_id": webhook_id,
    }
    import json as _json
    import httpx as _httpx

    headers = {"Content-Type": "application/json", "X-Jarvis-Event": "test"}
    if hook.get("secret"):
        import hashlib, hmac
        sig = hmac.new(hook["secret"].encode(), _json.dumps(payload, sort_keys=True).encode(), hashlib.sha256).hexdigest()
        headers["X-Jarvis-Signature"] = sig

    try:
        resp = _httpx.post(hook["url"], json=payload, headers=headers, timeout=10)
        return {"status": "delivered", "http_status": resp.status_code, "webhook_id": webhook_id}
    except Exception as e:
        return {"status": "failed", "error": str(e), "webhook_id": webhook_id}


@router.delete("/webhooks/{webhook_id}")
@_limiter.limit("10/minute")
async def delete_webhook(
    request: Request,
    webhook_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """Delete a webhook."""
    if not remove_webhook(user.id, webhook_id):
        raise HTTPException(404, "Webhook not found")
    return {"status": "deleted", "webhook_id": webhook_id}
