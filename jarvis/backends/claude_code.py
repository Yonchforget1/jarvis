"""Claude Code CLI backend -- routes through the user's Max subscription.

Spawns `claude -p --output-format json` and pipes the prompt via stdin.
Tool calling is done via prompt engineering: we include tool schemas in the
prompt and instruct Claude to respond with a specific JSON format when it
wants to call a tool.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import uuid
from typing import TYPE_CHECKING

from jarvis.backends.base import Backend, BackendResponse, ToolCall, TokenUsage
from jarvis.tool_registry import ToolDef

if TYPE_CHECKING:
    from jarvis.config import Config

log = logging.getLogger("jarvis.backends.claude_code")

_TIMEOUT = 300  # seconds per invocation

_TOOL_CALL_INSTRUCTIONS = """\
You have access to tools. When you need to use a tool, respond with ONLY \
a raw JSON object in this exact format (no markdown, no extra text):
{"tool_calls": [{"id": "call_1", "name": "tool_name", "args": {"param": "value"}}]}

If you do NOT need a tool, respond normally with text. Never mix tool calls \
with regular text in the same response."""


class ClaudeCodeBackend(Backend):
    """Backend that shells out to the `claude` CLI."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config
        self._cli = shutil.which("claude") or "claude"

    # ── send ──────────────────────────────────────────────────

    def send(
        self,
        messages: list,
        system: str,
        tools: list[ToolDef],
        max_tokens: int = 4096,
    ) -> BackendResponse:
        prompt = self._build_prompt(messages, system, tools)

        try:
            proc = subprocess.run(
                [self._cli, "-p", "--output-format", "json"],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "Claude Code CLI not found. "
                "Install: npm install -g @anthropic-ai/claude-code"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Claude Code timed out after {_TIMEOUT}s")

        if proc.returncode != 0:
            stderr = proc.stderr.strip()[:500]
            raise RuntimeError(
                f"Claude Code failed (exit {proc.returncode}): {stderr}"
            )

        # Parse the JSON envelope
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            # Fallback: treat raw stdout as plain text
            return BackendResponse(text=proc.stdout.strip())

        result_text = data.get("result", "")
        is_error = data.get("is_error", False)

        if is_error:
            return BackendResponse(text=f"[Claude Error] {result_text}")

        # Check if Claude responded with tool calls
        tool_calls = self._extract_tool_calls(result_text)

        if tool_calls:
            return BackendResponse(
                text=None, tool_calls=tool_calls, raw=data
            )

        return BackendResponse(text=result_text, raw=data)

    # ── message formatting ────────────────────────────────────

    def format_user_message(self, text: str) -> dict:
        return {"role": "user", "content": text}

    def format_assistant_message(self, response: BackendResponse) -> dict:
        if response.tool_calls:
            payload = json.dumps(
                {
                    "tool_calls": [
                        {"id": tc.id, "name": tc.name, "args": tc.args}
                        for tc in response.tool_calls
                    ]
                }
            )
            return {"role": "assistant", "content": payload}
        return {"role": "assistant", "content": response.text or ""}

    def format_tool_results(
        self, results: list[tuple[str, str]]
    ) -> dict:
        parts = []
        for tool_call_id, result_text in results:
            parts.append(f"[Tool {tool_call_id} result]: {result_text}")
        return {"role": "user", "content": "\n\n".join(parts)}

    # ── internals ─────────────────────────────────────────────

    def _build_prompt(
        self,
        messages: list,
        system: str,
        tools: list[ToolDef],
    ) -> str:
        sections: list[str] = []

        # System prompt
        if system:
            sections.append(f"<system>\n{system}\n</system>")

        # Tool definitions
        if tools:
            tool_block = self._format_tools(tools)
            sections.append(tool_block)

        # Conversation history
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict):
                        text_parts.append(part.get("text", str(part)))
                    else:
                        text_parts.append(str(part))
                content = "\n".join(text_parts)
            sections.append(f"<{role}>\n{content}\n</{role}>")

        return "\n\n".join(sections)

    def _format_tools(self, tools: list[ToolDef]) -> str:
        lines = ["<available_tools>", _TOOL_CALL_INSTRUCTIONS, ""]
        for tool in tools:
            lines.append(f"Name: {tool.name}")
            lines.append(f"Description: {tool.description}")
            if tool.parameters:
                lines.append(
                    f"Parameters: {json.dumps(tool.parameters, indent=2)}"
                )
            lines.append("")
        lines.append("</available_tools>")
        return "\n".join(lines)

    def _extract_tool_calls(self, text: str) -> list[ToolCall]:
        """Try to parse tool calls from Claude's response text."""
        text = text.strip()
        if not text:
            return []

        # Strip markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(
                line for line in lines if not line.strip().startswith("```")
            ).strip()

        try:
            data = json.loads(text)
            if isinstance(data, dict) and "tool_calls" in data:
                calls = []
                for tc in data["tool_calls"]:
                    calls.append(
                        ToolCall(
                            id=tc.get("id", f"call_{uuid.uuid4().hex[:8]}"),
                            name=tc["name"],
                            args=tc.get("args", {}),
                        )
                    )
                return calls
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        return []

    def ping(self) -> bool:
        try:
            proc = subprocess.run(
                [self._cli, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return proc.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
