"""Multi-model routing: use different models for different task types.

Routes requests to the most appropriate backend/model based on
task classification. For example:
- Simple queries -> fast/cheap model (Haiku, GPT-4o-mini)
- Complex reasoning -> strong model (Opus, GPT-4o)
- Code tasks -> code-optimized model
"""

import logging
import re
from dataclasses import dataclass

log = logging.getLogger("jarvis.model_router")


@dataclass
class ModelRoute:
    """A routing rule that maps task patterns to a specific model."""

    name: str
    backend: str
    model: str
    patterns: list[str]  # Regex patterns that trigger this route
    priority: int = 0  # Higher priority routes are checked first


# Default routing rules
DEFAULT_ROUTES = [
    ModelRoute(
        name="simple",
        backend="claude",
        model="claude-haiku-4-5-20251001",
        patterns=[
            r"^(hi|hello|hey|thanks|ok|yes|no)\b",
            r"^what (is|are) ",
            r"^who (is|are) ",
            r"^when (is|was|did) ",
            r"time|date|weather",
        ],
        priority=10,
    ),
    ModelRoute(
        name="code",
        backend="claude",
        model="claude-sonnet-4-5-20250929",
        patterns=[
            r"(write|create|fix|debug|refactor)\s+(code|function|class|script|program)",
            r"\b(python|javascript|typescript|rust|go|java|c\+\+)\b.*\b(code|implement)\b",
            r"(bug|error|exception|traceback)",
            r"(pull request|code review|git)",
        ],
        priority=20,
    ),
    ModelRoute(
        name="complex",
        backend="claude",
        model="claude-sonnet-4-5-20250929",
        patterns=[
            r"(analyze|explain|compare|design|architect|plan)",
            r"(strategy|approach|trade-?off|pros and cons)",
            r"(research|investigate|deep dive)",
        ],
        priority=15,
    ),
]


class ModelRouter:
    """Routes requests to appropriate models based on content analysis."""

    def __init__(self, routes: list[ModelRoute] | None = None, default_backend: str = "claude", default_model: str = "claude-sonnet-4-5-20250929"):
        self.routes = sorted(routes or DEFAULT_ROUTES, key=lambda r: -r.priority)
        self.default_backend = default_backend
        self.default_model = default_model
        self._compiled: list[tuple[ModelRoute, list[re.Pattern]]] = []
        for route in self.routes:
            compiled_patterns = [re.compile(p, re.IGNORECASE) for p in route.patterns]
            self._compiled.append((route, compiled_patterns))

    def route(self, message: str) -> tuple[str, str, str]:
        """Determine the best backend and model for a message.

        Args:
            message: The user's message text.

        Returns:
            Tuple of (route_name, backend, model).
        """
        for route, patterns in self._compiled:
            for pattern in patterns:
                if pattern.search(message):
                    log.debug("Routed to '%s' (%s/%s)", route.name, route.backend, route.model)
                    return route.name, route.backend, route.model

        return "default", self.default_backend, self.default_model

    def add_route(self, route: ModelRoute) -> None:
        """Add a custom routing rule."""
        self.routes.append(route)
        self.routes.sort(key=lambda r: -r.priority)
        compiled_patterns = [re.compile(p, re.IGNORECASE) for p in route.patterns]
        self._compiled.append((route, compiled_patterns))
        self._compiled.sort(key=lambda x: -x[0].priority)

    def list_routes(self) -> list[dict]:
        """List all routing rules."""
        return [
            {
                "name": r.name,
                "backend": r.backend,
                "model": r.model,
                "patterns": r.patterns,
                "priority": r.priority,
            }
            for r in self.routes
        ]
