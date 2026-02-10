"""Prometheus-compatible metrics endpoint.

Exposes metrics in Prometheus text exposition format at /api/metrics.
No external dependency required — generates the text format directly.
"""

import time

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
_limiter = Limiter(key_func=get_remote_address)

_session_manager = None
_start_time = time.time()

# Simple in-memory counters (reset on restart)
_counters = {
    "http_requests_total": 0,
    "chat_messages_total": 0,
    "tool_calls_total": 0,
    "tool_errors_total": 0,
    "auth_failures_total": 0,
}


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


def increment(metric: str, value: int = 1):
    """Increment a counter metric."""
    if metric in _counters:
        _counters[metric] += value


@router.get("/metrics", response_class=PlainTextResponse)
@_limiter.limit("5/minute")
async def prometheus_metrics(request: Request):
    """Prometheus-compatible metrics endpoint.

    Returns metrics in text exposition format:
    https://prometheus.io/docs/instrumenting/exposition_formats/
    """
    lines = []

    def gauge(name: str, help_text: str, value: float):
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} gauge")
        lines.append(f"{name} {value}")

    def counter(name: str, help_text: str, value: float):
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} counter")
        lines.append(f"{name} {value}")

    # Uptime
    gauge("jarvis_uptime_seconds", "Time since API server started", round(time.time() - _start_time, 1))

    # Sessions
    active_sessions = _session_manager.active_session_count if _session_manager else 0
    gauge("jarvis_active_sessions", "Number of active sessions", active_sessions)

    # Request counters
    counter("jarvis_http_requests_total", "Total HTTP requests processed", _counters["http_requests_total"])
    counter("jarvis_chat_messages_total", "Total chat messages processed", _counters["chat_messages_total"])
    counter("jarvis_tool_calls_total", "Total tool calls executed", _counters["tool_calls_total"])
    counter("jarvis_tool_errors_total", "Total tool execution errors", _counters["tool_errors_total"])
    counter("jarvis_auth_failures_total", "Total authentication failures", _counters["auth_failures_total"])

    # Token usage across all sessions
    total_input = 0
    total_output = 0
    if _session_manager:
        for session in _session_manager.get_all_sessions():
            total_input += session.conversation.total_input_tokens
            total_output += session.conversation.total_output_tokens

    counter("jarvis_input_tokens_total", "Total input tokens consumed", total_input)
    counter("jarvis_output_tokens_total", "Total output tokens generated", total_output)

    # Tool stats
    if _session_manager:
        all_tool_stats = {}
        for session in _session_manager.get_all_sessions():
            for name, stat in session.conversation.registry.get_stats().items():
                if name not in all_tool_stats:
                    all_tool_stats[name] = {"calls": 0, "errors": 0, "duration_ms": 0}
                all_tool_stats[name]["calls"] += stat.call_count
                all_tool_stats[name]["errors"] += stat.error_count
                all_tool_stats[name]["duration_ms"] += stat.total_duration_ms

        if all_tool_stats:
            lines.append(f"# HELP jarvis_tool_calls Per-tool call counts")
            lines.append(f"# TYPE jarvis_tool_calls counter")
            for name, stats in sorted(all_tool_stats.items()):
                lines.append(f'jarvis_tool_calls{{tool="{name}"}} {stats["calls"]}')

            lines.append(f"# HELP jarvis_tool_duration_ms_total Per-tool total duration")
            lines.append(f"# TYPE jarvis_tool_duration_ms_total counter")
            for name, stats in sorted(all_tool_stats.items()):
                lines.append(f'jarvis_tool_duration_ms_total{{tool="{name}"}} {stats["duration_ms"]:.1f}')

    # Memory usage
    try:
        import psutil
        process = psutil.Process()
        gauge("jarvis_memory_rss_bytes", "Resident set size in bytes", process.memory_info().rss)
        gauge("jarvis_cpu_percent", "CPU usage percentage", process.cpu_percent(interval=None))
    except ImportError:
        pass

    return "\n".join(lines) + "\n"
