from . import filesystem, gamedev, game_engine, shell, web, computer, browser

__all__ = ["register_all"]


def register_all(registry, config=None):
    """Register all built-in tools. Pass config to enable computer/browser tools."""
    filesystem.register(registry)
    shell.register(registry)
    web.register(registry)
    gamedev.register(registry)
    game_engine.register(registry)
    if config:
        computer.register(registry, config)
        browser.register(registry, config)
