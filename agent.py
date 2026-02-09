"""Jarvis AI Agent -- entry point."""
import os
import sys

# Ensure project root is on the path so the jarvis package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jarvis.config import Config
from jarvis.conversation import Conversation
from jarvis.logger import log
from jarvis.tool_registry import ToolRegistry
from jarvis.backends import create_backend
from jarvis.core import build_system_prompt
from jarvis.memory import Memory


def main() -> None:
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

    # Load persistent memory
    memory = Memory(path=os.path.join(project_root, "memory", "learnings.json"))

    # Build composite system prompt: identity + config + game workflow + memory
    system_prompt = build_system_prompt(config.system_prompt, memory.get_summary())

    # Register tools (pass config to enable computer/browser tools)
    registry = ToolRegistry()
    from jarvis.tools import register_all
    register_all(registry, config)

    # Register memory tools (needs Memory instance)
    from jarvis.tools.memory_tools import register as register_memory_tools

    register_memory_tools(registry, memory)

    registry.load_plugins(os.path.join(project_root, "plugins"))

    log.info("Jarvis AI Agent (%s/%s)", config.backend, config.model)
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


if __name__ == "__main__":
    main()
