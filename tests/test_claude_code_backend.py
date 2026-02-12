"""Tests for ClaudeCodeBackend (unit tests with mocked subprocess)."""

import json
from unittest.mock import patch, MagicMock
from jarvis.backends.claude_code import ClaudeCodeBackend
from jarvis.tool_registry import ToolDef


def _make_backend():
    return ClaudeCodeBackend(config=None)


def _mock_run(result_text, is_error=False):
    """Create a mock subprocess.run result."""
    data = {
        "result": result_text,
        "session_id": "test-session",
        "is_error": is_error,
    }
    mock = MagicMock()
    mock.returncode = 0
    mock.stdout = json.dumps(data)
    mock.stderr = ""
    return mock


def test_send_text_response():
    backend = _make_backend()
    with patch("jarvis.backends.claude_code.subprocess.run", return_value=_mock_run("Hello!")):
        resp = backend.send(
            messages=[{"role": "user", "content": "hi"}],
            system="test",
            tools=[],
        )
    assert resp.text == "Hello!"
    assert resp.tool_calls == []


def test_send_tool_call_response():
    tool_json = json.dumps({
        "tool_calls": [{"id": "c1", "name": "read_file", "args": {"path": "x.txt"}}]
    })
    backend = _make_backend()
    with patch("jarvis.backends.claude_code.subprocess.run", return_value=_mock_run(tool_json)):
        resp = backend.send(
            messages=[{"role": "user", "content": "read x.txt"}],
            system="test",
            tools=[ToolDef("read_file", "Read", {"properties": {}}, lambda: "")],
        )
    assert resp.text is None
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "read_file"


def test_send_error_response():
    backend = _make_backend()
    with patch("jarvis.backends.claude_code.subprocess.run", return_value=_mock_run("bad", is_error=True)):
        resp = backend.send(messages=[], system="", tools=[])
    assert "Error" in resp.text


def test_format_user_message():
    backend = _make_backend()
    msg = backend.format_user_message("hello")
    assert msg == {"role": "user", "content": "hello"}


def test_format_assistant_message_text():
    from jarvis.backends.base import BackendResponse
    backend = _make_backend()
    msg = backend.format_assistant_message(BackendResponse(text="hi"))
    assert msg == {"role": "assistant", "content": "hi"}


def test_format_tool_results():
    backend = _make_backend()
    msg = backend.format_tool_results([("c1", "file contents here")])
    assert msg["role"] == "user"
    assert "c1" in msg["content"]
    assert "file contents here" in msg["content"]


def test_build_prompt_includes_system():
    backend = _make_backend()
    prompt = backend._build_prompt(
        messages=[{"role": "user", "content": "hi"}],
        system="Be helpful",
        tools=[],
    )
    assert "<system>" in prompt
    assert "Be helpful" in prompt
    assert "<user>" in prompt


def test_build_prompt_includes_tools():
    tool = ToolDef("test_tool", "A test", {"properties": {"x": {"type": "string"}}}, lambda x: x)
    backend = _make_backend()
    prompt = backend._build_prompt(
        messages=[],
        system="",
        tools=[tool],
    )
    assert "test_tool" in prompt
    assert "available_tools" in prompt


def test_extract_tool_calls_valid():
    backend = _make_backend()
    text = '{"tool_calls": [{"name": "foo", "args": {"a": 1}}]}'
    calls = backend._extract_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "foo"


def test_extract_tool_calls_plain_text():
    backend = _make_backend()
    calls = backend._extract_tool_calls("Just a normal response")
    assert calls == []


def test_extract_tool_calls_markdown_wrapped():
    backend = _make_backend()
    text = '```json\n{"tool_calls": [{"name": "bar", "args": {}}]}\n```'
    calls = backend._extract_tool_calls(text)
    assert len(calls) == 1
    assert calls[0].name == "bar"


def test_ping_success():
    backend = _make_backend()
    mock = MagicMock()
    mock.returncode = 0
    with patch("jarvis.backends.claude_code.subprocess.run", return_value=mock):
        assert backend.ping() is True


def test_ping_not_installed():
    backend = _make_backend()
    with patch("jarvis.backends.claude_code.subprocess.run", side_effect=FileNotFoundError):
        assert backend.ping() is False
