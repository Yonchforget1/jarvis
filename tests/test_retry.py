"""Tests for jarvis.retry: rate-limit-aware retry logic."""

import pytest

from jarvis.retry import (
    retry_api_call,
    is_transient,
    is_rate_limit,
    RATE_LIMIT_WAIT,
)


class _Counter:
    """Tracks call count for testing retry behavior."""

    def __init__(self, fail_times, error_msg, succeed_value="ok"):
        self.fail_times = fail_times
        self.error_msg = error_msg
        self.succeed_value = succeed_value
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise Exception(self.error_msg)
        return self.succeed_value


def test_is_transient_rate_limit():
    assert is_transient(Exception("rate_limit exceeded"))
    assert is_transient(Exception("HTTP 529 overloaded"))
    assert is_transient(Exception("connection reset"))
    assert is_transient(Exception("502 Bad Gateway"))


def test_is_transient_false():
    assert not is_transient(Exception("invalid api key"))
    assert not is_transient(ValueError("bad model"))


def test_is_rate_limit():
    assert is_rate_limit(Exception("rate_limit exceeded"))
    assert is_rate_limit(Exception("429 Too Many Requests"))
    assert is_rate_limit(Exception("overloaded"))
    assert not is_rate_limit(Exception("connection timeout"))


def test_retry_succeeds_on_first_try():
    fn = _Counter(0, "")
    result = retry_api_call(fn, max_retries=3)
    assert result == "ok"
    assert fn.calls == 1


def test_retry_on_transient_error(monkeypatch):
    """Should retry transient errors with backoff."""
    monkeypatch.setattr("jarvis.retry.TRANSIENT_BASE_DELAY", 0.01)
    fn = _Counter(2, "connection timeout")
    result = retry_api_call(fn, max_retries=5)
    assert result == "ok"
    assert fn.calls == 3


def test_retry_on_rate_limit(monkeypatch):
    """Should retry rate limit errors with 90s wait (mocked to 0.01s)."""
    monkeypatch.setattr("jarvis.retry.RATE_LIMIT_WAIT", 0.01)
    fn = _Counter(1, "rate_limit exceeded")
    result = retry_api_call(fn, max_retries=3)
    assert result == "ok"
    assert fn.calls == 2


def test_no_retry_on_non_transient_error():
    """Should raise immediately for non-transient errors."""
    fn = _Counter(5, "invalid api key")
    with pytest.raises(Exception, match="invalid api key"):
        retry_api_call(fn, max_retries=5)
    assert fn.calls == 1


def test_raises_after_max_retries(monkeypatch):
    """Should raise after exhausting all retries."""
    monkeypatch.setattr("jarvis.retry.TRANSIENT_BASE_DELAY", 0.01)
    fn = _Counter(10, "connection timeout")
    with pytest.raises(Exception, match="connection timeout"):
        retry_api_call(fn, max_retries=3)
    assert fn.calls == 3


def test_retry_passes_args_and_kwargs(monkeypatch):
    """Should pass all args and kwargs through to the function."""
    monkeypatch.setattr("jarvis.retry.TRANSIENT_BASE_DELAY", 0.01)
    received = {}

    def capture(a, b, key1=None):
        received["a"] = a
        received["b"] = b
        received["key1"] = key1
        return "done"

    result = retry_api_call(capture, "x", "y", key1="z", max_retries=3)
    assert result == "done"
    assert received == {"a": "x", "b": "y", "key1": "z"}
