"""Usage tracking – track token consumption per user for billing – backed by Supabase."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone

from api.db import db

log = logging.getLogger("jarvis.api.usage")

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
    """Track and persist token usage per user via Supabase."""

    def __init__(self):
        self.records: dict[str, UsageRecord] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        """Load persisted usage data from Supabase (aggregated across all dates)."""
        rows = db.select("usage", order="date.asc")
        if not rows:
            return
        for row in rows:
            uid = row["user_id"]
            if uid not in self.records:
                self.records[uid] = UsageRecord(
                    user_id=uid,
                    first_request=str(row.get("date", "")),
                )
            record = self.records[uid]
            record.total_input_tokens += row.get("input_tokens", 0)
            record.total_output_tokens += row.get("output_tokens", 0)
            record.total_requests += row.get("requests", 0)
            record.estimated_cost_usd += row.get("estimated_cost_usd", 0.0)
            record.last_request = str(row.get("date", ""))

    def record_usage(
        self,
        user_id: str,
        input_tokens: int,
        output_tokens: int,
        model: str = "default",
    ) -> None:
        """Record token usage for a request."""
        now = datetime.now(timezone.utc).isoformat()
        today = datetime.now(timezone.utc).date().isoformat()

        # Estimate cost
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])
        cost = (input_tokens / 1_000_000) * pricing["input"] + \
               (output_tokens / 1_000_000) * pricing["output"]

        with self._lock:
            if user_id not in self.records:
                self.records[user_id] = UsageRecord(user_id=user_id, first_request=now)

            record = self.records[user_id]
            record.total_input_tokens += input_tokens
            record.total_output_tokens += output_tokens
            record.total_requests += 1
            record.last_request = now
            record.estimated_cost_usd += cost

        # Upsert today's usage row (incremental update via RPC would be ideal,
        # but for simplicity we read-then-update)
        existing = db.select(
            "usage",
            filters={"user_id": user_id, "date.eq": today},
            single=True,
        )
        if existing:
            db.update(
                "usage",
                {"user_id": user_id, "date.eq": today},
                {
                    "input_tokens": existing["input_tokens"] + input_tokens,
                    "output_tokens": existing["output_tokens"] + output_tokens,
                    "requests": existing["requests"] + 1,
                    "estimated_cost_usd": existing["estimated_cost_usd"] + cost,
                },
            )
        else:
            db.insert("usage", {
                "user_id": user_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "requests": 1,
                "estimated_cost_usd": round(cost, 6),
                "date": today,
            })

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
