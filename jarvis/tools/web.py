import ipaddress
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from ddgs import DDGS

from jarvis.tool_registry import ToolDef


def _is_internal_url(url: str) -> bool:
    """Check if a URL points to an internal/private IP address (SSRF protection)."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return True
        # Block common internal hostnames
        if hostname in ("localhost", "0.0.0.0", "127.0.0.1", "::1"):
            return True
        # Block private/reserved IP ranges
        try:
            addr = ipaddress.ip_address(hostname)
            return addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local
        except ValueError:
            # Not a raw IP — hostname is fine
            return False
    except Exception:
        return True


def search_web(query: str) -> str:
    """Search the web via DuckDuckGo and return formatted results."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "No results found."
        lines = []
        for r in results:
            lines.append(f"**{r['title']}**\n{r['href']}\n{r['body']}\n")
        return "\n".join(lines)
    except Exception as e:
        return f"Search error: {e}"


def fetch_url(url: str, selector: str = "") -> str:
    """Fetch a URL and extract text content, optionally filtered by CSS selector."""
    if _is_internal_url(url):
        return "Error: cannot fetch internal/private URLs (SSRF protection)."
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; Jarvis/1.0)"}
        response = httpx.get(url, headers=headers, follow_redirects=True, timeout=15)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            text = response.text[:20000]
            return text if text else "(empty response)"

        soup = BeautifulSoup(response.text, "lxml")

        # Remove non-content elements
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        if selector:
            elements = soup.select(selector)
            if not elements:
                return f"No elements matched selector: {selector}"
            text = "\n\n".join(el.get_text(separator="\n", strip=True) for el in elements)
        else:
            text = soup.get_text(separator="\n", strip=True)

        text = re.sub(r"\n{3,}", "\n\n", text)

        if len(text) > 20000:
            text = text[:20000] + f"\n\n... (truncated, {len(text)} chars total)"
        return text if text else "(no readable content)"
    except Exception as e:
        return f"Error fetching URL: {e}"


def register(registry):
    registry.register(ToolDef(
        name="search_web",
        description="Search the web for current information on a topic using DuckDuckGo.",
        parameters={
            "properties": {
                "query": {"type": "string", "description": "The search query."},
            },
            "required": ["query"],
        },
        func=search_web,
    ))
    registry.register(ToolDef(
        name="fetch_url",
        description="Fetch a web page and extract its text content. Can optionally filter by CSS selector.",
        parameters={
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch."},
                "selector": {"type": "string", "description": "Optional CSS selector to extract specific elements.", "default": ""},
            },
            "required": ["url"],
        },
        func=fetch_url,
    ))
