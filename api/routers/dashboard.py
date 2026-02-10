"""Health check dashboard: HTML page showing system status at a glance."""

import platform
import time

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_session_manager = None
_start_time = time.time()


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


@router.get("/dashboard", response_class=HTMLResponse)
async def health_dashboard():
    """HTML dashboard showing system health, sessions, and metrics."""
    uptime = time.time() - _start_time
    hours, remainder = divmod(int(uptime), 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    sessions = _session_manager.active_session_count if _session_manager else 0
    backend = _session_manager.config.backend if _session_manager else "unknown"
    model = _session_manager.config.model if _session_manager else "unknown"

    # Aggregate token usage
    total_input = 0
    total_output = 0
    total_tool_calls = 0
    if _session_manager:
        for s in _session_manager.get_all_sessions():
            total_input += s.conversation.total_input_tokens
            total_output += s.conversation.total_output_tokens
            total_tool_calls += s.conversation.total_tool_calls

    # Memory info
    mem_str = "N/A"
    cpu_str = "N/A"
    try:
        import psutil
        proc = psutil.Process()
        mem_str = f"{proc.memory_info().rss / 1024 / 1024:.1f} MB"
        cpu_str = f"{proc.cpu_percent(interval=None):.1f}%"
    except ImportError:
        pass

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Jarvis Dashboard</title>
<meta http-equiv="refresh" content="30">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #0f172a; color: #e2e8f0; padding: 2rem; }}
  h1 {{ color: #38bdf8; margin-bottom: 1.5rem; font-size: 1.8rem; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; }}
  .card {{ background: #1e293b; border-radius: 12px; padding: 1.5rem;
           border: 1px solid #334155; }}
  .card h3 {{ color: #94a3b8; font-size: 0.85rem; text-transform: uppercase;
              letter-spacing: 0.05em; margin-bottom: 0.5rem; }}
  .card .value {{ font-size: 1.8rem; font-weight: 700; color: #f1f5f9; }}
  .card .sub {{ font-size: 0.85rem; color: #64748b; margin-top: 0.25rem; }}
  .status {{ display: inline-block; width: 12px; height: 12px; border-radius: 50%;
             background: #22c55e; margin-right: 0.5rem; }}
  .footer {{ margin-top: 2rem; color: #475569; font-size: 0.8rem; text-align: center; }}
</style>
</head>
<body>
<h1><span class="status"></span>Jarvis AI Agent Dashboard</h1>
<div class="grid">
  <div class="card">
    <h3>Status</h3>
    <div class="value">Healthy</div>
    <div class="sub">Uptime: {uptime_str}</div>
  </div>
  <div class="card">
    <h3>Backend</h3>
    <div class="value">{backend}</div>
    <div class="sub">Model: {model}</div>
  </div>
  <div class="card">
    <h3>Active Sessions</h3>
    <div class="value">{sessions}</div>
    <div class="sub">24h TTL auto-cleanup</div>
  </div>
  <div class="card">
    <h3>Input Tokens</h3>
    <div class="value">{total_input:,}</div>
    <div class="sub">Cumulative across all sessions</div>
  </div>
  <div class="card">
    <h3>Output Tokens</h3>
    <div class="value">{total_output:,}</div>
    <div class="sub">Cumulative across all sessions</div>
  </div>
  <div class="card">
    <h3>Tool Calls</h3>
    <div class="value">{total_tool_calls}</div>
    <div class="sub">Total executions</div>
  </div>
  <div class="card">
    <h3>Memory</h3>
    <div class="value">{mem_str}</div>
    <div class="sub">Process RSS</div>
  </div>
  <div class="card">
    <h3>CPU</h3>
    <div class="value">{cpu_str}</div>
    <div class="sub">Process CPU usage</div>
  </div>
  <div class="card">
    <h3>Platform</h3>
    <div class="value">{platform.system()}</div>
    <div class="sub">Python {platform.python_version()}</div>
  </div>
</div>
<div class="footer">
  Auto-refreshes every 30 seconds &middot; Jarvis AI Agent Platform
</div>
</body>
</html>"""
    return HTMLResponse(content=html)
