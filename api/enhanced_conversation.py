"""WebConversation: captures tool calls for web display instead of printing."""

from jarvis.conversation import Conversation


class WebConversation(Conversation):
    """Extended Conversation that captures tool calls for the web API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pending_tool_calls: list[dict] = []

    def send(self, user_input: str) -> str:
        """Send a message, run the tool loop, capture tool calls, return text."""
        self._pending_tool_calls = []
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
                    result = self.registry.handle_call(tc.name, tc.args)
                    self._pending_tool_calls.append({
                        "id": tc.id,
                        "name": tc.name,
                        "args": tc.args,
                        "result": result[:2000],
                    })
                    results.append((tc.id, result))

                tool_msg = self.backend.format_tool_results(results)
                if isinstance(tool_msg, list):
                    self.messages.extend(tool_msg)
                else:
                    self.messages.append(tool_msg)
            else:
                self.messages.append(self.backend.format_assistant_message(response))
                return response.text or ""

    def get_and_clear_tool_calls(self) -> list[dict]:
        """Return captured tool calls and reset the list."""
        calls = self._pending_tool_calls
        self._pending_tool_calls = []
        return calls
