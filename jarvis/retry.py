"""Retry logic for API calls with rate-limit-aware backoff."""

import time
import logging

log = logging.getLogger("jarvis")

# Keywords that indicate a transient / rate-limit error worth retrying
_TRANSIENT_KEYWORDS = [
    "rate_limit", "rate limit", "overloaded", "529",
    "timeout", "connection", "502", "503", "504",
]

_RATE_LIMIT_KEYWORDS = ["rate_limit", "rate limit", "429", "529", "overloaded"]

DEFAULT_MAX_RETRIES = 5
RATE_LIMIT_WAIT = 90  # seconds to wait on rate-limit errors
TRANSIENT_BASE_DELAY = 2.0  # base delay for non-rate-limit transient errors


def is_transient(error: Exception) -> bool:
    """Check if an error is transient and worth retrying."""
    error_str = str(error).lower()
    return any(kw in error_str for kw in _TRANSIENT_KEYWORDS)


def is_rate_limit(error: Exception) -> bool:
    """Check if an error is specifically a rate limit."""
    error_str = str(error).lower()
    return any(kw in error_str for kw in _RATE_LIMIT_KEYWORDS)


def retry_api_call(func, *args, max_retries=DEFAULT_MAX_RETRIES, **kwargs):
    """Call func(*args, **kwargs) with retry logic.

    - Rate limit errors: wait 90 seconds before retrying.
    - Other transient errors: exponential backoff starting at 2s.
    - Non-transient errors: raise immediately.
    """
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            is_last = attempt == max_retries - 1

            if is_last:
                raise

            if is_rate_limit(e):
                log.warning(
                    "Rate limit hit (attempt %d/%d), waiting %ds: %s",
                    attempt + 1, max_retries, RATE_LIMIT_WAIT, e,
                )
                time.sleep(RATE_LIMIT_WAIT)
            elif is_transient(e):
                delay = TRANSIENT_BASE_DELAY * (2 ** attempt)
                log.warning(
                    "Transient error (attempt %d/%d), retrying in %.1fs: %s",
                    attempt + 1, max_retries, delay, e,
                )
                time.sleep(delay)
            else:
                # Non-transient error — don't retry
                raise
