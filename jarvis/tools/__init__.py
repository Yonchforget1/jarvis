"""Register all built-in tools."""

from jarvis.tool_registry import ToolRegistry


def register_all_tools(registry: ToolRegistry) -> None:
    from jarvis.tools.filesystem import register as reg_fs
    from jarvis.tools.shell import register as reg_shell
    from jarvis.tools.web import register as reg_web

    reg_fs(registry)
    reg_shell(registry)
    reg_web(registry)

    # Optional tools – only register if deps are available
    try:
        from jarvis.tools.computer import register as reg_computer
        reg_computer(registry)
    except ImportError:
        pass

    try:
        from jarvis.tools.browser import register as reg_browser
        reg_browser(registry)
    except ImportError:
        pass

    try:
        from jarvis.tools.memory_tools import register as reg_memory
        reg_memory(registry)
    except ImportError:
        pass

    try:
        from jarvis.tools.gamedev import register as reg_gamedev
        reg_gamedev(registry)
    except ImportError:
        pass

    from jarvis.tools.planning import register as reg_planning
    reg_planning(registry)

    from jarvis.tools.data import register as reg_data
    reg_data(registry)

    from jarvis.tools.http_tools import register as reg_http
    reg_http(registry)

    # Load plugins from plugins/ directory
    from jarvis.plugin_loader import load_plugins
    load_plugins(registry)
