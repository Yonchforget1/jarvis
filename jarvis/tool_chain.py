"""Tool chaining: compose tool outputs as inputs to subsequent tools.

Provides a mechanism for the AI to define a pipeline of tool calls where
each step can reference the output of previous steps via {{step_N}} placeholders.
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field

log = logging.getLogger("jarvis.tool_chain")


@dataclass
class ChainStep:
    """A single step in a tool chain."""

    tool_name: str
    args: dict
    result: str = ""
    duration_ms: float = 0.0
    success: bool = False


@dataclass
class ChainResult:
    """Result of executing a tool chain."""

    steps: list[ChainStep] = field(default_factory=list)
    final_output: str = ""

    @property
    def success(self) -> bool:
        return all(s.success for s in self.steps)

    @property
    def total_duration_ms(self) -> float:
        return sum(s.duration_ms for s in self.steps)


class ToolChain:
    """Executes a sequence of tool calls, piping outputs between steps."""

    PLACEHOLDER_RE = re.compile(r"\{\{step_(\d+)\}\}")

    def __init__(self, registry):
        self.registry = registry

    def _resolve_placeholders(self, value: str, outputs: dict[int, str]) -> str:
        """Replace {{step_N}} placeholders with actual outputs from previous steps."""
        def replacer(match):
            step_num = int(match.group(1))
            return outputs.get(step_num, match.group(0))
        return self.PLACEHOLDER_RE.sub(replacer, value)

    def _resolve_args(self, args: dict, outputs: dict[int, str]) -> dict:
        """Resolve placeholders in all string argument values."""
        resolved = {}
        for key, value in args.items():
            if isinstance(value, str):
                resolved[key] = self._resolve_placeholders(value, outputs)
            else:
                resolved[key] = value
        return resolved

    def execute(self, steps: list[dict]) -> ChainResult:
        """Execute a chain of tool calls.

        Each step dict has:
            - tool: tool name
            - args: dict of arguments (may contain {{step_N}} placeholders)

        Returns a ChainResult with all step outputs.
        """
        result = ChainResult()
        outputs: dict[int, str] = {}

        for i, step_def in enumerate(steps):
            tool_name = step_def.get("tool", "")
            raw_args = step_def.get("args", {})

            # Resolve any placeholders from previous step outputs
            resolved_args = self._resolve_args(raw_args, outputs)

            chain_step = ChainStep(tool_name=tool_name, args=resolved_args)

            start = time.perf_counter()
            output = self.registry.handle_call(tool_name, resolved_args)
            chain_step.duration_ms = (time.perf_counter() - start) * 1000

            chain_step.result = output
            chain_step.success = not output.startswith("Unknown tool:") and not output.startswith("Tool error")
            result.steps.append(chain_step)

            # Store output for downstream steps
            outputs[i + 1] = output

            log.info("Chain step %d (%s): %s in %.0fms",
                     i + 1, tool_name, "OK" if chain_step.success else "FAILED", chain_step.duration_ms)

            if not chain_step.success:
                log.warning("Chain aborted at step %d: %s", i + 1, output[:200])
                break

        result.final_output = result.steps[-1].result if result.steps else ""
        return result


def run_chain(steps: str) -> str:
    """Execute a chain of tool calls, piping outputs between steps.

    Args:
        steps: JSON array of step objects. Each: {"tool": "tool_name", "args": {"key": "value"}}.
               Use {{step_N}} in arg values to reference the output of step N.
    """
    # Lazy import to avoid circular dependency
    from jarvis.tool_registry import ToolRegistry
    try:
        step_list = json.loads(steps)
    except json.JSONDecodeError as e:
        return f"Error parsing steps JSON: {e}"
    if not isinstance(step_list, list) or not step_list:
        return "Steps must be a non-empty JSON array."

    # Get the global registry from the planner tools module
    # This is set during tool registration
    if _registry is None:
        return "Tool chain not initialized (no registry)."

    chain = ToolChain(_registry)
    result = chain.execute(step_list)

    lines = [f"Chain {'completed' if result.success else 'failed'} ({len(result.steps)} steps, {result.total_duration_ms:.0f}ms total)"]
    for i, step in enumerate(result.steps):
        status = "OK" if step.success else "FAILED"
        lines.append(f"  Step {i+1} ({step.tool_name}): {status} ({step.duration_ms:.0f}ms)")
    lines.append(f"\nFinal output:\n{result.final_output}")
    return "\n".join(lines)


# Module-level registry reference, set during registration
_registry = None


def register(registry) -> None:
    global _registry
    _registry = registry

    from jarvis.tool_registry import ToolDef
    registry.register(ToolDef(
        name="chain_tools",
        description="Execute a sequence of tool calls where each step can use outputs from previous steps via {{step_N}} placeholders.",
        parameters={
            "properties": {
                "steps": {
                    "type": "string",
                    "description": 'JSON array of steps. Each: {"tool": "tool_name", "args": {"key": "value"}}. Use {{step_N}} to reference output of step N.',
                },
            },
            "required": ["steps"],
        },
        func=run_chain,
        category="planning",
    ))
