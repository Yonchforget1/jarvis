"""Plugin: Docker management tool

List, start, stop, and inspect Docker containers.
Requires Docker CLI (docker) to be installed and accessible.
"""

import json
import subprocess

from jarvis.tool_registry import ToolDef

TIMEOUT = 15


def _run_docker(args: list[str]) -> str:
    """Run a docker CLI command and return output."""
    try:
        result = subprocess.run(
            ["docker"] + args,
            capture_output=True, text=True, timeout=TIMEOUT,
        )
        if result.returncode != 0:
            return f"Docker error: {result.stderr.strip()}"
        return result.stdout.strip()
    except FileNotFoundError:
        return "Error: Docker CLI not found. Is Docker installed?"
    except subprocess.TimeoutExpired:
        return f"Error: Docker command timed out after {TIMEOUT}s."
    except Exception as e:
        return f"Error running docker: {e}"


def docker_list_containers(all_containers: bool = False) -> str:
    """List Docker containers."""
    args = ["ps", "--format", "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"]
    if all_containers:
        args.append("-a")
    return _run_docker(args)


def docker_container_logs(container: str, tail: int = 50) -> str:
    """Get recent logs from a Docker container."""
    return _run_docker(["logs", "--tail", str(tail), container])


def docker_start_container(container: str) -> str:
    """Start a stopped Docker container."""
    return _run_docker(["start", container])


def docker_stop_container(container: str) -> str:
    """Stop a running Docker container."""
    return _run_docker(["stop", container])


def docker_inspect(container: str) -> str:
    """Inspect a Docker container (detailed JSON info)."""
    output = _run_docker(["inspect", container])
    if output.startswith("Error") or output.startswith("Docker"):
        return output
    try:
        data = json.loads(output)
        if data and isinstance(data, list):
            info = data[0]
            return json.dumps({
                "Id": info.get("Id", "")[:12],
                "Name": info.get("Name", ""),
                "State": info.get("State", {}).get("Status", ""),
                "Image": info.get("Config", {}).get("Image", ""),
                "Created": info.get("Created", ""),
                "Ports": info.get("NetworkSettings", {}).get("Ports", {}),
                "Env": info.get("Config", {}).get("Env", [])[:10],
            }, indent=2)
    except json.JSONDecodeError:
        pass
    return output[:3000]


def docker_images() -> str:
    """List Docker images."""
    return _run_docker(["images", "--format", "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}"])


def register(registry) -> None:
    registry.register(ToolDef(
        name="docker_list",
        description="List Docker containers. Use all_containers=true to include stopped ones.",
        parameters={
            "properties": {
                "all_containers": {"type": "boolean", "description": "Show all containers, not just running.", "default": False},
            },
            "required": [],
        },
        func=docker_list_containers,
        category="integration",
    ))
    registry.register(ToolDef(
        name="docker_logs",
        description="Get recent logs from a Docker container.",
        parameters={
            "properties": {
                "container": {"type": "string", "description": "Container name or ID."},
                "tail": {"type": "integer", "description": "Number of log lines.", "default": 50},
            },
            "required": ["container"],
        },
        func=docker_container_logs,
        category="integration",
    ))
    registry.register(ToolDef(
        name="docker_start",
        description="Start a stopped Docker container.",
        parameters={
            "properties": {
                "container": {"type": "string", "description": "Container name or ID."},
            },
            "required": ["container"],
        },
        func=docker_start_container,
        category="integration",
    ))
    registry.register(ToolDef(
        name="docker_stop",
        description="Stop a running Docker container.",
        parameters={
            "properties": {
                "container": {"type": "string", "description": "Container name or ID."},
            },
            "required": ["container"],
        },
        func=docker_stop_container,
        category="integration",
    ))
    registry.register(ToolDef(
        name="docker_inspect",
        description="Inspect a Docker container for detailed information.",
        parameters={
            "properties": {
                "container": {"type": "string", "description": "Container name or ID."},
            },
            "required": ["container"],
        },
        func=docker_inspect,
        category="integration",
    ))
    registry.register(ToolDef(
        name="docker_images",
        description="List Docker images on the system.",
        parameters={"properties": {}, "required": []},
        func=docker_images,
        category="integration",
    ))
