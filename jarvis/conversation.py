from jarvis.backends.base import Backend
from jarvis.logger import log
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

    def _trim_history(self):
        """Trim old messages to stay within MAX_MESSAGES, keeping recent context."""
        if len(self.messages) > self.MAX_MESSAGES:
            # Keep the most recent messages
            self.messages = self.messages[-self.MAX_MESSAGES:]

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

            if response.tool_calls:
                turns += 1
                if turns > self.MAX_TOOL_TURNS:
                    self.messages.append(self.backend.format_assistant_message(response))
                    return f"(Stopped after {self.MAX_TOOL_TURNS} tool turns to prevent runaway loop. Last response: {response.text or ''})"

                self.messages.append(self.backend.format_assistant_message(response))
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

    def clear(self):
        """Reset conversation history."""
        self.messages.clear()
