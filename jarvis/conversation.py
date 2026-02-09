import copy
from datetime import datetime, timezone

from jarvis.backends.base import Backend
from jarvis.context_manager import estimate_tokens, summarize_messages
from jarvis.logger import log
from jarvis.parallel import execute_tools_parallel
from jarvis.tool_registry import ToolRegistry
from jarvis.tool_router import select_tools


class Conversation:
    """Manages conversation history and the agent tool loop, backend-agnostic."""

    MAX_TOOL_TURNS = 25  # Safety limit to prevent infinite loops
    MAX_MESSAGES = 100  # Keep conversation manageable
    CONTEXT_TOKEN_THRESHOLD = 30000  # Trigger summarization when estimated tokens exceed this

    def __init__(self, backend: Backend, registry: ToolRegistry, system: str,
                 max_tokens: int = 4096, use_tool_router: bool = False):
        self.backend = backend
        self.registry = registry
        self.system = system
        self.max_tokens = max_tokens
        self.use_tool_router = use_tool_router
        self.messages: list = []
        self.total_tool_calls: int = 0
        self.total_turns: int = 0
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self._checkpoints: list[dict] = []

    def _trim_history(self):
        """Trim old messages to stay within limits, using smart summarization.

        First tries to summarize if the context window is getting large.
        Falls back to simple truncation if still over MAX_MESSAGES.
        """
        # Smart summarization when token estimate is high
        est_tokens = estimate_tokens(self.messages)
        if est_tokens > self.CONTEXT_TOKEN_THRESHOLD and len(self.messages) > 20:
            self.messages, removed = summarize_messages(self.messages, keep_recent=20)
            if removed > 0:
                log.info("Context management: summarized %d messages (est. %d tokens)", removed, est_tokens)
                return

        # Fallback: simple truncation
        if len(self.messages) <= self.MAX_MESSAGES:
            return
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

    def _resolve_tools(self, user_input: str) -> list:
        """Return the tool list to send to the backend.

        When *use_tool_router* is enabled (typically for local models), picks
        the ~8 most relevant tools.  Otherwise sends the full registry.
        """
        if self.use_tool_router:
            routed = select_tools(user_input, self.registry)
            log.info("Tool router selected %d tools: %s",
                     len(routed), [t.name for t in routed])
            return routed
        return self.registry.all_tools()

    def send(self, user_input: str) -> str:
        """Send a message, run the tool loop, return the final text response."""
        self.messages.append(self.backend.format_user_message(user_input))
        tools = self._resolve_tools(user_input)
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

    def send_stream(self, user_input: str, event_queue) -> None:
        """Send a message with tool loop, emitting SSE events to event_queue.

        Events emitted:
            thinking  - {"status": "Processing your request..."}
            tool_call - {"id": str, "name": str, "args": dict}
            tool_result - {"id": str, "result": str}
            text      - {"content": str}
            done      - {}
        """
        self.messages.append(self.backend.format_user_message(user_input))
        tools = self._resolve_tools(user_input)
        turns = 0

        event_queue.put({"event": "thinking", "data": {"status": "Processing your request..."}})

        while True:
            response = self._call_backend(tools)
            self.total_input_tokens += response.usage.input_tokens
            self.total_output_tokens += response.usage.output_tokens

            if response.tool_calls:
                turns += 1
                if turns > self.MAX_TOOL_TURNS:
                    self.messages.append(self.backend.format_assistant_message(response))
                    text = f"(Stopped after {self.MAX_TOOL_TURNS} tool turns to prevent runaway loop. Last response: {response.text or ''})"
                    event_queue.put({"event": "text", "data": {"content": text}})
                    event_queue.put({"event": "done", "data": {}})
                    return

                self.messages.append(self.backend.format_assistant_message(response))

                # Execute tools and emit events
                results = []
                for tc in response.tool_calls:
                    event_queue.put({"event": "tool_call", "data": {"id": tc.id, "name": tc.name, "args": tc.args}})
                    log.info("tool call: %s", tc.name)
                    result = self.registry.handle_call(tc.name, tc.args)
                    results.append((tc.id, result))
                    event_queue.put({"event": "tool_result", "data": {"id": tc.id, "result": result}})

                tool_msg = self.backend.format_tool_results(results)
                if isinstance(tool_msg, list):
                    self.messages.extend(tool_msg)
                else:
                    self.messages.append(tool_msg)

                event_queue.put({"event": "thinking", "data": {"status": "Processing tool results..."}})
            else:
                self.messages.append(self.backend.format_assistant_message(response))
                self._trim_history()
                event_queue.put({"event": "text", "data": {"content": response.text or ""}})
                event_queue.put({"event": "done", "data": {}})
                return

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
