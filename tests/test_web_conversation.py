"""Tests for WebConversation (api/enhanced_conversation.py)."""

from jarvis.backends.base import BackendResponse, ToolCall, Backend
from jarvis.tool_registry import ToolDef, ToolRegistry
from api.enhanced_conversation import WebConversation


class FakeBackend(Backend):
    def __init__(self, responses):
        self._responses = list(responses)
        self._idx = 0

    def send(self, messages, system, tools, max_tokens=4096):
        resp = self._responses[self._idx]
        self._idx += 1
        return resp

    def format_user_message(self, text):
        return {"role": "user", "content": text}

    def format_assistant_message(self, response):
        return {"role": "assistant", "content": response.text or ""}

    def format_tool_results(self, results):
        return {"role": "user", "content": str(results)}


def test_web_conversation_captures_tool_calls():
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
    convo = WebConversation(backend=backend, registry=registry, system="test", max_tokens=100)
    result = convo.send("test")
    assert result == "Done!"

    calls = convo.get_and_clear_tool_calls()
    assert len(calls) == 1
    assert calls[0]["name"] == "echo"
    assert "echo: hi" in calls[0]["result"]


def test_web_conversation_clears_tool_calls():
    backend = FakeBackend([
        BackendResponse(text="Hi", tool_calls=[]),
    ])
    registry = ToolRegistry()
    convo = WebConversation(backend=backend, registry=registry, system="test", max_tokens=100)
    convo.send("test")
    calls = convo.get_and_clear_tool_calls()
    assert calls == []
    # Calling again returns empty
    assert convo.get_and_clear_tool_calls() == []


def test_web_conversation_tracks_stats():
    backend = FakeBackend([
        BackendResponse(text=None, tool_calls=[
            ToolCall(id="tc1", name="echo", args={"text": "x"}),
        ]),
        BackendResponse(text="ok", tool_calls=[]),
    ])
    registry = ToolRegistry()
    registry.register(ToolDef(
        name="echo", description="e",
        parameters={"properties": {"text": {"type": "string"}}, "required": ["text"]},
        func=lambda text: text,
    ))
    convo = WebConversation(backend=backend, registry=registry, system="test", max_tokens=100)
    convo.send("test")
    assert convo.total_tool_calls == 1
    assert convo.total_turns == 1
