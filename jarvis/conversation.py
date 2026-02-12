"""Agent conversation loop with tool calling."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.backends.base import Backend, BackendResponse
    from jarvis.tool_registry import ToolRegistry
    from jarvis.tool_router import ToolRouter

log = logging.getLogger("jarvis.conversation")

MAX_TOOL_TURNS = 25
MAX_MESSAGES = 100


class Conversation:
    """Manages a multi-turn conversation with tool calling."""

    def __init__(
        self,
        backend: Backend,
        registry: ToolRegistry,
        system: str = "",
        max_tokens: int = 4096,
        router: ToolRouter | None = None,
    ) -> None:
        self.backend = backend
        self.registry = registry
        self.system = system
        self.max_tokens = max_tokens
        self.router = router
        self.messages: list[dict] = []

        # Tracking
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_tool_calls: int = 0
        self.total_turns: int = 0

    def send(self, user_input: str) -> str:
        """Send a user message and return the final assistant text."""
        self.messages.append(self.backend.format_user_message(user_input))

        # Use smart tool routing if available, otherwise send all tools
        if self.router:
            tools = self.router.select(user_input)
            log.info("Tool router selected %d tools for: %s", len(tools), user_input[:80])
        else:
            tools = self.registry.all_tools()
        tool_turns = 0

        while True:
            response = self.backend.send(
                messages=self.messages,
                system=self.system,
                tools=tools,
                max_tokens=self.max_tokens,
            )
            self._track_usage(response)

            if response.tool_calls:
                tool_turns += 1
                if tool_turns > MAX_TOOL_TURNS:
                    self.messages.append(
                        {"role": "assistant", "content": "[max tool turns reached]"}
                    )
                    return "[Stopped: too many tool calls]"

                # Record the assistant's tool-calling message
                self.messages.append(
                    self.backend.format_assistant_message(response)
                )

                # Execute each tool
                results: list[tuple[str, str]] = []
                for tc in response.tool_calls:
                    self.total_tool_calls += 1
                    log.info("Tool call: %s(%s)", tc.name, tc.args)
                    result = self.registry.handle_call(tc.name, tc.args)
                    results.append((tc.id, result))

                # Format and append tool results
                tool_msg = self.backend.format_tool_results(results)
                if isinstance(tool_msg, list):
                    self.messages.extend(tool_msg)
                else:
                    self.messages.append(tool_msg)

                continue  # Loop back to get next response

            # No tool calls - final text response
            self.total_turns += 1
            self.messages.append(
                self.backend.format_assistant_message(response)
            )
            self._trim_history()
            return response.text or ""

    def get_first_user_message(self) -> str:
        for msg in self.messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    return content[:100]
        return ""

    def _track_usage(self, response: BackendResponse) -> None:
        self.total_input_tokens += response.usage.input_tokens
        self.total_output_tokens += response.usage.output_tokens

    def _trim_history(self) -> None:
        if len(self.messages) > MAX_MESSAGES:
            self.messages = self.messages[-MAX_MESSAGES:]
