"""Plugin auto-discovery from installed Python packages.

Discovers Jarvis plugins from installed packages that declare the
'jarvis.plugins' entry point group. This allows third-party plugins
to be installed via pip and automatically detected.

Package authors add to their pyproject.toml:
    [project.entry-points."jarvis.plugins"]
    my_plugin = "my_package.jarvis_plugin:register"
"""

import importlib
import logging

log = logging.getLogger("jarvis.plugin_discovery")


def discover_plugins(registry) -> list[str]:
    """Discover and load plugins from installed packages.

    Scans for packages that declare the 'jarvis.plugins' entry point
    group and calls their register() function.

    Returns list of successfully loaded plugin names.
    """
    loaded = []

    try:
        from importlib.metadata import entry_points
    except ImportError:
        log.debug("importlib.metadata not available, skipping plugin discovery")
        return loaded

    try:
        # Python 3.12+ style
        eps = entry_points(group="jarvis.plugins")
    except TypeError:
        # Fallback for older Python
        try:
            all_eps = entry_points()
            eps = all_eps.get("jarvis.plugins", [])
        except Exception:
            eps = []

    for ep in eps:
        try:
            register_func = ep.load()
            if callable(register_func):
                register_func(registry)
                loaded.append(ep.name)
                log.info("Discovered plugin: %s (from %s)", ep.name, ep.value)
            else:
                log.warning("Plugin entry point %s is not callable", ep.name)
        except Exception as e:
            log.warning("Failed to load discovered plugin %s: %s", ep.name, e)

    if loaded:
        log.info("Auto-discovered %d plugin(s): %s", len(loaded), ", ".join(loaded))

    return loaded


def list_available_plugins() -> list[dict]:
    """List all available plugins from installed packages (without loading them).

    Returns list of dicts with name, module, and package info.
    """
    plugins = []

    try:
        from importlib.metadata import entry_points, metadata
    except ImportError:
        return plugins

    try:
        eps = entry_points(group="jarvis.plugins")
    except TypeError:
        try:
            all_eps = entry_points()
            eps = all_eps.get("jarvis.plugins", [])
        except Exception:
            eps = []

    for ep in eps:
        info = {
            "name": ep.name,
            "module": ep.value,
        }
        # Try to get package metadata
        try:
            dist = ep.dist
            if dist:
                info["package"] = dist.name
                info["version"] = dist.version
        except Exception:
            pass
        plugins.append(info)

    return plugins
