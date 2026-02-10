"""Tests for Conversation class: send, clear, message management, retry logic."""

from unittest.mock import MagicMock, patch

import pytest

from jarvis.backends.base import Backend, BackendResponse, ToolCall
from jarvis.conversation import Conversation
from jarvis.tool_registry import ToolDef, ToolRegistry


class FakeBackend(Backend):
    """Fake backend that returns predefined responses."""

    def __init__(self, responses):
        self._responses = list(responses)
        self._call_count = 0

    def send(self, messages, system, tools, max_tokens=4096):
        resp = self._responses[self._call_count]
        self._call_count += 1
        return resp

    def format_user_message(self, text):
        return {"role": "user", "content": text}

    def format_assistant_message(self, response):
        return {"role": "assistant", "content": response.text or ""}

    def format_tool_results(self, results):
        return {"role": "user", "content": str(results)}


def test_send_simple_response():
    backend = FakeBackend([
        BackendResponse(text="Hello!", tool_calls=[]),
    ])
    registry = ToolRegistry()
    convo = Conversation(backend, registry, "system", 1000)
    result = convo.send("Hi")
    assert result == "Hello!"
    assert len(convo.messages) == 2  # user + assistant


def test_send_with_tool_call():
    backend = FakeBackend([
        BackendResponse(text=None, tool_calls=[
            ToolCall(id="tc1", name="echo", args={"text": "hi"}),
        ]),
        BackendResponse(text="Done!", tool_calls=[]),
    ])
    registry = ToolRegistry()
    registry.register(ToolDef(
        name="echo",
        description="Echo",
        parameters={"properties": {"text": {"type": "string"}}, "required": ["text"]},
        func=lambda text: f"echo: {text}",
    ))
    convo = Conversation(backend, registry, "system", 1000)
    result = convo.send("Run echo")
    assert result == "Done!"
    # user + assistant(tool_call) + tool_result + assistant(final)
    assert len(convo.messages) == 4


def test_max_tool_turns_limit():
    """Should stop after MAX_TOOL_TURNS to prevent infinite loops."""
    # Create responses that always return tool calls
    responses = []
    for i in range(30):
        responses.append(BackendResponse(
            text=f"turn {i}",
            tool_calls=[ToolCall(id=f"tc{i}", name="echo", args={"text": "x"})],
        ))
    backend = FakeBackend(responses)
    registry = ToolRegistry()
    registry.register(ToolDef(
        name="echo",
        description="Echo",
        parameters={"properties": {"text": {"type": "string"}}, "required": ["text"]},
        func=lambda text: text,
    ))
    convo = Conversation(backend, registry, "system", 1000)
    result = convo.send("loop")
    assert "Stopped after" in result


def test_clear():
    backend = FakeBackend([BackendResponse(text="Hi", tool_calls=[])])
    registry = ToolRegistry()
    convo = Conversation(backend, registry, "system", 1000)
    convo.send("Hello")
    assert len(convo.messages) > 0
    convo.clear()
    assert len(convo.messages) == 0


def test_trim_history():
    backend_responses = [BackendResponse(text=f"resp{i}", tool_calls=[]) for i in range(120)]
    backend = FakeBackend(backend_responses)
    registry = ToolRegistry()
    convo = Conversation(backend, registry, "system", 1000)
    for i in range(110):
        convo.send(f"msg{i}")
    # After many sends, messages should be trimmed to MAX_MESSAGES
    assert len(convo.messages) <= convo.MAX_MESSAGES


def test_call_backend_delegates_to_backend():
    """_call_backend delegates directly to backend.send (retry lives in backends)."""
    backend = FakeBackend([BackendResponse(text="ok", tool_calls=[])])
    registry = ToolRegistry()
    convo = Conversation(backend, registry, "system", 1000)
    result = convo._call_backend(registry.all_tools())
    assert result.text == "ok"


def test_call_backend_propagates_errors():
    """_call_backend propagates errors from backend.send."""
    registry = ToolRegistry()
    backend = FakeBackend([])

    def bad_send(messages, system, tools, max_tokens=4096):
        raise ValueError("Invalid model name")

    backend.send = bad_send
    convo = Conversation(backend, registry, "system", 1000)
    with pytest.raises(ValueError, match="Invalid model name"):
        convo._call_backend(registry.all_tools())
