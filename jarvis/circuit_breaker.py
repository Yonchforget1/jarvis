"""Circuit breaker pattern for backend API calls.

Prevents cascading failures by tracking error rates and temporarily
halting requests to failing backends.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Backend is failing, requests are rejected immediately
- HALF_OPEN: Testing if backend has recovered
"""

import logging
import threading
import time
from enum import Enum

log = logging.getLogger("jarvis.circuit_breaker")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker that wraps backend API calls."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._half_open_calls = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has elapsed
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    log.info("Circuit breaker transitioning to HALF_OPEN")
            return self._state

    def can_execute(self) -> bool:
        """Check if a request is allowed through the circuit breaker."""
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            with self._lock:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
            return False
        return False  # OPEN

    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.half_open_max_calls:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    log.info("Circuit breaker CLOSED (backend recovered)")
            else:
                self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                log.warning("Circuit breaker OPEN (recovery attempt failed)")
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                log.warning(
                    "Circuit breaker OPEN after %d failures (timeout: %.0fs)",
                    self._failure_count, self.recovery_timeout,
                )

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0
            log.info("Circuit breaker manually reset")

    def get_status(self) -> dict:
        """Get circuit breaker status for monitoring."""
        return {
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_seconds": self.recovery_timeout,
            "last_failure": self._last_failure_time,
        }


class CircuitOpenError(Exception):
    """Raised when a call is rejected because the circuit is open."""

    def __init__(self, breaker: CircuitBreaker):
        self.breaker = breaker
        super().__init__(
            f"Circuit breaker is {breaker.state.value}. "
            f"Backend has failed {breaker._failure_count} times. "
            f"Recovery in {max(0, breaker.recovery_timeout - (time.time() - breaker._last_failure_time)):.0f}s."
        )
