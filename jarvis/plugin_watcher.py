"""Hot-reload for plugins: watch filesystem for changes and reload.

Uses a simple polling approach (no external dependency like watchdog)
to detect modified plugin files and re-register their tools.
"""

import importlib.util
import logging
import os
import threading
import time

log = logging.getLogger("jarvis.plugin_watcher")


class PluginWatcher:
    """Watches the plugins directory for changes and hot-reloads modified plugins."""

    def __init__(self, registry, plugins_dir: str, poll_interval: float = 2.0):
        self.registry = registry
        self.plugins_dir = plugins_dir
        self.poll_interval = poll_interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._mtimes: dict[str, float] = {}
        self._scan_initial()

    def _scan_initial(self) -> None:
        """Record initial modification times."""
        if not os.path.isdir(self.plugins_dir):
            return
        for filename in os.listdir(self.plugins_dir):
            if filename.startswith("_") or not filename.endswith(".py"):
                continue
            filepath = os.path.join(self.plugins_dir, filename)
            self._mtimes[filepath] = os.path.getmtime(filepath)

    def start(self) -> None:
        """Start watching for plugin changes."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True, name="plugin-watcher")
        self._thread.start()
        log.info("Plugin watcher started for %s (poll every %.1fs)", self.plugins_dir, self.poll_interval)

    def stop(self) -> None:
        """Stop watching."""
        self._running = False

    def _watch_loop(self) -> None:
        while self._running:
            try:
                self._check_changes()
            except Exception as e:
                log.exception("Plugin watcher error: %s", e)
            time.sleep(self.poll_interval)

    def _check_changes(self) -> None:
        if not os.path.isdir(self.plugins_dir):
            return

        current_files = set()
        for filename in os.listdir(self.plugins_dir):
            if filename.startswith("_") or not filename.endswith(".py"):
                continue
            filepath = os.path.join(self.plugins_dir, filename)
            current_files.add(filepath)
            mtime = os.path.getmtime(filepath)

            if filepath not in self._mtimes:
                # New plugin added
                log.info("New plugin detected: %s", filename)
                self._load_plugin(filepath, filename)
                self._mtimes[filepath] = mtime
            elif mtime != self._mtimes[filepath]:
                # Plugin modified
                log.info("Plugin modified, reloading: %s", filename)
                self._load_plugin(filepath, filename)
                self._mtimes[filepath] = mtime

        # Check for removed plugins
        removed = set(self._mtimes.keys()) - current_files
        for filepath in removed:
            filename = os.path.basename(filepath)
            log.info("Plugin removed: %s", filename)
            del self._mtimes[filepath]

    def _load_plugin(self, filepath: str, filename: str) -> None:
        """Load or reload a single plugin file."""
        module_name = f"plugins.{filename[:-3]}"
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            if hasattr(module, "register"):
                module.register(self.registry)
                log.info("Plugin %s (re)loaded successfully", filename)
            else:
                log.warning("Plugin %s has no register() function", filename)
        except Exception as e:
            log.error("Failed to load plugin %s: %s", filename, e)
