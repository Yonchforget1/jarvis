import glob
import json
import os
import subprocess
import sys
import tempfile

import anthropic
from ddgs import DDGS
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are Jarvis, a helpful AI assistant. You can use the provided tools to \
answer questions and accomplish tasks. Think step by step before responding."""

tools = [
    {
        "name": "search_web",
        "description": "Search the web for current information on a topic.",
        "input_schema": {
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
    {
        "name": "run_python",
        "description": "Execute a Python code snippet and return the output.",
        "input_schema": {
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
    {
        "name": "run_shell",
        "description": "Run a shell command and return its output. Use for system tasks like git, npm, pip, listing processes, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                }
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file at the given path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute or relative file path to read.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file, creating it if it doesn't exist or overwriting if it does.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The file path to write to.",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file.",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_directory",
        "description": "List files and directories at the given path. Supports glob patterns like '**/*.py'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path or glob pattern. Defaults to current directory.",
                    "default": ".",
                }
            },
            "required": ["path"],
        },
    },
]


def search_web(query: str) -> str:
    """Search the web via DuckDuckGo and return formatted results."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "No results found."
        lines = []
        for r in results:
            lines.append(f"**{r['title']}**\n{r['href']}\n{r['body']}\n")
        return "\n".join(lines)
    except Exception as e:
        return f"Search error: {e}"


def run_python(code: str) -> str:
    """Execute Python code in a subprocess and return stdout/stderr."""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        os.unlink(tmp_path)
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        return output.strip() if output.strip() else "(no output)"
    except subprocess.TimeoutExpired:
        os.unlink(tmp_path)
        return "Error: Code execution timed out (30s limit)."
    except Exception as e:
        return f"Error: {e}"


def run_shell(command: str) -> str:
    """Run a shell command and return stdout/stderr."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n(exit code {result.returncode})"
        return output.strip() if output.strip() else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out (30s limit)."
    except Exception as e:
        return f"Error: {e}"


def read_file(path: str) -> str:
    """Read and return the contents of a file."""
    try:
        path = os.path.expanduser(path)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 50000:
            content = content[:50000] + f"\n\n... (truncated, {len(content)} chars total)"
        return content if content else "(empty file)"
    except Exception as e:
        return f"Error: {e}"


def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    try:
        path = os.path.expanduser(path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote {len(content)} chars to {path}"
    except Exception as e:
        return f"Error: {e}"


def list_directory(path: str) -> str:
    """List directory contents or match a glob pattern."""
    try:
        path = os.path.expanduser(path)
        if any(c in path for c in ("*", "?", "[")):
            matches = sorted(glob.glob(path, recursive=True))
            if not matches:
                return "No matches found."
            return "\n".join(matches)
        if os.path.isdir(path):
            entries = sorted(os.listdir(path))
            lines = []
            for entry in entries:
                full = os.path.join(path, entry)
                prefix = "[DIR] " if os.path.isdir(full) else "      "
                lines.append(f"{prefix}{entry}")
            return "\n".join(lines) if lines else "(empty directory)"
        return f"Error: {path} is not a directory."
    except Exception as e:
        return f"Error: {e}"


def handle_tool_call(name: str, args: dict) -> str:
    """Dispatch tool calls to their implementations."""
    if name == "search_web":
        return search_web(args["query"])
    if name == "run_python":
        return run_python(args["code"])
    if name == "run_shell":
        return run_shell(args["command"])
    if name == "read_file":
        return read_file(args["path"])
    if name == "write_file":
        return write_file(args["path"], args["content"])
    if name == "list_directory":
        return list_directory(args["path"])
    return f"Unknown tool: {name}"


class Conversation:
    """Manages conversation history for multi-turn memory."""

    def __init__(self):
        self.messages: list[dict] = []

    def send(self, user_input: str) -> str:
        """Send a message and run the agent loop, preserving history."""
        self.messages.append({"role": "user", "content": user_input})

        while True:
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=self.messages,
            )

            if response.stop_reason == "tool_use":
                self.messages.append(
                    {"role": "assistant", "content": response.content}
                )
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = handle_tool_call(block.name, block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": result,
                            }
                        )
                self.messages.append({"role": "user", "content": tool_results})
            else:
                self.messages.append(
                    {"role": "assistant", "content": response.content}
                )
                for block in response.content:
                    if hasattr(block, "text"):
                        return block.text
                return ""

    def clear(self):
        """Reset conversation history."""
        self.messages.clear()


def main():
    print("Jarvis AI Agent")
    print("Commands: 'quit' to exit, '/clear' to reset conversation")
    print("-" * 50)
    convo = Conversation()
    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break
        if user_input.lower() == "/clear":
            convo.clear()
            print("(conversation cleared)")
            continue
        if not user_input:
            continue
        response = convo.send(user_input)
        print(f"\nJarvis: {response}")


if __name__ == "__main__":
    main()
