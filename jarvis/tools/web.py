"""Web tools: search and fetch with SSRF protection."""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

from jarvis.tool_registry import ToolDef, ToolRegistry

# Private/reserved IP ranges that must be blocked (SSRF protection)
_BLOCKED_RANGES = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def _is_private_url(url: str) -> bool:
    """Check if a URL resolves to a private/internal IP."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        if hostname in ("localhost", ""):
            return True
        addr = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(addr)
        return any(ip in net for net in _BLOCKED_RANGES)
    except (socket.gaierror, ValueError):
        return False


def search_web(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "Error: duckduckgo_search not installed (pip install duckduckgo-search)"

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return f"No results found for '{query}'"
        lines = []
        for r in results:
            lines.append(f"**{r.get('title', 'Untitled')}**")
            lines.append(f"  {r.get('href', '')}")
            lines.append(f"  {r.get('body', '')}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Search error: {e}"


def fetch_url(url: str, max_chars: int = 10000) -> str:
    """Fetch a URL and return its text content."""
    if _is_private_url(url):
        return "Error: access to internal/private URLs is blocked (SSRF protection)"

    try:
        import httpx
    except ImportError:
        return "Error: httpx not installed"

    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")

            if "html" in content_type:
                try:
                    from bs4 import BeautifulSoup

                    soup = BeautifulSoup(resp.text, "lxml")
                    # Remove script/style tags
                    for tag in soup(["script", "style", "nav", "footer"]):
                        tag.decompose()
                    text = soup.get_text(separator="\n", strip=True)
                except ImportError:
                    text = resp.text
            else:
                text = resp.text

            if len(text) > max_chars:
                text = text[:max_chars] + f"\n... (truncated, {len(resp.text)} total chars)"
            return text
    except httpx.HTTPStatusError as e:
        return f"HTTP error {e.response.status_code}: {e}"
    except Exception as e:
        return f"Fetch error: {e}"


def register(registry: ToolRegistry) -> None:
    registry.register(ToolDef(
        name="search_web",
        description="Search the web using DuckDuckGo and return results",
        parameters={
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Max results (default 5)"},
            },
            "required": ["query"],
        },
        func=search_web,
    ))
    registry.register(ToolDef(
        name="fetch_url",
        description="Fetch content from a URL (with SSRF protection)",
        parameters={
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "max_chars": {"type": "integer", "description": "Max characters to return"},
            },
            "required": ["url"],
        },
        func=fetch_url,
    ))
