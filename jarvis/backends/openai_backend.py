import json

from openai import OpenAI

from .base import Backend, BackendResponse, ToolCall
from jarvis.tool_registry import ToolDef


class OpenAIBackend(Backend):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def send(self, messages, system, tools, max_tokens=4096):
        # OpenAI uses a system message prepended to the conversation
        full_messages = [{"role": "system", "content": system}] + messages
        tool_schemas = [t.schema_openai() for t in tools]

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=full_messages,
            tools=tool_schemas if tool_schemas else None,
        )
        choice = response.choices[0]
        text = choice.message.content
        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        args=json.loads(tc.function.arguments),
                    )
                )
        return BackendResponse(text=text, tool_calls=tool_calls, raw=choice.message)

    def format_user_message(self, text):
        return {"role": "user", "content": text}

    def format_assistant_message(self, response):
        msg = {"role": "assistant", "content": response.raw.content}
        if response.raw.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in response.raw.tool_calls
            ]
        return msg

    def format_tool_results(self, results):
        # OpenAI expects one message per tool result with role "tool"
        return [
            {"role": "tool", "tool_call_id": tid, "content": result}
            for tid, result in results
        ]
