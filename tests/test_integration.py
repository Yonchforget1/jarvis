"""Integration test: full conversation flow with mock backend."""

from jarvis.backends.base import Backend, BackendResponse, ToolCall
from jarvis.conversation import Conversation
from jarvis.tool_registry import ToolDef, ToolRegistry


class ScriptedBackend(Backend):
    """Backend that returns scripted responses to test full conversation flows."""

    def __init__(self, script: list[BackendResponse]):
        self._script = list(script)
        self._idx = 0

    def send(self, messages, system, tools, max_tokens=4096):
        resp = self._script[self._idx]
        self._idx += 1
        return resp

    def format_user_message(self, text):
        return {"role": "user", "content": text}

    def format_assistant_message(self, response):
        return {"role": "assistant", "content": response.text or ""}

    def format_tool_results(self, results):
        return {"role": "user", "content": str(results)}


def test_full_conversation_with_tools():
    """Test a multi-turn conversation: text -> tool call -> tool result -> text."""
    backend = ScriptedBackend([
        # Turn 1: greeting
        BackendResponse(text="Hello! How can I help?", tool_calls=[]),
        # Turn 2: uses a tool then responds
        BackendResponse(text=None, tool_calls=[
            ToolCall(id="tc1", name="read_file", args={"path": "test.txt"}),
        ]),
        BackendResponse(text="The file contains: mock content", tool_calls=[]),
    ])

    registry = ToolRegistry()
    registry.register(ToolDef(
        name="read_file",
        description="Read a file.",
        parameters={
            "properties": {"path": {"type": "string", "description": "File path."}},
            "required": ["path"],
        },
        func=lambda path: "mock content",
    ))

    convo = Conversation(backend, registry, "You are a test assistant.", 1000)

    # Turn 1
    response = convo.send("Hi!")
    assert response == "Hello! How can I help?"
    assert len(convo.messages) == 2  # user + assistant

    # Turn 2 with tool call
    response = convo.send("Read test.txt")
    assert "mock content" in response
    # user + assistant(tool) + tool_result + assistant(final)
    # Plus the 2 from turn 1
    assert len(convo.messages) == 6


def test_conversation_clear_resets():
    backend = ScriptedBackend([
        BackendResponse(text="First response", tool_calls=[]),
        BackendResponse(text="After clear", tool_calls=[]),
    ])
    registry = ToolRegistry()
    convo = Conversation(backend, registry, "system", 1000)

    convo.send("msg1")
    assert len(convo.messages) == 2

    convo.clear()
    assert len(convo.messages) == 0

    convo.send("msg2")
    assert len(convo.messages) == 2


def test_conversation_handles_multiple_tool_calls():
    """Backend returns two tool calls in a single response."""
    backend = ScriptedBackend([
        BackendResponse(text=None, tool_calls=[
            ToolCall(id="tc1", name="echo", args={"text": "one"}),
            ToolCall(id="tc2", name="echo", args={"text": "two"}),
        ]),
        BackendResponse(text="Both tools executed.", tool_calls=[]),
    ])

    registry = ToolRegistry()
    registry.register(ToolDef(
        name="echo", description="Echo",
        parameters={"properties": {"text": {"type": "string"}}, "required": ["text"]},
        func=lambda text: f"echo:{text}",
    ))

    convo = Conversation(backend, registry, "system", 1000)
    result = convo.send("Do two things")
    assert result == "Both tools executed."
