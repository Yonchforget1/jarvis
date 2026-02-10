"""Tests for ToolRegistry: register, get, handle_call, schema generation."""

from jarvis.tool_registry import ToolDef, ToolRegistry


def test_register_and_get(registry, sample_tool):
    registry.register(sample_tool)
    assert registry.get("echo") is sample_tool


def test_get_missing(registry):
    assert registry.get("nonexistent") is None


def test_all_tools(registry, sample_tool):
    assert registry.all_tools() == []
    registry.register(sample_tool)
    tools = registry.all_tools()
    assert len(tools) == 1
    assert tools[0].name == "echo"


def test_handle_call_success(registry, sample_tool):
    registry.register(sample_tool)
    result = registry.handle_call("echo", {"text": "hello"})
    assert result == "echo: hello"


def test_handle_call_unknown_tool(registry):
    result = registry.handle_call("missing", {})
    assert "Unknown tool" in result


def test_handle_call_missing_required_param(registry, sample_tool):
    registry.register(sample_tool)
    result = registry.handle_call("echo", {})
    assert "missing required parameters" in result
    assert "text" in result


def test_handle_call_exception(registry):
    def fail(**kwargs):
        raise ValueError("boom")

    tool = ToolDef(
        name="failer",
        description="Always fails.",
        parameters={"properties": {}, "required": []},
        func=fail,
    )
    registry.register(tool)
    result = registry.handle_call("failer", {})
    assert "Tool error" in result
    assert "boom" in result


def test_schema_anthropic(sample_tool):
    schema = sample_tool.schema_anthropic()
    assert schema["name"] == "echo"
    assert "input_schema" in schema
    assert schema["input_schema"]["type"] == "object"
    assert "text" in schema["input_schema"]["properties"]


def test_schema_openai(sample_tool):
    schema = sample_tool.schema_openai()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "echo"
    assert "parameters" in schema["function"]


def test_schema_gemini(sample_tool):
    schema = sample_tool.schema_gemini()
    assert schema["name"] == "echo"
    assert "parameters" in schema
    assert schema["parameters"]["type"] == "object"


def test_register_overwrites(registry):
    tool1 = ToolDef("t", "v1", {"properties": {}, "required": []}, func=lambda: "v1")
    tool2 = ToolDef("t", "v2", {"properties": {}, "required": []}, func=lambda: "v2")
    registry.register(tool1)
    registry.register(tool2)
    assert registry.get("t").description == "v2"
    assert registry.handle_call("t", {}) == "v2"
