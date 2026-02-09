"""WebConversation: captures tool calls for web display with streaming support."""

import queue

from jarvis.conversation import Conversation
from jarvis.logger import log


class WebConversation(Conversation):
    """Extended Conversation that captures tool calls for the web API."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pending_tool_calls: list[dict] = []

    def _truncate_result(self, result: str) -> str:
        """Truncate tool result for web display."""
        display = result[:2000]
        if len(result) > 2000:
            display += f"\n... (truncated, {len(result)} chars total)"
        return display

    def send(self, user_input: str) -> str:
        """Send a message, run the tool loop, capture tool calls, return text."""
        self._pending_tool_calls = []
        self.messages.append(self.backend.format_user_message(user_input))
        tools = self.registry.all_tools()
        turns = 0

        while True:
            response = self._call_backend(tools)

            if response.tool_calls:
                turns += 1
                self.total_turns += 1
                if turns > self.MAX_TOOL_TURNS:
                    self.messages.append(self.backend.format_assistant_message(response))
                    return f"(Stopped after {self.MAX_TOOL_TURNS} tool turns to prevent runaway loop. Last response: {response.text or ''})"

                self.messages.append(self.backend.format_assistant_message(response))
                results = []
                for tc in response.tool_calls:
                    log.info("tool call: %s", tc.name)
                    self.total_tool_calls += 1
                    result = self.registry.handle_call(tc.name, tc.args)
                    self._pending_tool_calls.append({
                        "id": tc.id,
                        "name": tc.name,
                        "args": tc.args,
                        "result": self._truncate_result(result),
                    })
                    results.append((tc.id, result))

                tool_msg = self.backend.format_tool_results(results)
                if isinstance(tool_msg, list):
                    self.messages.extend(tool_msg)
                else:
                    self.messages.append(tool_msg)
            else:
                self.messages.append(self.backend.format_assistant_message(response))
                self._trim_history()
                return response.text or ""

    def send_stream(self, user_input: str, event_queue: queue.Queue) -> str:
        """Send a message with real-time SSE events pushed to the queue.

        Events emitted:
            thinking  - Jarvis is calling the LLM
            tool_call - A tool invocation started (id, name, args)
            tool_result - A tool finished (id, name, result)
            text      - Final assistant text response
            done      - Stream complete
            error     - An error occurred
        """
        self._pending_tool_calls = []
        self.messages.append(self.backend.format_user_message(user_input))
        tools = self.registry.all_tools()
        turns = 0

        event_queue.put({"event": "thinking", "data": {"status": "Processing your request..."}})

        while True:
            response = self._call_backend(tools)

            if response.tool_calls:
                turns += 1
                self.total_turns += 1
                if turns > self.MAX_TOOL_TURNS:
                    self.messages.append(self.backend.format_assistant_message(response))
                    text = f"(Stopped after {self.MAX_TOOL_TURNS} tool turns to prevent runaway loop. Last response: {response.text or ''})"
                    event_queue.put({"event": "text", "data": {"content": text}})
                    event_queue.put({"event": "done", "data": {}})
                    return text

                self.messages.append(self.backend.format_assistant_message(response))
                results = []
                for tc in response.tool_calls:
                    log.info("tool call (stream): %s", tc.name)
                    event_queue.put({
                        "event": "tool_call",
                        "data": {"id": tc.id, "name": tc.name, "args": tc.args},
                    })

                    self.total_tool_calls += 1
                    result = self.registry.handle_call(tc.name, tc.args)
                    display_result = self._truncate_result(result)

                    self._pending_tool_calls.append({
                        "id": tc.id, "name": tc.name,
                        "args": tc.args, "result": display_result,
                    })

                    event_queue.put({
                        "event": "tool_result",
                        "data": {"id": tc.id, "name": tc.name, "result": display_result},
                    })
                    results.append((tc.id, result))

                tool_msg = self.backend.format_tool_results(results)
                if isinstance(tool_msg, list):
                    self.messages.extend(tool_msg)
                else:
                    self.messages.append(tool_msg)

                event_queue.put({
                    "event": "thinking",
                    "data": {"status": f"Processing (turn {turns + 1})..."},
                })
            else:
                self.messages.append(self.backend.format_assistant_message(response))
                self._trim_history()
                text = response.text or ""
                event_queue.put({"event": "text", "data": {"content": text}})
                event_queue.put({"event": "done", "data": {}})
                return text

    def get_and_clear_tool_calls(self) -> list[dict]:
        """Return captured tool calls and reset the list."""
        calls = self._pending_tool_calls
        self._pending_tool_calls = []
        return calls
