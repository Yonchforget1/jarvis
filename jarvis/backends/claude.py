import anthropic
from .base import Backend, BackendResponse, ToolCall
from jarvis.tool_registry import ToolDef


class ClaudeBackend(Backend):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def send(self, messages, system, tools, max_tokens=4096):
        tool_schemas = [t.schema_anthropic() for t in tools]
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            tools=tool_schemas,
            messages=messages,
        )
        text = None
        tool_calls = []
        for block in response.content:
            if hasattr(block, "text"):
                text = block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, args=block.input)
                )
        return BackendResponse(text=text, tool_calls=tool_calls, raw=response)

    def format_user_message(self, text):
        return {"role": "user", "content": text}

    def format_assistant_message(self, response):
        return {"role": "assistant", "content": response.raw.content}

    def format_tool_results(self, results):
        return {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": tid, "content": result}
                for tid, result in results
            ],
        }
