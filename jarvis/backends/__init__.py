"""Backend factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.config import Config
    from jarvis.backends.base import Backend


def create_backend(config: Config) -> Backend:
    name = config.backend

    if name == "claude_code":
        from jarvis.backends.claude_code import ClaudeCodeBackend
        return ClaudeCodeBackend(config)

    raise ValueError(f"Unknown backend: {name!r}")
