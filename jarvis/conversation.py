import copy
from datetime import datetime, timezone

from jarvis.backends.base import Backend
from jarvis.logger import log
from jarvis.parallel import execute_tools_parallel
from jarvis.tool_registry import ToolRegistry


class Conversation:
    """Manages conversation history and the agent tool loop, backend-agnostic."""

    MAX_TOOL_TURNS = 25  # Safety limit to prevent infinite loops
    MAX_MESSAGES = 100  # Keep conversation manageable

    def __init__(self, backend: Backend, registry: ToolRegistry, system: str, max_tokens: int = 4096):
        self.backend = backend
        self.registry = registry
        self.system = system
        self.max_tokens = max_tokens
        self.messages: list = []
        self.total_tool_calls: int = 0
        self.total_turns: int = 0
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self._checkpoints: list[dict] = []

    def _trim_history(self):
        """Trim old messages to stay within MAX_MESSAGES, keeping recent context.

        Preserves a summary marker at the front if messages are truncated,
        so the conversation doesn't lose all context.
        """
        if len(self.messages) <= self.MAX_MESSAGES:
            return
        # Keep the most recent messages, add a summary note
        trimmed_count = len(self.messages) - self.MAX_MESSAGES
        self.messages = self.messages[-self.MAX_MESSAGES:]
        log.info("Trimmed %d old messages from conversation history", trimmed_count)

    def _call_backend(self, tools):
        """Call backend — retry logic now lives in each backend via jarvis.retry."""
        return self.backend.send(
            messages=self.messages,
            system=self.system,
            tools=tools,
            max_tokens=self.max_tokens,
        )

    def send(self, user_input: str) -> str:
        """Send a message, run the tool loop, return the final text response."""
        self.messages.append(self.backend.format_user_message(user_input))
        tools = self.registry.all_tools()
        turns = 0

        while True:
            response = self._call_backend(tools)
            self.total_input_tokens += response.usage.input_tokens
            self.total_output_tokens += response.usage.output_tokens

            if response.tool_calls:
                turns += 1
                if turns > self.MAX_TOOL_TURNS:
                    self.messages.append(self.backend.format_assistant_message(response))
                    return f"(Stopped after {self.MAX_TOOL_TURNS} tool turns to prevent runaway loop. Last response: {response.text or ''})"

                self.messages.append(self.backend.format_assistant_message(response))
                if len(response.tool_calls) > 1:
                    log.info("Parallel execution of %d tool calls", len(response.tool_calls))
                    results = execute_tools_parallel(self.registry, response.tool_calls)
                else:
                    results = []
                    for tc in response.tool_calls:
                        log.info("tool call: %s", tc.name)
                        result = self.registry.handle_call(tc.name, tc.args)
                        results.append((tc.id, result))

                tool_msg = self.backend.format_tool_results(results)
                # OpenAI returns a list of messages; Claude/Gemini return a single dict
                if isinstance(tool_msg, list):
                    self.messages.extend(tool_msg)
                else:
                    self.messages.append(tool_msg)
            else:
                self.messages.append(self.backend.format_assistant_message(response))
                self._trim_history()
                return response.text or ""

    def save_checkpoint(self, label: str = "") -> dict:
        """Save the current conversation state as a checkpoint.

        Returns a checkpoint dict that can be passed to restore_checkpoint().
        """
        checkpoint = {
            "label": label or f"checkpoint-{len(self._checkpoints)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "messages": copy.deepcopy(self.messages),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "message_count": len(self.messages),
        }
        self._checkpoints.append(checkpoint)
        log.info("Saved checkpoint '%s' (%d messages)", checkpoint["label"], len(self.messages))
        return checkpoint

    def restore_checkpoint(self, index: int = -1) -> bool:
        """Restore conversation to a saved checkpoint.

        Args:
            index: Checkpoint index (-1 for most recent).

        Returns:
            True if restored, False if no checkpoints exist.
        """
        if not self._checkpoints:
            return False
        try:
            checkpoint = self._checkpoints[index]
        except IndexError:
            return False
        self.messages = copy.deepcopy(checkpoint["messages"])
        self.total_input_tokens = checkpoint["total_input_tokens"]
        self.total_output_tokens = checkpoint["total_output_tokens"]
        log.info("Restored checkpoint '%s' (%d messages)", checkpoint["label"], len(self.messages))
        return True

    def list_checkpoints(self) -> list[dict]:
        """Return metadata for all saved checkpoints."""
        return [
            {"index": i, "label": cp["label"], "timestamp": cp["timestamp"], "messages": cp["message_count"]}
            for i, cp in enumerate(self._checkpoints)
        ]

    def clear(self) -> None:
        """Reset conversation history."""
        self.messages.clear()
