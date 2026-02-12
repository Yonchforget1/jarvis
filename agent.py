#!/usr/bin/env python3
"""Jarvis CLI – interactive agent in the terminal."""

from __future__ import annotations

import sys

from rich.console import Console
from rich.markdown import Markdown

from jarvis.backends import create_backend
from jarvis.config import Config
from jarvis.conversation import Conversation
from jarvis.memory import Memory
from jarvis.tool_registry import ToolRegistry
from jarvis.tools import register_all_tools

console = Console()


def main() -> None:
    config = Config.load()
    backend = create_backend(config)
    registry = ToolRegistry()
    register_all_tools(registry)
    memory = Memory()

    # Read past learnings
    learnings = memory.get_learnings(limit=10)
    system = config.system_prompt
    if learnings:
        insights = "\n".join(f"- {l['insight']}" for l in learnings)
        system += f"\n\nPast learnings to build on:\n{insights}"

    convo = Conversation(
        backend=backend,
        registry=registry,
        system=system,
        max_tokens=config.max_tokens,
    )

    tool_count = len(registry.all_tools())
    console.print(f"[bold blue]Jarvis v2.0[/bold blue] | {tool_count} tools | {memory.count} learnings")
    console.print("[dim]Type 'quit' to exit, 'tools' to list tools[/dim]\n")

    while True:
        try:
            user_input = console.input("[bold green]> [/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye.[/dim]")
            break
        if user_input.lower() == "tools":
            for t in registry.all_tools():
                console.print(f"  [cyan]{t.name}[/cyan] – {t.description[:70]}")
            continue

        with console.status("[bold blue]Thinking...[/bold blue]"):
            try:
                response = convo.send(user_input)
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                continue

        console.print(Markdown(response))
        console.print()


if __name__ == "__main__":
    main()
