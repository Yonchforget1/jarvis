import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()

SYSTEM_PROMPT = """You are Jarvis, a helpful AI assistant. You can use the provided tools to \
answer questions and accomplish tasks. Think step by step before responding."""

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for current information on a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_python",
            "description": "Execute a Python code snippet and return the output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to execute.",
                    }
                },
                "required": ["code"],
            },
        },
    },
]


def handle_tool_call(name: str, args: dict) -> str:
    """Dispatch tool calls to their implementations."""
    if name == "search_web":
        return f"[search_web stub] No results for: {args['query']}"
    if name == "run_python":
        try:
            exec_globals: dict = {}
            exec(args["code"], exec_globals)
            return str(exec_globals.get("result", "Code executed successfully."))
        except Exception as e:
            return f"Error: {e}"
    return f"Unknown tool: {name}"


def run_agent(user_input: str) -> str:
    """Run the agent loop: send message, handle tool calls, return final answer."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]

    while True:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
        )
        choice = response.choices[0]

        if choice.finish_reason == "tool_calls":
            messages.append(choice.message)
            for tool_call in choice.message.tool_calls:
                import json

                args = json.loads(tool_call.function.arguments)
                result = handle_tool_call(tool_call.function.name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )
        else:
            return choice.message.content


def main():
    print("Jarvis AI Agent (type 'quit' to exit)")
    print("-" * 40)
    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break
        if not user_input:
            continue
        response = run_agent(user_input)
        print(f"\nJarvis: {response}")


if __name__ == "__main__":
    main()
