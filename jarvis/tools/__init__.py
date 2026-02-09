from . import filesystem, gamedev, game_engine, planner_tools, shell, web
from jarvis import tool_chain

__all__ = ["register_all", "register_all_tools"]


def register_all(registry, config=None):
    """Register built-in tools.

    When *config* is provided and the backend is ``ollama``, only core tools
    (filesystem, shell, web, memory) are registered so that the local model
    is not overwhelmed by dozens of tool schemas.  Cloud backends get the
    full suite.
    """
    # Core tools — always registered
    filesystem.register(registry)
    shell.register(registry)
    web.register(registry)

    is_local = config and config.backend == "ollama"

    if not is_local:
        # Extended tools for cloud backends
        gamedev.register(registry)
        game_engine.register(registry)
        planner_tools.register(registry)
        tool_chain.register(registry)
        if config:
            # Lazy-load heavy computer vision modules only when needed
            from . import computer, browser

            computer.register(registry, config)
            browser.register(registry, config)


# Alias so both names work across the codebase
register_all_tools = register_all
