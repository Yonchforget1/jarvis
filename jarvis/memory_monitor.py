"""Memory usage monitoring and alerts.

Periodically checks process memory usage and warns when thresholds
are exceeded. Works with or without psutil.
"""

import logging
import os
import sys
import threading
import time

log = logging.getLogger("jarvis.memory_monitor")

# Default thresholds in MB
WARN_THRESHOLD_MB = int(os.getenv("JARVIS_MEMORY_WARN_MB", "512"))
CRITICAL_THRESHOLD_MB = int(os.getenv("JARVIS_MEMORY_CRITICAL_MB", "1024"))
CHECK_INTERVAL_SECONDS = 60


def get_memory_usage_mb() -> float | None:
    """Get current process memory usage in MB.

    Returns None if memory info is unavailable.
    """
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1024 / 1024
    except ImportError:
        pass

    # Fallback for Linux
    try:
        with open(f"/proc/{os.getpid()}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) / 1024  # kB to MB
    except (FileNotFoundError, ValueError):
        pass

    return None


def get_memory_info() -> dict:
    """Get detailed memory information."""
    info = {"process_mb": get_memory_usage_mb()}

    try:
        import psutil
        proc = psutil.Process()
        mem = proc.memory_info()
        info.update({
            "rss_mb": round(mem.rss / 1024 / 1024, 1),
            "vms_mb": round(mem.vms / 1024 / 1024, 1),
            "percent": round(proc.memory_percent(), 2),
        })
        sys_mem = psutil.virtual_memory()
        info["system"] = {
            "total_mb": round(sys_mem.total / 1024 / 1024, 1),
            "available_mb": round(sys_mem.available / 1024 / 1024, 1),
            "percent_used": sys_mem.percent,
        }
    except ImportError:
        pass

    info["thresholds"] = {
        "warn_mb": WARN_THRESHOLD_MB,
        "critical_mb": CRITICAL_THRESHOLD_MB,
    }

    usage = info.get("process_mb")
    if usage is not None:
        if usage >= CRITICAL_THRESHOLD_MB:
            info["status"] = "critical"
        elif usage >= WARN_THRESHOLD_MB:
            info["status"] = "warning"
        else:
            info["status"] = "ok"
    else:
        info["status"] = "unknown"

    return info


class MemoryMonitor:
    """Background thread that periodically checks memory usage."""

    def __init__(self, check_interval: float = CHECK_INTERVAL_SECONDS):
        self._interval = check_interval
        self._running = False
        self._thread: threading.Thread | None = None
        self._callbacks: list = []

    def start(self) -> None:
        """Start the background monitoring thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="memory-monitor")
        self._thread.start()
        log.info("Memory monitor started (warn=%dMB, critical=%dMB)", WARN_THRESHOLD_MB, CRITICAL_THRESHOLD_MB)

    def stop(self) -> None:
        """Stop the monitoring thread."""
        self._running = False

    def on_threshold(self, callback) -> None:
        """Register a callback for threshold violations.

        Callback signature: callback(level: str, usage_mb: float)
        where level is 'warning' or 'critical'.
        """
        self._callbacks.append(callback)

    def _run(self) -> None:
        while self._running:
            usage = get_memory_usage_mb()
            if usage is not None:
                if usage >= CRITICAL_THRESHOLD_MB:
                    log.critical("Memory usage CRITICAL: %.1f MB (threshold: %d MB)", usage, CRITICAL_THRESHOLD_MB)
                    for cb in self._callbacks:
                        try:
                            cb("critical", usage)
                        except Exception:
                            pass
                elif usage >= WARN_THRESHOLD_MB:
                    log.warning("Memory usage HIGH: %.1f MB (threshold: %d MB)", usage, WARN_THRESHOLD_MB)
                    for cb in self._callbacks:
                        try:
                            cb("warning", usage)
                        except Exception:
                            pass
            time.sleep(self._interval)
