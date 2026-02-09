"""Ollama backend -- local LLM inference with zero API costs.

Uses the Ollama REST API (default: http://localhost:11434) to run models
like llama3, mistral, codellama, etc. entirely on local hardware.

Supports:
- Text generation (chat completion)
- Tool/function calling (Ollama >= 0.3 with compatible models)
- Streaming-ready architecture (non-streaming by default for parity with other backends)
"""

import json
import uuid

import httpx

from .base import Backend, BackendResponse, ToolCall
from jarvis.tool_registry import ToolDef


class OllamaBackend(Backend):
    """Local LLM backend via Ollama REST API."""

    def __init__(
        self,
        model: str = "llama3",
        base_url: str = "http://localhost:11434",
        api_key: str = "",  # accepted for interface parity; unused
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=300.0)  # local models can be slow

    # -- Backend interface ----------------------------------------------------

    def send(self, messages, system, tools, max_tokens=4096):
        """Send a chat completion request to the local Ollama instance."""
        ollama_messages = []
        if system:
            ollama_messages.append({"role": "system", "content": system})
        ollama_messages.extend(messages)

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
            },
        }

        # Add tools if model supports them
        tool_schemas = self._build_tool_schemas(tools)
        if tool_schemas:
            payload["tools"] = tool_schemas

        resp = self._client.post(
            f"{self.base_url}/api/chat",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

        message = data.get("message", {})
        text = message.get("content")
        tool_calls = []

        if message.get("tool_calls"):
            for tc in message["tool_calls"]:
                func = tc.get("function", {})
                tool_calls.append(
                    ToolCall(
                        id=str(uuid.uuid4()),
                        name=func.get("name", ""),
                        args=func.get("arguments", {}),
                    )
                )

        return BackendResponse(text=text, tool_calls=tool_calls, raw=data)

    def format_user_message(self, text):
        return {"role": "user", "content": text}

    def format_assistant_message(self, response):
        msg = {"role": "assistant", "content": response.text or ""}
        if response.tool_calls:
            msg["tool_calls"] = [
                {
                    "function": {
                        "name": tc.name,
                        "arguments": tc.args,
                    }
                }
                for tc in response.tool_calls
            ]
        return msg

    def format_tool_results(self, results):
        return [
            {"role": "tool", "content": result}
            for _tid, result in results
        ]

    # -- Helpers --------------------------------------------------------------

    @staticmethod
    def _build_tool_schemas(tools: list[ToolDef]) -> list[dict]:
        """Convert ToolDef list into Ollama-compatible tool schemas.

        Ollama uses the OpenAI tool format.
        """
        schemas = []
        for t in tools:
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": {
                            "type": "object",
                            "properties": t.parameters.get("properties", {}),
                            "required": t.parameters.get("required", []),
                        },
                    },
                }
            )
        return schemas

    def list_local_models(self) -> list[str]:
        """Return names of models available locally."""
        resp = self._client.get(f"{self.base_url}/api/tags")
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]

    def is_available(self) -> bool:
        """Check whether the Ollama server is reachable."""
        try:
            resp = self._client.get(f"{self.base_url}/api/tags")
            return resp.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False
