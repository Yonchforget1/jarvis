"""Plugin auto-discovery and loading.

Scans the plugins/ directory for .py files with a register(registry) function.
Each plugin can register new tools dynamically.
"""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path

from jarvis.tool_registry import ToolRegistry

log = logging.getLogger("jarvis.plugins")

_PLUGINS_DIR = Path(__file__).resolve().parent.parent / "plugins"


def load_plugins(registry: ToolRegistry, plugins_dir: Path | None = None) -> list[str]:
    """Load all plugins from the plugins directory.

    Returns list of loaded plugin names.
    """
    pdir = plugins_dir or _PLUGINS_DIR
    if not pdir.exists():
        return []

    loaded = []
    for path in sorted(pdir.glob("*.py")):
        if path.name.startswith("_"):
            continue

        name = path.stem
        try:
            spec = importlib.util.spec_from_file_location(f"plugins.{name}", str(path))
            if spec is None or spec.loader is None:
                log.warning("Could not load plugin spec: %s", path)
                continue

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "register"):
                before = len(registry.all_tools())
                module.register(registry)
                after = len(registry.all_tools())
                loaded.append(name)
                log.info(
                    "Loaded plugin '%s' – registered %d tools",
                    name,
                    after - before,
                )
            else:
                log.warning("Plugin '%s' has no register() function", name)

        except Exception:
            log.exception("Failed to load plugin '%s'", name)

    return loaded
