"""Download file tool: download a URL to a local file path."""

import os

import httpx

from jarvis.tool_registry import ToolDef

MAX_DOWNLOAD_SIZE = 100 * 1024 * 1024  # 100 MB


def download_file(url: str, destination: str, timeout: int = 60) -> str:
    """Download a file from a URL to a local path.

    Args:
        url: The URL to download from.
        destination: Local file path to save to.
        timeout: Request timeout in seconds.
    """
    if not url.startswith(("http://", "https://")):
        return "Error: URL must start with http:// or https://"

    # Ensure destination directory exists
    dest_dir = os.path.dirname(destination)
    if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)

    try:
        with httpx.stream("GET", url, timeout=timeout, follow_redirects=True,
                          headers={"User-Agent": "Jarvis/1.0"}) as response:
            response.raise_for_status()

            # Check content length if available
            content_length = response.headers.get("content-length")
            if content_length and int(content_length) > MAX_DOWNLOAD_SIZE:
                return f"Error: file too large ({int(content_length)} bytes, max {MAX_DOWNLOAD_SIZE})."

            total = 0
            with open(destination, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_SIZE:
                        f.close()
                        os.remove(destination)
                        return f"Error: download exceeded max size ({MAX_DOWNLOAD_SIZE} bytes)."
                    f.write(chunk)

        content_type = response.headers.get("content-type", "unknown")
        return f"Downloaded {total:,} bytes to {destination} (type: {content_type})"

    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} {e.response.reason_phrase}"
    except httpx.TimeoutException:
        return f"Error: download timed out after {timeout}s."
    except Exception as e:
        return f"Error downloading file: {e}"


def register(registry):
    registry.register(ToolDef(
        name="download_file",
        description="Download a file from a URL to a local path. Supports up to 100MB files.",
        parameters={
            "properties": {
                "url": {"type": "string", "description": "The URL to download from."},
                "destination": {"type": "string", "description": "Local file path to save the downloaded file."},
                "timeout": {"type": "integer", "description": "Timeout in seconds.", "default": 60},
            },
            "required": ["url", "destination"],
        },
        func=download_file,
        category="web",
    ))
