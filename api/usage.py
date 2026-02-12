"""Usage tracking – track token consumption per user for billing."""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("jarvis.api.usage")

_USAGE_DIR = Path(__file__).parent / "data" / "usage"

# Approximate cost per 1M tokens (USD) for common models
MODEL_PRICING = {
    # Anthropic
    "claude-sonnet-4-5-20250929": {"input": 3.00, "output": 15.00},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    # Gemini
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    "gemini-2.0-pro": {"input": 1.25, "output": 5.00},
    # Default fallback
    "default": {"input": 3.00, "output": 15.00},
}


@dataclass
class UsageRecord:
    user_id: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_requests: int = 0
    estimated_cost_usd: float = 0.0
    first_request: str = ""
    last_request: str = ""

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_requests": self.total_requests,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
            "first_request": self.first_request,
            "last_request": self.last_request,
        }


class UsageTracker:
    """Track and persist token usage per user."""

    def __init__(self):
        self.records: dict[str, UsageRecord] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        """Load persisted usage data from disk."""
        if not _USAGE_DIR.exists():
            return
        for file in _USAGE_DIR.glob("*.json"):
            try:
                data = json.loads(file.read_text())
                record = UsageRecord(
                    user_id=data["user_id"],
                    total_input_tokens=data.get("total_input_tokens", 0),
                    total_output_tokens=data.get("total_output_tokens", 0),
                    total_requests=data.get("total_requests", 0),
                    estimated_cost_usd=data.get("estimated_cost_usd", 0.0),
                    first_request=data.get("first_request", ""),
                    last_request=data.get("last_request", ""),
                )
                self.records[record.user_id] = record
            except Exception as e:
                log.warning("Failed to load usage %s: %s", file.name, e)

    def _persist(self, record: UsageRecord) -> None:
        """Save a usage record to disk."""
        _USAGE_DIR.mkdir(parents=True, exist_ok=True)
        path = _USAGE_DIR / f"{record.user_id}.json"
        path.write_text(json.dumps(record.to_dict(), indent=2))

    def record_usage(
        self,
        user_id: str,
        input_tokens: int,
        output_tokens: int,
        model: str = "default",
    ) -> None:
        """Record token usage for a request."""
        now = datetime.now(timezone.utc).isoformat()

        with self._lock:
            if user_id not in self.records:
                self.records[user_id] = UsageRecord(user_id=user_id, first_request=now)

            record = self.records[user_id]
            record.total_input_tokens += input_tokens
            record.total_output_tokens += output_tokens
            record.total_requests += 1
            record.last_request = now

            # Estimate cost
            pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
            cost = (input_tokens / 1_000_000) * pricing["input"] + \
                   (output_tokens / 1_000_000) * pricing["output"]
            record.estimated_cost_usd += cost

            self._persist(record)

    def get_user_usage(self, user_id: str) -> UsageRecord | None:
        return self.records.get(user_id)

    def get_all_usage(self) -> list[UsageRecord]:
        return list(self.records.values())

    def get_total_stats(self) -> dict:
        """Aggregate stats across all users."""
        total_input = sum(r.total_input_tokens for r in self.records.values())
        total_output = sum(r.total_output_tokens for r in self.records.values())
        total_cost = sum(r.estimated_cost_usd for r in self.records.values())
        total_requests = sum(r.total_requests for r in self.records.values())
        return {
            "total_users": len(self.records),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_requests": total_requests,
            "estimated_total_cost_usd": round(total_cost, 4),
        }
