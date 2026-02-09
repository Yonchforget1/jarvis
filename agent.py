"""Jarvis AI Agent -- entry point."""
import os
import sys

# Ensure project root is on the path so the jarvis package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jarvis.config import Config
from jarvis.conversation import Conversation
from jarvis.tool_registry import ToolRegistry
from jarvis.backends import create_backend


def main():
    config = Config.load()
    backend = create_backend(config)
    registry = ToolRegistry()
    registry.load_builtin_tools()
    registry.load_plugins(os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugins"))

    print(f"Jarvis AI Agent ({config.backend}/{config.model})")
    print(f"Tools loaded: {len(registry.all_tools())}")
    print("Commands: 'quit' to exit, '/clear' to reset conversation")
    print("-" * 50)

    convo = Conversation(backend, registry, config.system_prompt, config.max_tokens)
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
