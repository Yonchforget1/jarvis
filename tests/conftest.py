"""Shared test fixtures."""

import os
# Disable rate limiting during tests
os.environ["JARVIS_RATE_LIMIT"] = "0"

import pytest
from jarvis.tool_registry import ToolDef, ToolRegistry
from jarvis.backends.base import Backend, BackendResponse, ToolCall, TokenUsage

from tests.mock_db import MockDB


@pytest.fixture(autouse=True)
def mock_database(monkeypatch):
    """Replace the global db object's methods with an in-memory mock for all tests."""
    from api.db import db as real_db

    mock = MockDB()
    # Replace methods on the real singleton so all modules see the mock
    for attr in [
        "insert", "select", "update", "delete", "upsert",
        "count", "rpc", "health_check",
    ]:
        monkeypatch.setattr(real_db, attr, getattr(mock, attr))
    monkeypatch.setattr(real_db, "available", True)
    yield mock


class FakeBackend(Backend):
    """Backend that returns pre-configured responses for testing."""

    def __init__(self, responses: list[BackendResponse]) -> None:
        self._responses = list(responses)
        self._idx = 0

    def send(self, messages, system, tools, max_tokens=4096):
        resp = self._responses[self._idx]
        self._idx = min(self._idx + 1, len(self._responses) - 1)
        return resp

    def format_user_message(self, text):
        return {"role": "user", "content": text}

    def format_assistant_message(self, response):
        return {"role": "assistant", "content": response.text or ""}

    def format_tool_results(self, results):
        return {
            "role": "user",
            "content": "\n".join(f"[{tid}]: {r}" for tid, r in results),
        }


def make_echo_tool() -> ToolDef:
    return ToolDef(
        name="echo",
        description="Echo the input",
        parameters={
            "properties": {"text": {"type": "string", "description": "Text to echo"}},
            "required": ["text"],
        },
        func=lambda text: f"echo: {text}",
    )


@pytest.fixture
def registry():
    r = ToolRegistry()
    r.register(make_echo_tool())
    return r


@pytest.fixture
def echo_tool():
    return make_echo_tool()
