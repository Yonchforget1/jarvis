from . import filesystem, gamedev, shell, web


def register_all(registry):
    """Register all built-in tools."""
    filesystem.register(registry)
    shell.register(registry)
    web.register(registry)
    gamedev.register(registry)
