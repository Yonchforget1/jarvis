"""Anthropic Claude API backend with native tool_use support."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from jarvis.backends.base import Backend, BackendResponse, ToolCall, TokenUsage
from jarvis.tool_registry import ToolDef

if TYPE_CHECKING:
    from jarvis.config import Config

log = logging.getLogger("jarvis.backends.anthropic")


class AnthropicBackend(Backend):
    """Backend using the Anthropic Messages API with native tool use."""

    def __init__(self, config: Config) -> None:
        try:
            import anthropic
        except ImportError:
            raise ImportError("Install anthropic: pip install anthropic")

        self.model = config.model or "claude-sonnet-4-5-20250929"
        self._client = anthropic.Anthropic(api_key=config.api_key)

    def send(
        self,
        messages: list,
        system: str,
        tools: list[ToolDef],
        max_tokens: int = 4096,
    ) -> BackendResponse:
        kwargs: dict = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = [self._tool_schema(t) for t in tools]

        response = self._client.messages.create(**kwargs)

        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

        # Extract tool use blocks and text blocks
        tool_calls = []
        text_parts = []

        for block in response.content:
            if block.type == "tool_use":
                tool_calls.append(ToolCall(
                    id=block.id,
                    name=block.name,
                    args=block.input if isinstance(block.input, dict) else {},
                ))
            elif block.type == "text":
                text_parts.append(block.text)

        if tool_calls:
            return BackendResponse(
                text=None, tool_calls=tool_calls, raw=response, usage=usage
            )

        return BackendResponse(
            text="\n".join(text_parts), raw=response, usage=usage
        )

    def format_user_message(self, text: str) -> dict:
        return {"role": "user", "content": text}

    def format_assistant_message(self, response: BackendResponse) -> dict:
        if response.tool_calls:
            content = []
            # Include any text that came with tool calls
            if response.raw and hasattr(response.raw, "content"):
                for block in response.raw.content:
                    if block.type == "text":
                        content.append({"type": "text", "text": block.text})
                    elif block.type == "tool_use":
                        content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })
            else:
                # Fallback: construct from tool_calls
                for tc in response.tool_calls:
                    content.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.args,
                    })
            return {"role": "assistant", "content": content}
        return {"role": "assistant", "content": response.text or ""}

    def format_tool_results(self, results: list[tuple[str, str]]) -> dict:
        """Format tool results as a single user message with tool_result blocks."""
        content = []
        for tool_use_id, result_text in results:
            content.append({
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": result_text,
            })
        return {"role": "user", "content": content}

    def _tool_schema(self, tool: ToolDef) -> dict:
        """Convert ToolDef to Anthropic tool schema format."""
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.parameters,
        }
