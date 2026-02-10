"""Shared test fixtures for Jarvis tests."""

import os
import sys

import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jarvis.tool_registry import ToolDef, ToolRegistry


@pytest.fixture
def registry():
    """Return a fresh ToolRegistry."""
    return ToolRegistry()


@pytest.fixture
def sample_tool():
    """Return a simple test tool."""
    return ToolDef(
        name="echo",
        description="Echoes back the input.",
        parameters={
            "properties": {
                "text": {"type": "string", "description": "Text to echo."},
            },
            "required": ["text"],
        },
        func=lambda text: f"echo: {text}",
    )
