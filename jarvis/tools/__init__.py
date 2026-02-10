from . import filesystem, gamedev, game_engine, planner_tools, shell, web
from jarvis import tool_chain

__all__ = ["register_all", "register_all_tools"]


def register_all(registry, config=None):
    """Register all built-in tools.

    All tools are always registered.  For local models (Ollama), the tool
    *router* in jarvis/tool_router.py selects the ~8 most relevant tools
    per request so the model context stays small.
    """
    filesystem.register(registry)
    shell.register(registry)
    web.register(registry)
    gamedev.register(registry)
    game_engine.register(registry)
    planner_tools.register(registry)
    tool_chain.register(registry)

    if config and config.api_key:
        # Lazy-load heavy computer vision modules only when an API key is set
        from . import computer, browser
        computer.register(registry, config)
        browser.register(registry, config)


# Alias so both names work across the codebase
register_all_tools = register_all
