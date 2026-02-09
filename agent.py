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

    args = parser.parse_args()

    if args.command is None:
        cmd_chat(args)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
