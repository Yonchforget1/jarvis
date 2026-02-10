try:
    import google.generativeai as genai
    from google.generativeai import types as genai_types

    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

from .base import Backend, BackendResponse, TokenUsage, ToolCall
from jarvis.retry import retry_api_call
from jarvis.tool_registry import ToolDef


class GeminiBackend(Backend):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        if not HAS_GENAI:
            raise ImportError(
                "google-generativeai is not installed. Run: pip install google-generativeai"
            )
        genai.configure(api_key=api_key)
        self.model_name = model

    def send(self, messages, system, tools, max_tokens=4096):
        func_decls = []
        for t in tools:
            schema = t.schema_gemini()
            func_decls.append(
                genai_types.FunctionDeclaration(
                    name=schema["name"],
                    description=schema["description"],
                    parameters=schema["parameters"],
                )
            )
        gemini_tools = [genai_types.Tool(function_declarations=func_decls)]

        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system,
            tools=gemini_tools,
        )
        response = retry_api_call(
            model.generate_content,
            messages,
            generation_config=genai_types.GenerationConfig(max_output_tokens=max_tokens),
        )

        text = None
        tool_calls = []
        for part in response.parts:
            if part.text:
                text = part.text
            elif part.function_call:
                fc = part.function_call
                tool_calls.append(
                    ToolCall(id=fc.name, name=fc.name, args=dict(fc.args))
                )
        usage = TokenUsage()
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            um = response.usage_metadata
            usage = TokenUsage(
                input_tokens=getattr(um, "prompt_token_count", 0),
                output_tokens=getattr(um, "candidates_token_count", 0),
            )
        return BackendResponse(text=text, tool_calls=tool_calls, raw=response, usage=usage)

    def format_user_message(self, text):
        return genai_types.ContentDict(role="user", parts=[text])

    def format_assistant_message(self, response):
        return genai_types.ContentDict(role="model", parts=response.raw.parts)

    def format_tool_results(self, results):
        parts = []
        for call_name, result in results:
            parts.append(
                genai_types.Part(
                    function_response=genai_types.FunctionResponse(
                        name=call_name,
                        response={"result": result},
                    )
                )
            )
        return genai_types.ContentDict(role="user", parts=parts)
