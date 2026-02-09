"""Tests for AI backends: Claude, OpenAI, Gemini — all using mocked API calls."""

from unittest.mock import MagicMock, patch

import pytest

from jarvis.backends.base import Backend, BackendResponse, ToolCall
from jarvis.tool_registry import ToolDef


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_tool():
    return ToolDef(
        name="echo",
        description="Echo text.",
        parameters={
            "properties": {"text": {"type": "string", "description": "Text."}},
            "required": ["text"],
        },
        func=lambda text: text,
    )


# ---------------------------------------------------------------------------
# ClaudeBackend
# ---------------------------------------------------------------------------

class TestClaudeBackend:
    def _make_backend(self):
        with patch("jarvis.backends.claude.anthropic") as mock_anthropic:
            from jarvis.backends.claude import ClaudeBackend
            backend = ClaudeBackend(api_key="test-key", model="test-model")
            return backend, mock_anthropic

    def test_send_text_response(self):
        backend, mock_anthropic = self._make_backend()
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Hello!"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        backend.client.messages.create = MagicMock(return_value=mock_response)

        with patch("jarvis.backends.claude.retry_api_call", side_effect=lambda fn, **kw: fn(**kw)):
            result = backend.send([], "system", [], max_tokens=100)

        assert result.text == "Hello!"
        assert result.tool_calls == []

    def test_send_tool_call_response(self):
        backend, _ = self._make_backend()
        mock_block = MagicMock()
        mock_block.type = "tool_use"
        mock_block.id = "tc1"
        mock_block.name = "echo"
        mock_block.input = {"text": "hi"}
        delattr(mock_block, "text")  # no text attribute
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        backend.client.messages.create = MagicMock(return_value=mock_response)

        with patch("jarvis.backends.claude.retry_api_call", side_effect=lambda fn, **kw: fn(**kw)):
            result = backend.send([], "system", [_sample_tool()])

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "echo"
        assert result.tool_calls[0].args == {"text": "hi"}

    def test_format_user_message(self):
        backend, _ = self._make_backend()
        msg = backend.format_user_message("hello")
        assert msg == {"role": "user", "content": "hello"}

    def test_format_tool_results(self):
        backend, _ = self._make_backend()
        result = backend.format_tool_results([("id1", "result1")])
        assert result["role"] == "user"
        assert len(result["content"]) == 1
        assert result["content"][0]["tool_use_id"] == "id1"


# ---------------------------------------------------------------------------
# OpenAIBackend
# ---------------------------------------------------------------------------

openai = pytest.importorskip("openai", reason="openai package not installed")


class TestOpenAIBackend:
    def _make_backend(self):
        # Import the module first so it's in sys.modules before patching
        import jarvis.backends.openai_backend
        with patch.object(jarvis.backends.openai_backend, "OpenAI") as MockOpenAI:
            from jarvis.backends.openai_backend import OpenAIBackend
            backend = OpenAIBackend(api_key="test-key", model="gpt-test")
            return backend, MockOpenAI

    def test_send_text_response(self):
        backend, _ = self._make_backend()
        mock_choice = MagicMock()
        mock_choice.message.content = "Hi!"
        mock_choice.message.tool_calls = None
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        backend.client.chat.completions.create = MagicMock(return_value=mock_response)

        with patch("jarvis.backends.openai_backend.retry_api_call", side_effect=lambda fn, **kw: fn(**kw)):
            result = backend.send([], "system", [])

        assert result.text == "Hi!"
        assert result.tool_calls == []

    def test_format_user_message(self):
        backend, _ = self._make_backend()
        msg = backend.format_user_message("test")
        assert msg == {"role": "user", "content": "test"}

    def test_format_tool_results(self):
        backend, _ = self._make_backend()
        results = backend.format_tool_results([("id1", "result1"), ("id2", "result2")])
        assert isinstance(results, list)
        assert len(results) == 2
        assert results[0]["role"] == "tool"
        assert results[0]["tool_call_id"] == "id1"


# ---------------------------------------------------------------------------
# Backend factory
# ---------------------------------------------------------------------------

class TestBackendFactory:
    def test_create_claude(self):
        with patch("jarvis.backends.claude.anthropic"):
            from jarvis.backends import create_backend
            config = MagicMock()
            config.backend = "claude"
            config.api_key = "test-key"
            config.model = "test-model"
            backend = create_backend(config)
            assert backend is not None

    def test_create_unknown_raises(self):
        from jarvis.backends import create_backend
        config = MagicMock()
        config.backend = "unknown_backend"
        with pytest.raises(ValueError, match="Unknown backend"):
            create_backend(config)
