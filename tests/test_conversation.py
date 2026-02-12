"""Tests for conversation loop."""

from jarvis.conversation import Conversation
from jarvis.backends.base import BackendResponse, ToolCall
from tests.conftest import FakeBackend, make_echo_tool
from jarvis.tool_registry import ToolRegistry


def test_simple_text_response():
    backend = FakeBackend([BackendResponse(text="Hello!")])
    reg = ToolRegistry()
    convo = Conversation(backend=reg, registry=reg, system="test")
    # Fix: use backend
    convo = Conversation(backend=backend, registry=reg, system="test")
    result = convo.send("hi")
    assert result == "Hello!"
    assert convo.total_turns == 1


def test_tool_call_and_response():
    backend = FakeBackend([
        BackendResponse(
            text=None,
            tool_calls=[ToolCall(id="c1", name="echo", args={"text": "hi"})],
        ),
        BackendResponse(text="Done!"),
    ])
    reg = ToolRegistry()
    reg.register(make_echo_tool())
    convo = Conversation(backend=backend, registry=reg, system="test")
    result = convo.send("test")
    assert result == "Done!"
    assert convo.total_tool_calls == 1


def test_max_tool_turns():
    """Should stop after MAX_TOOL_TURNS to prevent infinite loops."""
    # Always return tool calls - should eventually stop
    tc = ToolCall(id="c1", name="echo", args={"text": "loop"})
    backend = FakeBackend([BackendResponse(text=None, tool_calls=[tc])])
    reg = ToolRegistry()
    reg.register(make_echo_tool())
    convo = Conversation(backend=backend, registry=reg, system="test")
    result = convo.send("loop forever")
    assert "too many tool calls" in result.lower()


def test_tracks_usage():
    from jarvis.backends.base import TokenUsage

    backend = FakeBackend([
        BackendResponse(text="ok", usage=TokenUsage(input_tokens=100, output_tokens=50)),
    ])
    reg = ToolRegistry()
    convo = Conversation(backend=backend, registry=reg, system="test")
    convo.send("test")
    assert convo.total_input_tokens == 100
    assert convo.total_output_tokens == 50


def test_message_history():
    backend = FakeBackend([BackendResponse(text="Hi there!")])
    reg = ToolRegistry()
    convo = Conversation(backend=backend, registry=reg, system="test")
    convo.send("hello")
    assert len(convo.messages) == 2  # user + assistant
    assert convo.messages[0]["role"] == "user"
    assert convo.messages[1]["role"] == "assistant"


def test_get_first_user_message():
    backend = FakeBackend([BackendResponse(text="ok")])
    reg = ToolRegistry()
    convo = Conversation(backend=backend, registry=reg, system="test")
    convo.send("What is 2+2?")
    assert convo.get_first_user_message() == "What is 2+2?"
