"""Jarvis AI Agent -- entry point."""
import argparse
import os
import sys
import time

_start_time = time.perf_counter()

# Ensure project root is on the path so the jarvis package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jarvis.config import Config
from jarvis.conversation import Conversation
from jarvis.logger import log
from jarvis.tool_registry import ToolRegistry
from jarvis.backends import create_backend
from jarvis.core import build_system_prompt
from jarvis.memory import Memory


def _build_registry(config: Config) -> ToolRegistry:
    """Build and return a fully-loaded tool registry."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    registry = ToolRegistry()
    from jarvis.tools import register_all
    register_all(registry, config)
    from jarvis.tools.memory_tools import register as register_memory_tools
    memory = Memory(path=os.path.join(project_root, "memory", "learnings.json"))
    register_memory_tools(registry, memory)
    registry.load_plugins(os.path.join(project_root, "plugins"))
    return registry


def cmd_tools(args) -> None:
    """List all available tools."""
    config = Config.load()
    registry = _build_registry(config)
    tools = registry.all_tools()

    if args.category:
        tools = [t for t in tools if t.category == args.category]

    # Group by category
    by_category: dict[str, list] = {}
    for t in tools:
        by_category.setdefault(t.category, []).append(t)

    for cat in sorted(by_category):
        print(f"\n[{cat}]")
        for t in sorted(by_category[cat], key=lambda x: x.name):
            print(f"  {t.name:25s} {t.description[:60]}")

    print(f"\nTotal: {len(tools)} tools in {len(by_category)} categories")


def cmd_check_config(args) -> None:
    """Validate configuration."""
    try:
        config = Config.load()
        print(f"Backend:    {config.backend}")
        print(f"Model:      {config.model}")
        print(f"Max tokens: {config.max_tokens}")
        print(f"Timeout:    {config.tool_timeout}s")
        print(f"Max turns:  {config.max_tool_turns}")
        print(f"API key:    {'set' if config.api_key else 'NOT SET'}")
        print("\nConfiguration is valid.")
    except Exception as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_chat(args) -> None:
    """Run the interactive chat (default command)."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    try:
        config = Config.load()
    except ValueError as e:
        log.error("Configuration error: %s", e)
        sys.exit(1)
    except Exception as e:
        log.error("Failed to load config: %s", e)
        sys.exit(1)
    try:
        backend = create_backend(config)
    except Exception as e:
        log.error("Failed to initialize %s backend: %s", config.backend, e)
        sys.exit(1)

    memory = Memory(path=os.path.join(project_root, "memory", "learnings.json"))
    system_prompt = build_system_prompt(config.system_prompt, memory.get_summary())

    registry = _build_registry(config)

    startup_ms = (time.perf_counter() - _start_time) * 1000
    log.info("Jarvis AI Agent (%s/%s) — started in %.0fms", config.backend, config.model, startup_ms)
    log.info("Tools loaded: %d", len(registry.all_tools()))
    if memory.count:
        log.info("Learnings loaded: %d", memory.count)
    print("Commands: 'quit' to exit, '/clear' to reset conversation")
    print("-" * 50)

    convo = Conversation(backend, registry, system_prompt, config.max_tokens)
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
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


def cmd_docs(args) -> None:
    """Generate tool documentation from ToolDef schemas."""
    config = Config.load()
    registry = _build_registry(config)
    tools = sorted(registry.all_tools(), key=lambda t: (t.category, t.name))

    fmt = args.format
    if fmt == "markdown":
        print("# Jarvis Tool Reference\n")
        current_cat = None
        for t in tools:
            if t.category != current_cat:
                current_cat = t.category
                print(f"\n## {current_cat.title()}\n")
            print(f"### `{t.name}`\n")
            print(f"{t.description}\n")
            props = t.parameters.get("properties", {})
            required = set(t.parameters.get("required", []))
            if props:
                print("| Parameter | Type | Required | Description |")
                print("|-----------|------|----------|-------------|")
                for pname, pinfo in props.items():
                    req = "Yes" if pname in required else "No"
                    ptype = pinfo.get("type", "any")
                    desc = pinfo.get("description", "")
                    default = pinfo.get("default")
                    if default is not None:
                        desc += f" (default: `{default}`)"
                    print(f"| `{pname}` | {ptype} | {req} | {desc} |")
                print()
    else:
        for t in tools:
            print(f"[{t.category}] {t.name}")
            print(f"  {t.description}")
            props = t.parameters.get("properties", {})
            required = set(t.parameters.get("required", []))
            for pname, pinfo in props.items():
                req = "*" if pname in required else " "
                ptype = pinfo.get("type", "any")
                desc = pinfo.get("description", "")
                print(f"  {req} {pname} ({ptype}): {desc}")
            print()

    print(f"\n---\nGenerated from {len(tools)} tools")


def cmd_new_plugin(args) -> None:
    """Scaffold a new plugin from a template."""
    name = args.name.lower().replace("-", "_")
    project_root = os.path.dirname(os.path.abspath(__file__))
    plugin_path = os.path.join(project_root, "plugins", f"{name}.py")

    if os.path.exists(plugin_path):
        print(f"Error: Plugin '{name}' already exists at {plugin_path}", file=sys.stderr)
        sys.exit(1)

    template = f'''"""Plugin: {name}

Description: TODO - describe what this plugin does.
Author: Jarvis Team
Version: 1.0.0
"""

from jarvis.tool_registry import ToolDef


def {name}_action(input_text: str) -> str:
    """TODO: Implement the main action for this tool.

    Args:
        input_text: The input to process.

    Returns:
        Result string.
    """
    # TODO: implement
    return f"Processed: {{input_text}}"


def register(registry) -> None:
    """Register tools with the Jarvis tool registry."""
    registry.register(ToolDef(
        name="{name}",
        description="TODO: describe what this tool does.",
        parameters={{
            "properties": {{
                "input_text": {{
                    "type": "string",
                    "description": "The input to process.",
                }},
            }},
            "required": ["input_text"],
        }},
        func={name}_action,
        category="custom",
    ))
'''
    os.makedirs(os.path.dirname(plugin_path), exist_ok=True)
    with open(plugin_path, "w", encoding="utf-8") as f:
        f.write(template)
    print(f"Created plugin scaffold: {plugin_path}")
    print(f"Next steps:")
    print(f"  1. Edit {plugin_path} to implement your tool logic")
    print(f"  2. Run 'python agent.py tools' to verify it loads")
    print(f"  3. Run 'python agent.py test-tool {name}' to test it")


def cmd_test_tool(args) -> None:
    """Test a specific tool interactively."""
    import json as _json
    config = Config.load()
    registry = _build_registry(config)
    tool = registry.get(args.name)
    if not tool:
        print(f"Error: Tool '{args.name}' not found.", file=sys.stderr)
        print(f"Available: {', '.join(t.name for t in registry.all_tools())}")
        sys.exit(1)

    print(f"Testing tool: {tool.name}")
    print(f"Description: {tool.description}")
    print(f"Category: {tool.category}")

    props = tool.parameters.get("properties", {})
    required = set(tool.parameters.get("required", []))

    if args.args_json:
        try:
            tool_args = _json.loads(args.args_json)
        except _json.JSONDecodeError as e:
            print(f"Error parsing JSON args: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # Interactive: prompt for each parameter
        tool_args = {}
        for pname, pinfo in props.items():
            req = " (required)" if pname in required else ""
            ptype = pinfo.get("type", "string")
            desc = pinfo.get("description", "")
            default = pinfo.get("default")

            prompt_str = f"  {pname} ({ptype}){req}"
            if desc:
                prompt_str += f" - {desc}"
            if default is not None:
                prompt_str += f" [{default}]"
            prompt_str += ": "

            try:
                value = input(prompt_str).strip()
            except (EOFError, KeyboardInterrupt):
                print("\nCancelled.")
                return

            if not value and default is not None:
                value = str(default)
            if not value and pname not in required:
                continue
            if ptype == "integer":
                value = int(value)
            elif ptype == "number":
                value = float(value)
            elif ptype == "boolean":
                value = value.lower() in ("true", "1", "yes")
            tool_args[pname] = value

    print(f"\nRunning {tool.name}({tool_args})...")
    print("-" * 50)
    result = registry.handle_call(tool.name, tool_args)
    print(result)
    print("-" * 50)
    print(f"Result length: {len(result)} chars")


def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis AI Agent")
    subparsers = parser.add_subparsers(dest="command")

    # Default: chat
    chat_parser = subparsers.add_parser("chat", help="Start interactive chat (default)")
    chat_parser.set_defaults(func=cmd_chat)

    # tools
    tools_parser = subparsers.add_parser("tools", help="List all available tools")
    tools_parser.add_argument("--category", "-c", help="Filter by category")
    tools_parser.set_defaults(func=cmd_tools)

    # check-config
    config_parser = subparsers.add_parser("check-config", help="Validate configuration")
    config_parser.set_defaults(func=cmd_check_config)

    # new-plugin
    plugin_parser = subparsers.add_parser("new-plugin", help="Scaffold a new plugin")
    plugin_parser.add_argument("name", help="Plugin name (e.g., my_tool)")
    plugin_parser.set_defaults(func=cmd_new_plugin)

    # test-tool
    test_parser = subparsers.add_parser("test-tool", help="Test a specific tool interactively")
    test_parser.add_argument("name", help="Tool name to test")
    test_parser.add_argument("--args", "-a", dest="args_json", help="JSON object of arguments")
    test_parser.set_defaults(func=cmd_test_tool)

    # docs
    docs_parser = subparsers.add_parser("docs", help="Generate tool documentation")
    docs_parser.add_argument("--format", "-f", choices=["text", "markdown"], default="markdown")
    docs_parser.set_defaults(func=cmd_docs)

    args = parser.parse_args()

    if args.command is None:
        cmd_chat(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
