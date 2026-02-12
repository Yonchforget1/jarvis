"""HTTP tools – make API requests to external services."""

from __future__ import annotations

import json
import logging

from jarvis.tool_registry import ToolDef, ToolRegistry
from jarvis.tools.web import _is_private_url

log = logging.getLogger("jarvis.tools.http")


def http_request(
    method: str,
    url: str,
    headers: dict | None = None,
    body: str = "",
    timeout: int = 30,
) -> str:
    """Make an HTTP request and return the response.

    Args:
        method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        url: Target URL
        headers: Optional request headers
        body: Optional request body (JSON string for POST/PUT/PATCH)
        timeout: Request timeout in seconds
    """
    if _is_private_url(url):
        return "Error: access to internal/private URLs is blocked (SSRF protection)"

    try:
        import httpx
    except ImportError:
        return "Error: httpx not installed"

    method = method.upper()
    if method not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
        return f"Error: unsupported method '{method}'"

    try:
        req_headers = headers or {}
        kwargs: dict = {
            "method": method,
            "url": url,
            "headers": req_headers,
            "timeout": timeout,
            "follow_redirects": True,
        }

        if body and method in ("POST", "PUT", "PATCH"):
            # Auto-set content-type if not specified
            if "content-type" not in {k.lower() for k in req_headers}:
                req_headers["Content-Type"] = "application/json"
            kwargs["content"] = body

        with httpx.Client() as client:
            resp = client.request(**kwargs)

        # Format response
        lines = [
            f"HTTP {resp.status_code} {resp.reason_phrase}",
            "",
        ]

        # Include important response headers
        for header in ["content-type", "content-length", "location", "x-request-id"]:
            if header in resp.headers:
                lines.append(f"{header}: {resp.headers[header]}")

        lines.append("")

        # Response body
        body_text = resp.text
        if len(body_text) > 10000:
            body_text = body_text[:10000] + "\n... (truncated)"

        # Try to pretty-print JSON
        try:
            parsed = json.loads(body_text)
            body_text = json.dumps(parsed, indent=2)
        except (json.JSONDecodeError, ValueError):
            pass

        lines.append(body_text)
        return "\n".join(lines)

    except Exception as e:
        return f"Request error: {e}"


def http_get(url: str, headers: dict | None = None) -> str:
    """Shorthand for HTTP GET request."""
    return http_request("GET", url, headers=headers)


def http_post(url: str, body: str = "", headers: dict | None = None) -> str:
    """Shorthand for HTTP POST request with JSON body."""
    return http_request("POST", url, headers=headers, body=body)


def register(registry: ToolRegistry) -> None:
    registry.register(ToolDef(
        name="http_request",
        description="Make an HTTP request (GET, POST, PUT, PATCH, DELETE) and return the response",
        parameters={
            "type": "object",
            "properties": {
                "method": {"type": "string", "description": "HTTP method (GET, POST, PUT, PATCH, DELETE)"},
                "url": {"type": "string", "description": "Target URL"},
                "headers": {"type": "object", "description": "Request headers"},
                "body": {"type": "string", "description": "Request body (JSON string)"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)"},
            },
            "required": ["method", "url"],
        },
        func=http_request,
    ))
    registry.register(ToolDef(
        name="http_get",
        description="Make a quick HTTP GET request and return the response",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "headers": {"type": "object", "description": "Optional headers"},
            },
            "required": ["url"],
        },
        func=http_get,
    ))
    registry.register(ToolDef(
        name="http_post",
        description="Make an HTTP POST request with JSON body",
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to post to"},
                "body": {"type": "string", "description": "JSON request body"},
                "headers": {"type": "object", "description": "Optional headers"},
            },
            "required": ["url"],
        },
        func=http_post,
    ))
