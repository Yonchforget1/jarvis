"""Webhook notifications: POST to user-configured URLs on events."""

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field

import httpx

log = logging.getLogger("jarvis.webhooks")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
WEBHOOKS_FILE = os.path.join(DATA_DIR, "webhooks.json")
_lock = threading.Lock()


@dataclass
class WebhookConfig:
    url: str
    events: list[str]  # e.g. ["chat.complete", "tool.error"]
    secret: str = ""  # Optional shared secret for verification
    active: bool = True


def _load_webhooks() -> dict[str, list[dict]]:
    """Load all user webhook configs from disk."""
    with _lock:
        if not os.path.exists(WEBHOOKS_FILE):
            return {}
        with open(WEBHOOKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)


def _save_webhooks(data: dict) -> None:
    with _lock:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(WEBHOOKS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def get_user_webhooks(user_id: str) -> list[dict]:
    all_hooks = _load_webhooks()
    return all_hooks.get(user_id, [])


def add_webhook(user_id: str, url: str, events: list[str], secret: str = "") -> dict:
    all_hooks = _load_webhooks()
    user_hooks = all_hooks.get(user_id, [])

    hook = {
        "id": f"wh_{len(user_hooks) + 1}_{int(time.time())}",
        "url": url,
        "events": events,
        "secret": secret,
        "active": True,
        "created_at": time.time(),
    }
    user_hooks.append(hook)
    all_hooks[user_id] = user_hooks
    _save_webhooks(all_hooks)
    log.info("Webhook added for user %s: %s -> %s", user_id, events, url)
    return hook


def remove_webhook(user_id: str, webhook_id: str) -> bool:
    all_hooks = _load_webhooks()
    user_hooks = all_hooks.get(user_id, [])
    original_len = len(user_hooks)
    user_hooks = [h for h in user_hooks if h.get("id") != webhook_id]
    if len(user_hooks) == original_len:
        return False
    all_hooks[user_id] = user_hooks
    _save_webhooks(all_hooks)
    return True


def fire_event(user_id: str, event: str, data: dict) -> None:
    """Fire a webhook event asynchronously (non-blocking)."""
    user_hooks = get_user_webhooks(user_id)
    for hook in user_hooks:
        if not hook.get("active", True):
            continue
        if event not in hook.get("events", []) and "*" not in hook.get("events", []):
            continue
        # Fire in background thread to not block the request
        thread = threading.Thread(
            target=_deliver, args=(hook, event, data), daemon=True
        )
        thread.start()


def _deliver(hook: dict, event: str, data: dict) -> None:
    """Deliver a webhook payload via POST."""
    url = hook.get("url", "")
    payload = {
        "event": event,
        "data": data,
        "timestamp": time.time(),
        "webhook_id": hook.get("id", ""),
    }
    headers = {"Content-Type": "application/json", "X-Jarvis-Event": event}
    if hook.get("secret"):
        import hashlib
        import hmac
        sig = hmac.new(hook["secret"].encode(), json.dumps(payload).encode(), hashlib.sha256).hexdigest()
        headers["X-Jarvis-Signature"] = sig

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=10)
        log.info("Webhook delivered to %s: %d", url, resp.status_code)
    except Exception as e:
        log.warning("Webhook delivery failed to %s: %s", url, e)
