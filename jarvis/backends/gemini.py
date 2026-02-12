"""Google Gemini backend using native function calling."""

from __future__ import annotations

import json
import logging
import uuid
from typing import TYPE_CHECKING

from jarvis.backends.base import Backend, BackendResponse, ToolCall, TokenUsage
from jarvis.tool_registry import ToolDef

if TYPE_CHECKING:
    from jarvis.config import Config

log = logging.getLogger("jarvis.backends.gemini")


def _json_schema_to_gemini(schema: dict) -> dict:
    """Convert JSON Schema to Gemini-compatible format (strip unsupported keys)."""
    cleaned = {}
    for key, val in schema.items():
        if key in ("$schema", "additionalProperties"):
            continue
        if key == "properties" and isinstance(val, dict):
            cleaned["properties"] = {
                k: _json_schema_to_gemini(v) for k, v in val.items()
            }
        elif isinstance(val, dict):
            cleaned[key] = _json_schema_to_gemini(val)
        else:
            cleaned[key] = val
    return cleaned


class GeminiBackend(Backend):
    """Backend using Google's Gemini API with native function calling."""

    def __init__(self, config: Config) -> None:
        try:
            from google import genai
        except ImportError:
            raise ImportError("Install google-genai: pip install google-genai")

        self.model = config.model or "gemini-2.0-flash"
        self._client = genai.Client(api_key=config.api_key)

    def send(
        self,
        messages: list,
        system: str,
        tools: list[ToolDef],
        max_tokens: int = 4096,
    ) -> BackendResponse:
        from google.genai import types

        # Build contents
        contents = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Map roles: Gemini uses "user" and "model"
            gemini_role = "model" if role == "assistant" else "user"

            # Handle tool results
            if role == "tool":
                tool_call_id = msg.get("tool_call_id", "")
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part(function_response=types.FunctionResponse(
                        name=tool_call_id,
                        response={"result": content},
                    ))],
                ))
                continue

            if isinstance(content, str):
                contents.append(types.Content(
                    role=gemini_role,
                    parts=[types.Part(text=content)],
                ))
            elif isinstance(content, list):
                # Handle structured content
                parts = []
                for part in content:
                    if isinstance(part, dict) and "text" in part:
                        parts.append(types.Part(text=part["text"]))
                    elif isinstance(part, dict) and "function_call" in part:
                        fc = part["function_call"]
                        parts.append(types.Part(function_call=types.FunctionCall(
                            name=fc["name"],
                            args=fc.get("args", {}),
                        )))
                if parts:
                    contents.append(types.Content(role=gemini_role, parts=parts))

        # Build tool declarations
        tool_declarations = None
        if tools:
            tool_declarations = [types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name=t.name,
                    description=t.description,
                    parameters=_json_schema_to_gemini(t.parameters) if t.parameters else None,
                )
                for t in tools
            ])]

        config = types.GenerateContentConfig(
            system_instruction=system if system else None,
            max_output_tokens=max_tokens,
            tools=tool_declarations,
        )

        response = self._client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        usage = TokenUsage(
            input_tokens=getattr(response.usage_metadata, "prompt_token_count", 0) or 0,
            output_tokens=getattr(response.usage_metadata, "candidates_token_count", 0) or 0,
        )

        # Extract tool calls from response
        tool_calls = []
        text_parts = []
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    fc = part.function_call
                    tool_calls.append(ToolCall(
                        id=fc.name,  # Gemini uses function name as ID
                        name=fc.name,
                        args=dict(fc.args) if fc.args else {},
                    ))
                elif part.text:
                    text_parts.append(part.text)

        if tool_calls:
            return BackendResponse(text=None, tool_calls=tool_calls, raw=response, usage=usage)

        return BackendResponse(text="".join(text_parts), raw=response, usage=usage)

    def format_user_message(self, text: str) -> dict:
        return {"role": "user", "content": text}

    def format_assistant_message(self, response: BackendResponse) -> dict:
        if response.tool_calls:
            return {
                "role": "assistant",
                "content": [
                    {
                        "function_call": {
                            "name": tc.name,
                            "args": tc.args,
                        }
                    }
                    for tc in response.tool_calls
                ],
            }
        return {"role": "assistant", "content": response.text or ""}

    def format_tool_results(self, results: list[tuple[str, str]]) -> list[dict]:
        return [
            {
                "role": "tool",
                "tool_call_id": name,
                "content": result_text,
            }
            for name, result_text in results
        ]
