"""Tool dependency declaration: declare that tool A requires tool B's output.

Allows tools to declare dependencies on other tools, enabling the system
to automatically sequence tool calls and validate that prerequisites are met.
"""

import logging
from dataclasses import dataclass, field

log = logging.getLogger("jarvis.tool_deps")


@dataclass
class ToolDependency:
    """Declares that a tool requires another tool's output."""

    tool_name: str
    requires: list[str] = field(default_factory=list)  # Tool names that must run first
    provides: list[str] = field(default_factory=list)  # Data keys this tool produces
    consumes: list[str] = field(default_factory=list)  # Data keys this tool needs


# Built-in dependency declarations
TOOL_DEPENDENCIES: dict[str, ToolDependency] = {
    "fetch_url": ToolDependency(
        tool_name="fetch_url",
        provides=["web_content"],
    ),
    "search_web": ToolDependency(
        tool_name="search_web",
        provides=["search_results"],
    ),
    "read_file": ToolDependency(
        tool_name="read_file",
        provides=["file_content"],
    ),
    "write_file": ToolDependency(
        tool_name="write_file",
        consumes=["file_content"],
    ),
    "file_search": ToolDependency(
        tool_name="file_search",
        provides=["search_results"],
    ),
}


class DependencyResolver:
    """Resolves tool dependencies and validates execution order."""

    def __init__(self):
        self._deps: dict[str, ToolDependency] = dict(TOOL_DEPENDENCIES)

    def register(self, dep: ToolDependency) -> None:
        """Register a tool dependency declaration."""
        self._deps[dep.tool_name] = dep

    def get_dependencies(self, tool_name: str) -> list[str]:
        """Get the list of tools that must run before the given tool."""
        dep = self._deps.get(tool_name)
        if not dep:
            return []
        return list(dep.requires)

    def get_providers(self, data_key: str) -> list[str]:
        """Find tools that provide a specific data key."""
        return [
            dep.tool_name
            for dep in self._deps.values()
            if data_key in dep.provides
        ]

    def validate_order(self, tool_sequence: list[str]) -> list[str]:
        """Validate a sequence of tool calls against dependency rules.

        Returns a list of warnings for any unmet dependencies.
        """
        warnings = []
        executed = set()

        for tool_name in tool_sequence:
            dep = self._deps.get(tool_name)
            if dep:
                for req in dep.requires:
                    if req not in executed:
                        warnings.append(
                            f"Tool '{tool_name}' requires '{req}' which hasn't been executed yet"
                        )
                for key in dep.consumes:
                    providers = self.get_providers(key)
                    if providers and not any(p in executed for p in providers):
                        warnings.append(
                            f"Tool '{tool_name}' consumes '{key}' but no provider "
                            f"({', '.join(providers)}) has run yet"
                        )
            executed.add(tool_name)

        return warnings

    def suggest_order(self, tools: list[str]) -> list[str]:
        """Suggest an optimal execution order based on dependencies.

        Uses topological sort to order tools.
        """
        # Build adjacency list
        graph: dict[str, set[str]] = {t: set() for t in tools}
        for tool_name in tools:
            dep = self._deps.get(tool_name)
            if dep:
                for req in dep.requires:
                    if req in graph:
                        graph[tool_name].add(req)
                for key in dep.consumes:
                    for provider in self.get_providers(key):
                        if provider in graph and provider != tool_name:
                            graph[tool_name].add(provider)

        # Kahn's algorithm for topological sort
        in_degree = {t: 0 for t in tools}
        for deps in graph.values():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 0  # Ensure key exists
                    # This is reversed: if A depends on B, B should come first
        for tool_name, deps in graph.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[tool_name] += 1

        queue = [t for t, d in in_degree.items() if d == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for tool_name, deps in graph.items():
                if node in deps:
                    in_degree[tool_name] -= 1
                    if in_degree[tool_name] == 0:
                        queue.append(tool_name)

        # Add any remaining tools (cycles)
        for t in tools:
            if t not in result:
                result.append(t)

        return result

    def get_dependency_graph(self) -> dict:
        """Return the full dependency graph for visualization."""
        return {
            name: {
                "requires": dep.requires,
                "provides": dep.provides,
                "consumes": dep.consumes,
            }
            for name, dep in self._deps.items()
        }
