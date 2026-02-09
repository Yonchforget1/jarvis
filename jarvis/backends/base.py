from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from jarvis.tool_registry import ToolDef


@dataclass
class ToolCall:
    """Backend-agnostic representation of a tool call from the model."""

    id: str
    name: str
    args: dict


@dataclass
class BackendResponse:
    """What the backend returns after one API call."""

    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: object = None


class Backend(ABC):
    """Common interface for all AI backends."""

    @abstractmethod
    def send(
        self,
        messages: list,
        system: str,
        tools: list[ToolDef],
        max_tokens: int = 4096,
    ) -> BackendResponse: ...

    @abstractmethod
    def format_user_message(self, text: str) -> dict: ...

    @abstractmethod
    def format_assistant_message(self, response: BackendResponse) -> dict: ...

    @abstractmethod
    def format_tool_results(self, results: list[tuple[str, str]]) -> dict | list[dict]: ...

    def ping(self) -> bool:
        """Check backend connectivity with a minimal API call.

        Returns True if the backend is reachable and authenticated.
        Subclasses should override for efficient implementation.
        """
        try:
            self.send(
                messages=[self.format_user_message("ping")],
                system="Respond with 'pong'.",
                tools=[],
                max_tokens=5,
            )
            return True
        except Exception:
            return False
