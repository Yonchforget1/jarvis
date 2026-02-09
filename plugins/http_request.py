"""HTTP request tool: make custom API calls with headers and body."""

import json

import httpx

from jarvis.tool_registry import ToolDef


def http_request(url: str, method: str = "GET", headers: str = "", body: str = "", timeout: int = 15) -> str:
    """Make an HTTP request and return the response.

    Args:
        url: The URL to request.
        method: HTTP method (GET, POST, PUT, DELETE, PATCH).
        headers: JSON string of headers, e.g., '{"Authorization": "Bearer xyz"}'.
        body: Request body (string or JSON string for POST/PUT/PATCH).
        timeout: Request timeout in seconds.
    """
    method = method.upper()
    if method not in ("GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"):
        return f"Error: unsupported HTTP method '{method}'."

    # Parse headers
    parsed_headers = {"User-Agent": "Jarvis/1.0"}
    if headers:
        try:
            parsed_headers.update(json.loads(headers))
        except json.JSONDecodeError:
            return "Error: headers must be valid JSON."

    # Parse body
    content = None
    json_body = None
    if body and method in ("POST", "PUT", "PATCH"):
        try:
            json_body = json.loads(body)
        except json.JSONDecodeError:
            content = body  # Send as raw text

    try:
        response = httpx.request(
            method=method,
            url=url,
            headers=parsed_headers,
            json=json_body,
            content=content,
            timeout=timeout,
            follow_redirects=True,
        )

        lines = [
            f"Status: {response.status_code} {response.reason_phrase}",
            f"Content-Type: {response.headers.get('content-type', 'unknown')}",
            f"Size: {len(response.content)} bytes",
            "",
        ]

        # Response body
        text = response.text
        if len(text) > 20000:
            text = text[:20000] + f"\n\n... (truncated, {len(text)} chars total)"
        lines.append(text)

        return "\n".join(lines)
    except httpx.TimeoutException:
        return f"Error: request timed out after {timeout}s."
    except Exception as e:
        return f"Error: {e}"


def register(registry):
    registry.register(ToolDef(
        name="http_request",
        description="Make a custom HTTP request (GET, POST, PUT, DELETE, PATCH). Supports custom headers and body for API calls.",
        parameters={
            "properties": {
                "url": {"type": "string", "description": "The URL to request."},
                "method": {"type": "string", "description": "HTTP method: GET, POST, PUT, DELETE, PATCH.", "default": "GET"},
                "headers": {"type": "string", "description": "JSON string of headers, e.g., '{\"Authorization\": \"Bearer xyz\"}'.", "default": ""},
                "body": {"type": "string", "description": "Request body (JSON or raw text) for POST/PUT/PATCH.", "default": ""},
                "timeout": {"type": "integer", "description": "Timeout in seconds.", "default": 15},
            },
            "required": ["url"],
        },
        func=http_request,
    ))
