"""Parallel tool execution: run multiple tool calls concurrently.

When the backend returns multiple tool calls in a single response,
this module can execute them in parallel using a thread pool.
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

log = logging.getLogger("jarvis.parallel")

# Default max workers for parallel tool execution
DEFAULT_MAX_WORKERS = 4


@dataclass
class ParallelResult:
    """Result of a single parallel tool execution."""

    tool_call_id: str
    tool_name: str
    result: str
    duration_ms: float
    success: bool


def execute_tools_parallel(
    registry,
    tool_calls: list,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> list[tuple[str, str]]:
    """Execute multiple tool calls in parallel.

    Args:
        registry: ToolRegistry instance.
        tool_calls: List of ToolCall objects (id, name, args).
        max_workers: Maximum number of concurrent executions.

    Returns:
        List of (tool_call_id, result) tuples in the same order as input.
    """
    if len(tool_calls) <= 1:
        # No benefit to parallelism for a single call
        results = []
        for tc in tool_calls:
            result = registry.handle_call(tc.name, tc.args)
            results.append((tc.id, result))
        return results

    log.info("Executing %d tool calls in parallel (max_workers=%d)", len(tool_calls), max_workers)
    start = time.perf_counter()

    # Map future -> index to preserve ordering
    results_by_index: dict[int, tuple[str, str]] = {}

    with ThreadPoolExecutor(max_workers=min(max_workers, len(tool_calls))) as executor:
        future_to_index = {}
        for i, tc in enumerate(tool_calls):
            future = executor.submit(registry.handle_call, tc.name, tc.args)
            future_to_index[future] = (i, tc)

        for future in as_completed(future_to_index):
            idx, tc = future_to_index[future]
            try:
                result = future.result()
            except Exception as e:
                log.exception("Parallel tool %s raised exception", tc.name)
                result = f"Tool error ({tc.name}): {e}"
            results_by_index[idx] = (tc.id, result)

    total_ms = (time.perf_counter() - start) * 1000
    log.info("Parallel execution of %d tools completed in %.0fms", len(tool_calls), total_ms)

    # Return in original order
    return [results_by_index[i] for i in range(len(tool_calls))]
