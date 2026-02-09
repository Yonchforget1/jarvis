from jarvis.backends.base import Backend
from jarvis.tool_registry import ToolRegistry


class Conversation:
    """Manages conversation history and the agent tool loop, backend-agnostic."""

    def __init__(self, backend: Backend, registry: ToolRegistry, system: str, max_tokens: int = 4096):
        self.backend = backend
        self.registry = registry
        self.system = system
        self.max_tokens = max_tokens
        self.messages: list = []

    def send(self, user_input: str) -> str:
        """Send a message, run the tool loop, return the final text response."""
        self.messages.append(self.backend.format_user_message(user_input))
        tools = self.registry.all_tools()

        while True:
            response = self.backend.send(
                messages=self.messages,
                system=self.system,
                tools=tools,
                max_tokens=self.max_tokens,
            )

            if response.tool_calls:
                self.messages.append(self.backend.format_assistant_message(response))
                results = []
                for tc in response.tool_calls:
                    print(f"  [tool: {tc.name}]")
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
                return response.text or ""

    def clear(self):
        """Reset conversation history."""
        self.messages.clear()
