"""Webhook system – register URLs and fire events asynchronously."""

from __future__ import annotations

import json
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("jarvis.api.webhooks")

_WEBHOOKS_DIR = Path(__file__).parent / "data" / "webhooks"


@dataclass
class Webhook:
    webhook_id: str
    user_id: str
    url: str
    events: list[str]  # e.g. ["task.completed", "message.received"]
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_fired: datetime | None = None
    fire_count: int = 0
    last_error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "webhook_id": self.webhook_id,
            "user_id": self.user_id,
            "url": self.url,
            "events": self.events,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "last_fired": self.last_fired.isoformat() if self.last_fired else None,
            "fire_count": self.fire_count,
            "last_error": self.last_error,
        }


class WebhookManager:
    """Manages webhook registrations and event firing."""

    VALID_EVENTS = [
        "task.completed",
        "task.failed",
        "message.received",
        "message.sent",
        "session.created",
        "session.deleted",
        "error.occurred",
    ]

    def __init__(self):
        self.webhooks: dict[str, Webhook] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        """Load persisted webhooks from disk."""
        if not _WEBHOOKS_DIR.exists():
            return
        for file in _WEBHOOKS_DIR.glob("*.json"):
            try:
                data = json.loads(file.read_text())
                wh = Webhook(
                    webhook_id=data["webhook_id"],
                    user_id=data["user_id"],
                    url=data["url"],
                    events=data["events"],
                    active=data.get("active", True),
                    fire_count=data.get("fire_count", 0),
                    last_error=data.get("last_error", ""),
                )
                self.webhooks[wh.webhook_id] = wh
            except Exception as e:
                log.warning("Failed to load webhook %s: %s", file.name, e)

    def _persist(self, wh: Webhook) -> None:
        """Save a webhook to disk."""
        _WEBHOOKS_DIR.mkdir(parents=True, exist_ok=True)
        path = _WEBHOOKS_DIR / f"{wh.webhook_id}.json"
        path.write_text(json.dumps(wh.to_dict(), default=str))

    def register(self, user_id: str, url: str, events: list[str]) -> Webhook:
        """Register a new webhook."""
        webhook_id = uuid.uuid4().hex[:12]
        wh = Webhook(
            webhook_id=webhook_id,
            user_id=user_id,
            url=url,
            events=events,
        )
        with self._lock:
            self.webhooks[webhook_id] = wh
            self._persist(wh)
        log.info("Webhook %s registered for user %s: %s -> %s", webhook_id, user_id, events, url)
        return wh

    def get_user_webhooks(self, user_id: str) -> list[Webhook]:
        return [wh for wh in self.webhooks.values() if wh.user_id == user_id]

    def delete(self, webhook_id: str) -> bool:
        with self._lock:
            wh = self.webhooks.pop(webhook_id, None)
            if wh:
                path = _WEBHOOKS_DIR / f"{webhook_id}.json"
                if path.exists():
                    path.unlink()
                return True
        return False

    def fire(self, event: str, payload: dict[str, Any]) -> int:
        """Fire an event to all matching webhooks. Returns count of webhooks fired."""
        matching = [
            wh for wh in self.webhooks.values()
            if wh.active and event in wh.events
        ]
        for wh in matching:
            thread = threading.Thread(
                target=self._deliver,
                args=(wh, event, payload),
                daemon=True,
            )
            thread.start()
        return len(matching)

    def _deliver(self, wh: Webhook, event: str, payload: dict) -> None:
        """Deliver a webhook with retry."""
        import time

        body = {
            "event": event,
            "webhook_id": wh.webhook_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload,
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                import httpx
                with httpx.Client(timeout=10) as client:
                    resp = client.post(
                        wh.url,
                        json=body,
                        headers={"Content-Type": "application/json", "X-Webhook-Event": event},
                    )
                    if resp.status_code < 400:
                        wh.fire_count += 1
                        wh.last_fired = datetime.now(timezone.utc)
                        wh.last_error = ""
                        self._persist(wh)
                        log.info("Webhook %s delivered: %s -> %d", wh.webhook_id, event, resp.status_code)
                        return
                    else:
                        wh.last_error = f"HTTP {resp.status_code}"
            except Exception as e:
                wh.last_error = str(e)

            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s

        self._persist(wh)
        log.warning("Webhook %s failed after %d retries: %s", wh.webhook_id, max_retries, wh.last_error)
