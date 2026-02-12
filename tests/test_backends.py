"""Tests for OpenAI and Gemini backends."""

from __future__ import annotations

import json
import sys
import pytest
from unittest.mock import MagicMock, patch

from jarvis.backends.base import BackendResponse, ToolCall, TokenUsage
from jarvis.tool_registry import ToolDef


# ── Helpers ──

def _make_openai_config():
    config = MagicMock()
    config.backend = "openai"
    config.model = "gpt-4o"
    config.api_key = "test-key"
    return config


def _make_gemini_config():
    config = MagicMock()
    config.backend = "gemini"
    config.model = "gemini-2.0-flash"
    config.api_key = "test-key"
    return config


@pytest.fixture
def mock_openai():
    """Mock the openai module so import works without installing it."""
    mock_module = MagicMock()
    with patch.dict(sys.modules, {"openai": mock_module}):
        # Clear cached module to force re-import
        sys.modules.pop("jarvis.backends.openai_backend", None)
        from jarvis.backends.openai_backend import OpenAIBackend
        yield OpenAIBackend, mock_module


@pytest.fixture
def mock_genai():
    """Mock the google.genai module."""
    mock_google = MagicMock()
    mock_genai_mod = MagicMock()
    mock_google.genai = mock_genai_mod
    with patch.dict(sys.modules, {
        "google": mock_google,
        "google.genai": mock_genai_mod,
    }):
        sys.modules.pop("jarvis.backends.gemini", None)
        from jarvis.backends.gemini import GeminiBackend
        yield GeminiBackend, mock_genai_mod


# ── OpenAI Backend ──

def test_openai_send_text(mock_openai):
    OpenAIBackend, mock_mod = mock_openai
    mock_client = MagicMock()
    mock_mod.OpenAI.return_value = mock_client

    mock_message = MagicMock()
    mock_message.content = "Hello from GPT!"
    mock_message.tool_calls = None
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 10
    mock_usage.completion_tokens = 5
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage
    mock_client.chat.completions.create.return_value = mock_response

    backend = OpenAIBackend(_make_openai_config())
    result = backend.send(
        messages=[{"role": "user", "content": "hi"}],
        system="You are helpful.",
        tools=[],
    )

    assert result.text == "Hello from GPT!"
    assert result.tool_calls == []
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 5


def test_openai_send_tool_call(mock_openai):
    OpenAIBackend, mock_mod = mock_openai
    mock_client = MagicMock()
    mock_mod.OpenAI.return_value = mock_client

    mock_tc = MagicMock()
    mock_tc.id = "call_123"
    mock_tc.function.name = "read_file"
    mock_tc.function.arguments = '{"path": "/tmp/test.txt"}'
    mock_message = MagicMock()
    mock_message.content = None
    mock_message.tool_calls = [mock_tc]
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = MagicMock(prompt_tokens=20, completion_tokens=10)
    mock_client.chat.completions.create.return_value = mock_response

    backend = OpenAIBackend(_make_openai_config())
    tool = ToolDef("read_file", "Read a file", {"properties": {"path": {"type": "string"}}}, lambda: "")
    result = backend.send(
        messages=[{"role": "user", "content": "read /tmp/test.txt"}],
        system="",
        tools=[tool],
    )

    assert result.text is None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "read_file"
    assert result.tool_calls[0].args == {"path": "/tmp/test.txt"}


def test_openai_format_messages(mock_openai):
    OpenAIBackend, mock_mod = mock_openai
    mock_mod.OpenAI.return_value = MagicMock()
    backend = OpenAIBackend(_make_openai_config())

    msg = backend.format_user_message("hello")
    assert msg == {"role": "user", "content": "hello"}

    resp = BackendResponse(text="hi there")
    msg = backend.format_assistant_message(resp)
    assert msg == {"role": "assistant", "content": "hi there"}

    results = [("call_1", "file content here")]
    tool_msgs = backend.format_tool_results(results)
    assert len(tool_msgs) == 1
    assert tool_msgs[0]["role"] == "tool"
    assert tool_msgs[0]["tool_call_id"] == "call_1"


def test_openai_tool_schema(mock_openai):
    OpenAIBackend, mock_mod = mock_openai
    mock_mod.OpenAI.return_value = MagicMock()
    backend = OpenAIBackend(_make_openai_config())
    tool = ToolDef("test_tool", "A test", {"type": "object", "properties": {}}, lambda: "")
    schema = backend._tool_schema(tool)
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "test_tool"


# ── Gemini Backend ──

def test_gemini_format_messages(mock_genai):
    GeminiBackend, mock_mod = mock_genai
    mock_mod.Client.return_value = MagicMock()
    backend = GeminiBackend(_make_gemini_config())

    msg = backend.format_user_message("hello")
    assert msg == {"role": "user", "content": "hello"}

    resp = BackendResponse(text="hi from gemini")
    msg = backend.format_assistant_message(resp)
    assert msg == {"role": "assistant", "content": "hi from gemini"}


def test_gemini_tool_results(mock_genai):
    GeminiBackend, mock_mod = mock_genai
    mock_mod.Client.return_value = MagicMock()
    backend = GeminiBackend(_make_gemini_config())

    results = [("read_file", "content here")]
    tool_msgs = backend.format_tool_results(results)
    assert len(tool_msgs) == 1
    assert tool_msgs[0]["role"] == "tool"
    assert tool_msgs[0]["tool_call_id"] == "read_file"


def test_gemini_schema_conversion():
    # This doesn't need mocking since it's a pure function
    sys.modules.pop("jarvis.backends.gemini", None)
    # Just import the function directly
    from jarvis.backends.gemini import _json_schema_to_gemini

    schema = {
        "type": "object",
        "$schema": "should-be-removed",
        "additionalProperties": False,
        "properties": {
            "path": {"type": "string", "description": "File path"},
        },
        "required": ["path"],
    }
    converted = _json_schema_to_gemini(schema)
    assert "$schema" not in converted
    assert "additionalProperties" not in converted
    assert converted["properties"]["path"]["type"] == "string"


# ── Backend Factory ──

def test_factory_claude_code():
    from jarvis.backends import create_backend
    config = MagicMock()
    config.backend = "claude_code"
    backend = create_backend(config)
    from jarvis.backends.claude_code import ClaudeCodeBackend
    assert isinstance(backend, ClaudeCodeBackend)


def test_factory_unknown():
    from jarvis.backends import create_backend
    config = MagicMock()
    config.backend = "nonexistent"
    with pytest.raises(ValueError, match="Unknown backend"):
        create_backend(config)


def test_factory_openai(mock_openai):
    OpenAIBackend, mock_mod = mock_openai
    mock_mod.OpenAI.return_value = MagicMock()
    from jarvis.backends import create_backend
    config = _make_openai_config()
    backend = create_backend(config)
    assert type(backend).__name__ == "OpenAIBackend"


def test_factory_gemini(mock_genai):
    GeminiBackend, mock_mod = mock_genai
    mock_mod.Client.return_value = MagicMock()
    from jarvis.backends import create_backend
    config = _make_gemini_config()
    backend = create_backend(config)
    assert type(backend).__name__ == "GeminiBackend"
