"""Tests for the tool chaining system."""

import json
import pytest

from jarvis.tool_registry import ToolDef, ToolRegistry
from jarvis.tool_chain import ToolChain, ChainStep, ChainResult


def _make_registry() -> ToolRegistry:
    """Create a registry with simple test tools."""
    registry = ToolRegistry()
    registry.register(ToolDef(
        name="echo",
        description="Echoes input text",
        parameters={"properties": {"text": {"type": "string"}}, "required": ["text"]},
        func=lambda text: f"ECHO:{text}",
    ))
    registry.register(ToolDef(
        name="upper",
        description="Uppercases input",
        parameters={"properties": {"text": {"type": "string"}}, "required": ["text"]},
        func=lambda text: text.upper(),
    ))
    registry.register(ToolDef(
        name="concat",
        description="Concatenates a and b",
        parameters={"properties": {"a": {"type": "string"}, "b": {"type": "string"}}, "required": ["a", "b"]},
        func=lambda a, b: f"{a}+{b}",
    ))
    registry.register(ToolDef(
        name="fail_tool",
        description="Always raises an error",
        parameters={"properties": {}, "required": []},
        func=lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    ))
    return registry


class TestChainStep:
    def test_defaults(self):
        step = ChainStep(tool_name="test", args={})
        assert step.result == ""
        assert step.success is False
        assert step.duration_ms == 0.0


class TestChainResult:
    def test_empty_result(self):
        r = ChainResult()
        assert r.success is True  # vacuously true
        assert r.total_duration_ms == 0.0
        assert r.final_output == ""

    def test_success_when_all_succeed(self):
        r = ChainResult(steps=[
            ChainStep("a", {}, "ok", 10, True),
            ChainStep("b", {}, "ok", 20, True),
        ])
        assert r.success is True
        assert r.total_duration_ms == 30.0

    def test_failure_when_any_fails(self):
        r = ChainResult(steps=[
            ChainStep("a", {}, "ok", 10, True),
            ChainStep("b", {}, "err", 20, False),
        ])
        assert r.success is False


class TestToolChain:
    def test_single_step(self):
        registry = _make_registry()
        chain = ToolChain(registry)
        result = chain.execute([{"tool": "echo", "args": {"text": "hello"}}])
        assert result.success
        assert len(result.steps) == 1
        assert result.final_output == "ECHO:hello"

    def test_multi_step_no_placeholders(self):
        registry = _make_registry()
        chain = ToolChain(registry)
        result = chain.execute([
            {"tool": "echo", "args": {"text": "a"}},
            {"tool": "upper", "args": {"text": "hello"}},
        ])
        assert result.success
        assert len(result.steps) == 2
        assert result.final_output == "HELLO"

    def test_placeholder_piping(self):
        registry = _make_registry()
        chain = ToolChain(registry)
        result = chain.execute([
            {"tool": "echo", "args": {"text": "world"}},
            {"tool": "upper", "args": {"text": "{{step_1}}"}},
        ])
        assert result.success
        assert result.final_output == "ECHO:WORLD"

    def test_multi_placeholder_piping(self):
        registry = _make_registry()
        chain = ToolChain(registry)
        result = chain.execute([
            {"tool": "echo", "args": {"text": "left"}},
            {"tool": "echo", "args": {"text": "right"}},
            {"tool": "concat", "args": {"a": "{{step_1}}", "b": "{{step_2}}"}},
        ])
        assert result.success
        assert result.final_output == "ECHO:left+ECHO:right"

    def test_unknown_tool_aborts_chain(self):
        registry = _make_registry()
        chain = ToolChain(registry)
        result = chain.execute([
            {"tool": "nonexistent", "args": {}},
            {"tool": "echo", "args": {"text": "never"}},
        ])
        assert not result.success
        assert len(result.steps) == 1  # aborted after first step
        assert "Unknown tool" in result.final_output

    def test_tool_error_aborts_chain(self):
        registry = _make_registry()
        chain = ToolChain(registry)
        result = chain.execute([
            {"tool": "fail_tool", "args": {}},
            {"tool": "echo", "args": {"text": "never"}},
        ])
        assert not result.success
        assert len(result.steps) == 1
        assert "Tool error" in result.final_output

    def test_unresolved_placeholder_kept_as_is(self):
        registry = _make_registry()
        chain = ToolChain(registry)
        result = chain.execute([
            {"tool": "echo", "args": {"text": "{{step_99}}"}},
        ])
        assert result.success
        assert "{{step_99}}" in result.final_output

    def test_empty_steps(self):
        registry = _make_registry()
        chain = ToolChain(registry)
        result = chain.execute([])
        assert result.final_output == ""

    def test_non_string_args_not_resolved(self):
        """Non-string args should pass through without placeholder resolution."""
        registry = ToolRegistry()
        registry.register(ToolDef(
            name="numtool",
            description="Returns number as string",
            parameters={"properties": {"n": {"type": "integer"}}, "required": ["n"]},
            func=lambda n: str(n),
        ))
        chain = ToolChain(registry)
        result = chain.execute([{"tool": "numtool", "args": {"n": 42}}])
        assert result.success
        assert result.final_output == "42"

    def test_duration_tracking(self):
        registry = _make_registry()
        chain = ToolChain(registry)
        result = chain.execute([
            {"tool": "echo", "args": {"text": "timing"}},
        ])
        assert result.steps[0].duration_ms > 0
        assert result.total_duration_ms > 0


class TestRunChain:
    """Test the run_chain function used as a tool."""

    def test_run_chain_valid(self):
        from jarvis import tool_chain
        registry = _make_registry()
        # Set the module-level registry
        tool_chain._registry = registry
        steps = json.dumps([
            {"tool": "echo", "args": {"text": "hello"}},
            {"tool": "upper", "args": {"text": "{{step_1}}"}},
        ])
        result = tool_chain.run_chain(steps)
        assert "completed" in result.lower()
        assert "ECHO:HELLO" in result

    def test_run_chain_invalid_json(self):
        from jarvis import tool_chain
        result = tool_chain.run_chain("not json")
        assert "Error parsing" in result

    def test_run_chain_empty_list(self):
        from jarvis import tool_chain
        result = tool_chain.run_chain("[]")
        assert "non-empty" in result

    def test_run_chain_not_a_list(self):
        from jarvis import tool_chain
        result = tool_chain.run_chain('{"tool": "echo"}')
        assert "non-empty" in result or "must be" in result.lower()

    def test_run_chain_no_registry(self):
        from jarvis import tool_chain
        old = tool_chain._registry
        tool_chain._registry = None
        try:
            result = tool_chain.run_chain('[{"tool": "echo", "args": {}}]')
            assert "not initialized" in result
        finally:
            tool_chain._registry = old
