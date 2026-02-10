"""Tests for the Ollama backend."""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest

from jarvis.backends.ollama_backend import OllamaBackend
from jarvis.backends.base import BackendResponse, ToolCall
from jarvis.tool_registry import ToolDef


@pytest.fixture
def backend():
    """Return an OllamaBackend with a mocked HTTP client."""
    b = OllamaBackend(model="llama3.2", base_url="http://localhost:11434")
    b._client = MagicMock()
    return b


@pytest.fixture
def sample_tool():
    return ToolDef(
        name="get_weather",
        description="Get the current weather.",
        parameters={
            "properties": {
                "city": {"type": "string", "description": "City name."},
            },
            "required": ["city"],
        },
        func=lambda city: f"Sunny in {city}",
    )


class TestOllamaBackendSend:
    """Test the send() method with mocked HTTP responses."""

    def test_simple_text_response(self, backend):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "message": {"role": "assistant", "content": "Hello! How can I help?"},
            "done": True,
        }
        mock_resp.raise_for_status = MagicMock()
        backend._client.post.return_value = mock_resp

        result = backend.send(
            messages=[{"role": "user", "content": "Hi"}],
            system="You are helpful.",
            tools=[],
        )

        assert isinstance(result, BackendResponse)
        assert result.text == "Hello! How can I help?"
        assert result.tool_calls == []

    def test_tool_call_response(self, backend, sample_tool):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_weather",
                            "arguments": {"city": "New York"},
                        }
                    }
                ],
            },
            "done": True,
        }
        mock_resp.raise_for_status = MagicMock()
        backend._client.post.return_value = mock_resp

        result = backend.send(
            messages=[{"role": "user", "content": "Weather in NY?"}],
            system="Use tools.",
            tools=[sample_tool],
        )

        assert len(result.tool_calls) == 1
        tc = result.tool_calls[0]
        assert tc.name == "get_weather"
        assert tc.args == {"city": "New York"}
        assert tc.id  # UUID should be generated

    def test_system_prompt_prepended(self, backend):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "message": {"role": "assistant", "content": "ok"},
        }
        mock_resp.raise_for_status = MagicMock()
        backend._client.post.return_value = mock_resp

        backend.send(
            messages=[{"role": "user", "content": "test"}],
            system="Be helpful.",
            tools=[],
        )

        call_args = backend._client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        messages = payload["messages"]
        assert messages[0] == {"role": "system", "content": "Be helpful."}
        assert messages[1] == {"role": "user", "content": "test"}

    def test_max_tokens_passed(self, backend):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "message": {"role": "assistant", "content": "ok"},
        }
        mock_resp.raise_for_status = MagicMock()
        backend._client.post.return_value = mock_resp

        backend.send(messages=[], system="", tools=[], max_tokens=2048)

        call_args = backend._client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["options"]["num_predict"] == 2048


class TestOllamaBackendFormatting:
    """Test message formatting methods."""

    def test_format_user_message(self, backend):
        msg = backend.format_user_message("hello")
        assert msg == {"role": "user", "content": "hello"}

    def test_format_assistant_message_text_only(self, backend):
        resp = BackendResponse(text="I can help with that.", tool_calls=[], raw={})
        msg = backend.format_assistant_message(resp)
        assert msg == {"role": "assistant", "content": "I can help with that."}
        assert "tool_calls" not in msg

    def test_format_assistant_message_with_tools(self, backend):
        resp = BackendResponse(
            text="",
            tool_calls=[ToolCall(id="abc", name="get_weather", args={"city": "LA"})],
            raw={},
        )
        msg = backend.format_assistant_message(resp)
        assert msg["role"] == "assistant"
        assert len(msg["tool_calls"]) == 1
        assert msg["tool_calls"][0]["function"]["name"] == "get_weather"

    def test_format_tool_results(self, backend):
        results = [("id1", "Result 1"), ("id2", "Result 2")]
        formatted = backend.format_tool_results(results)
        assert len(formatted) == 2
        assert formatted[0] == {"role": "tool", "content": "Result 1"}
        assert formatted[1] == {"role": "tool", "content": "Result 2"}


class TestOllamaBackendToolSchemas:
    """Test tool schema generation."""

    def test_build_tool_schemas(self, sample_tool):
        schemas = OllamaBackend._build_tool_schemas([sample_tool])
        assert len(schemas) == 1
        schema = schemas[0]
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "get_weather"
        assert "city" in schema["function"]["parameters"]["properties"]

    def test_empty_tools(self):
        schemas = OllamaBackend._build_tool_schemas([])
        assert schemas == []


class TestOllamaBackendHelpers:
    """Test helper methods."""

    def test_is_available_success(self, backend):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        backend._client.get.return_value = mock_resp
        assert backend.is_available() is True

    def test_is_available_failure(self, backend):
        import httpx
        backend._client.get.side_effect = httpx.ConnectError("connection refused")
        assert backend.is_available() is False

    def test_list_local_models(self, backend):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "models": [
                {"name": "llama3.2:latest"},
                {"name": "codellama:7b"},
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        backend._client.get.return_value = mock_resp

        models = backend.list_local_models()
        assert models == ["llama3.2:latest", "codellama:7b"]


class TestOllamaConfig:
    """Test Config works with ollama backend."""

    def test_ollama_no_api_key_required(self, tmp_path, monkeypatch):
        monkeypatch.setattr("jarvis.config.load_dotenv", lambda: None)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        config_file = tmp_path / "config.yaml"
        config_file.write_text("backend: ollama\nmodel: llama3.2\n")

        from jarvis.config import Config
        c = Config.load(str(config_file))
        assert c.backend == "ollama"
        assert c.model == "llama3.2"
        assert c.api_key == ""

    def test_ollama_base_url_from_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr("jarvis.config.load_dotenv", lambda: None)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "backend: ollama\nmodel: llama3.2\nollama_base_url: http://gpu-server:11434\n"
        )

        from jarvis.config import Config
        c = Config.load(str(config_file))
        assert c.ollama_base_url == "http://gpu-server:11434"


class TestBackendFactory:
    """Test that the factory creates OllamaBackend."""

    def test_create_ollama_backend(self, tmp_path, monkeypatch):
        monkeypatch.setattr("jarvis.config.load_dotenv", lambda: None)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        config_file = tmp_path / "config.yaml"
        config_file.write_text("backend: ollama\nmodel: llama3.2\n")

        from jarvis.config import Config
        from jarvis.backends import create_backend

        c = Config.load(str(config_file))
        backend = create_backend(c)
        assert isinstance(backend, OllamaBackend)
        assert backend.model == "llama3.2"
