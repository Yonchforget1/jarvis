from . import filesystem, gamedev, shell, web, computer, browser


def register_all(registry, config=None):
    """Register all built-in tools. Pass config to enable computer/browser tools."""
    filesystem.register(registry)
    shell.register(registry)
    web.register(registry)
    gamedev.register(registry)
    if config:
        computer.register(registry, config)
        browser.register(registry, config)
