"""Error rate tracking and alerting thresholds.

Tracks error rates over sliding time windows and triggers alerts
when thresholds are exceeded.
"""

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass

log = logging.getLogger("jarvis.errors")


@dataclass
class AlertThreshold:
    """Defines when an alert should trigger."""

    name: str
    error_count: int  # Trigger when this many errors occur...
    window_seconds: float  # ...within this time window
    cooldown_seconds: float = 300.0  # Don't re-alert for this long


class ErrorTracker:
    """Tracks errors over sliding time windows and checks alert thresholds."""

    def __init__(self):
        self._errors: deque[tuple[float, str, str]] = deque(maxlen=10000)
        self._lock = threading.Lock()
        self._thresholds: list[AlertThreshold] = [
            AlertThreshold("high_error_rate", error_count=10, window_seconds=60),
            AlertThreshold("sustained_errors", error_count=50, window_seconds=300),
            AlertThreshold("critical_burst", error_count=5, window_seconds=10),
        ]
        self._last_alert: dict[str, float] = {}
        self._alert_callbacks: list = []

    def record_error(self, category: str, message: str) -> list[str]:
        """Record an error and check thresholds. Returns list of triggered alert names."""
        now = time.time()
        with self._lock:
            self._errors.append((now, category, message))

        triggered = self._check_thresholds(now)
        for alert_name in triggered:
            log.warning("ALERT: %s threshold exceeded", alert_name)
            for callback in self._alert_callbacks:
                try:
                    callback(alert_name, category, message)
                except Exception as e:
                    log.exception("Alert callback failed: %s", e)
        return triggered

    def _check_thresholds(self, now: float) -> list[str]:
        """Check all thresholds and return names of triggered alerts."""
        triggered = []
        with self._lock:
            for threshold in self._thresholds:
                # Check cooldown
                last = self._last_alert.get(threshold.name, 0)
                if now - last < threshold.cooldown_seconds:
                    continue

                # Count errors in window
                cutoff = now - threshold.window_seconds
                count = sum(1 for ts, _, _ in self._errors if ts >= cutoff)
                if count >= threshold.error_count:
                    triggered.append(threshold.name)
                    self._last_alert[threshold.name] = now

        return triggered

    def on_alert(self, callback) -> None:
        """Register a callback for when an alert triggers.

        Callback signature: callback(alert_name: str, category: str, message: str)
        """
        self._alert_callbacks.append(callback)

    def get_error_rate(self, window_seconds: float = 60) -> float:
        """Get errors per minute over the given window."""
        now = time.time()
        cutoff = now - window_seconds
        with self._lock:
            count = sum(1 for ts, _, _ in self._errors if ts >= cutoff)
        return count / (window_seconds / 60)

    def get_recent_errors(self, limit: int = 20) -> list[dict]:
        """Get recent errors for display."""
        with self._lock:
            recent = list(self._errors)[-limit:]
        return [
            {"timestamp": ts, "category": cat, "message": msg[:500]}
            for ts, cat, msg in reversed(recent)
        ]

    def get_stats(self) -> dict:
        """Get error tracking statistics."""
        now = time.time()
        return {
            "total_errors": len(self._errors),
            "errors_per_minute_1m": round(self.get_error_rate(60), 2),
            "errors_per_minute_5m": round(self.get_error_rate(300), 2),
            "errors_per_minute_15m": round(self.get_error_rate(900), 2),
            "active_alerts": [
                name for name, ts in self._last_alert.items()
                if now - ts < 300  # Show alerts from last 5 minutes
            ],
        }


# Global instance
error_tracker = ErrorTracker()
