"""OpenAI backend using native function calling."""

from __future__ import annotations

import json
import logging
import uuid
from typing import TYPE_CHECKING

from jarvis.backends.base import Backend, BackendResponse, ToolCall, TokenUsage
from jarvis.tool_registry import ToolDef

if TYPE_CHECKING:
    from jarvis.config import Config

log = logging.getLogger("jarvis.backends.openai")


class OpenAIBackend(Backend):
    """Backend using the OpenAI API with native tool calling."""

    def __init__(self, config: Config) -> None:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("Install openai: pip install openai")

        self.model = config.model or "gpt-4o"
        self._client = OpenAI(api_key=config.api_key)

    def send(
        self,
        messages: list,
        system: str,
        tools: list[ToolDef],
        max_tokens: int = 4096,
    ) -> BackendResponse:
        api_messages = []
        if system:
            api_messages.append({"role": "system", "content": system})
        api_messages.extend(messages)

        kwargs: dict = {
            "model": self.model,
            "messages": api_messages,
            "max_tokens": max_tokens,
        }

        if tools:
            kwargs["tools"] = [self._tool_schema(t) for t in tools]

        response = self._client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        usage = TokenUsage(
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
        )

        # Extract tool calls
        if message.tool_calls:
            calls = []
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    args=args,
                ))
            return BackendResponse(text=None, tool_calls=calls, raw=response, usage=usage)

        return BackendResponse(text=message.content or "", raw=response, usage=usage)

    def format_user_message(self, text: str) -> dict:
        return {"role": "user", "content": text}

    def format_assistant_message(self, response: BackendResponse) -> dict:
        if response.tool_calls:
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.args),
                        },
                    }
                    for tc in response.tool_calls
                ],
            }
        return {"role": "assistant", "content": response.text or ""}

    def format_tool_results(self, results: list[tuple[str, str]]) -> list[dict]:
        return [
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": result_text,
            }
            for tool_call_id, result_text in results
        ]

    def _tool_schema(self, tool: ToolDef) -> dict:
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
