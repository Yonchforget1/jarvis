"""Tests for the smart tool router."""

from __future__ import annotations

import pytest

from jarvis.tool_registry import ToolDef
from jarvis.tool_router import ToolRouter


def _make_tool(name: str, desc: str) -> ToolDef:
    return ToolDef(
        name=name,
        description=desc,
        parameters={"type": "object", "properties": {}},
        func=lambda: "",
    )


@pytest.fixture
def tools():
    return [
        _make_tool("read_file", "Read the contents of a file from the filesystem"),
        _make_tool("write_file", "Write content to a file on the filesystem"),
        _make_tool("run_shell", "Execute a shell command"),
        _make_tool("search_web", "Search the web using DuckDuckGo"),
        _make_tool("fetch_url", "Fetch the content of a URL"),
        _make_tool("screenshot", "Take a screenshot of the screen"),
        _make_tool("mouse_click", "Click at screen coordinates"),
        _make_tool("browser_navigate", "Navigate to a URL in the browser"),
        _make_tool("save_learning", "Save a learning to persistent memory"),
        _make_tool("search_memory", "Search over stored memories"),
    ]


@pytest.fixture
def router(tools):
    return ToolRouter(tools)


def test_score_returns_all_tools(router, tools):
    scored = router.score("read a file")
    assert len(scored) == len(tools)


def test_file_query_ranks_file_tools_first(router):
    scored = router.score("read a file")
    top3_names = [t.name for t, _ in scored[:3]]
    assert "read_file" in top3_names


def test_web_query_ranks_web_tools_first(router):
    scored = router.score("search the web for python tutorials")
    top3_names = [t.name for t, _ in scored[:3]]
    assert "search_web" in top3_names


def test_shell_query(router):
    scored = router.score("execute a shell command to list files")
    top_name = scored[0][0].name
    assert top_name == "run_shell"


def test_select_returns_top_k(router):
    selected = router.select("read a file", top_k=3)
    assert len(selected) == 3


def test_select_default_top_k(router):
    selected = router.select("do something")
    assert len(selected) == 8  # DEFAULT_TOP_K


def test_empty_query(router):
    scored = router.score("")
    assert all(s == 0.0 for _, s in scored)


def test_browser_query(router):
    scored = router.score("navigate to google.com in the browser")
    top3_names = [t.name for t, _ in scored[:3]]
    assert "browser_navigate" in top3_names


def test_memory_query(router):
    scored = router.score("save this learning to memory")
    top3_names = [t.name for t, _ in scored[:3]]
    assert "save_learning" in top3_names
