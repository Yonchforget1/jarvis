from . import filesystem, gamedev, game_engine, planner_tools, shell, web
from jarvis import tool_chain

__all__ = ["register_all"]


def register_all(registry, config=None):
    """Register all built-in tools. Pass config to enable computer/browser tools."""
    filesystem.register(registry)
    shell.register(registry)
    web.register(registry)
    gamedev.register(registry)
    game_engine.register(registry)
    planner_tools.register(registry)
    tool_chain.register(registry)
    if config:
        # Lazy-load heavy computer vision modules only when needed
        from . import computer, browser

        computer.register(registry, config)
        browser.register(registry, config)
