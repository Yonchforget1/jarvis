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

    # Computer control tools: always register (they work without API key).
    # Only the AI vision tool (analyze_screen) needs an API key.
    try:
        from . import computer
        computer.register(registry, config)
    except ImportError:
        pass  # pywinauto/pyautogui not installed

    if config and config.api_key:
        # Browser automation requires API key for page analysis
        try:
            from . import browser
            browser.register(registry, config)
        except ImportError:
            pass


# Alias so both names work across the codebase
register_all_tools = register_all
