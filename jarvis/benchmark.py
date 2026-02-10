"""Benchmarking suite for measuring tool and backend performance.

Provides utilities to benchmark individual tools, measure backend
latency, and generate performance reports.
"""

import json
import logging
import statistics
import time

log = logging.getLogger("jarvis.benchmark")


class BenchmarkResult:
    """Results from a benchmark run."""

    def __init__(self, name: str, durations_ms: list[float]):
        self.name = name
        self.durations_ms = durations_ms
        self.iterations = len(durations_ms)

    @property
    def min_ms(self) -> float:
        return min(self.durations_ms) if self.durations_ms else 0

    @property
    def max_ms(self) -> float:
        return max(self.durations_ms) if self.durations_ms else 0

    @property
    def mean_ms(self) -> float:
        return statistics.mean(self.durations_ms) if self.durations_ms else 0

    @property
    def median_ms(self) -> float:
        return statistics.median(self.durations_ms) if self.durations_ms else 0

    @property
    def stdev_ms(self) -> float:
        return statistics.stdev(self.durations_ms) if len(self.durations_ms) >= 2 else 0

    @property
    def p95_ms(self) -> float:
        if not self.durations_ms:
            return 0
        sorted_d = sorted(self.durations_ms)
        idx = int(len(sorted_d) * 0.95)
        return sorted_d[min(idx, len(sorted_d) - 1)]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "min_ms": round(self.min_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "mean_ms": round(self.mean_ms, 2),
            "median_ms": round(self.median_ms, 2),
            "stdev_ms": round(self.stdev_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
        }

    def __str__(self) -> str:
        return (
            f"{self.name}: {self.iterations} iterations | "
            f"mean={self.mean_ms:.1f}ms median={self.median_ms:.1f}ms "
            f"min={self.min_ms:.1f}ms max={self.max_ms:.1f}ms "
            f"p95={self.p95_ms:.1f}ms stdev={self.stdev_ms:.1f}ms"
        )


def benchmark_tool(registry, tool_name: str, args: dict, iterations: int = 10) -> BenchmarkResult:
    """Benchmark a single tool with the given arguments.

    Args:
        registry: ToolRegistry instance.
        tool_name: Name of the tool to benchmark.
        args: Arguments to pass to the tool.
        iterations: Number of times to run the tool.

    Returns:
        BenchmarkResult with timing statistics.
    """
    durations = []
    for i in range(iterations):
        start = time.perf_counter()
        registry.handle_call(tool_name, args)
        duration_ms = (time.perf_counter() - start) * 1000
        durations.append(duration_ms)

    result = BenchmarkResult(tool_name, durations)
    log.info("Benchmark %s: %s", tool_name, result)
    return result


def benchmark_backend_latency(backend, iterations: int = 3) -> BenchmarkResult:
    """Measure backend API call latency with minimal requests.

    Args:
        backend: Backend instance.
        iterations: Number of ping calls.

    Returns:
        BenchmarkResult with latency statistics.
    """
    durations = []
    for _ in range(iterations):
        start = time.perf_counter()
        backend.ping()
        duration_ms = (time.perf_counter() - start) * 1000
        durations.append(duration_ms)

    result = BenchmarkResult(f"backend_latency", durations)
    log.info("Backend latency: %s", result)
    return result


def run_tool_suite(registry, iterations: int = 5) -> list[BenchmarkResult]:
    """Run benchmarks for a standard set of safe, read-only tools.

    Only benchmarks tools that don't have side effects.
    """
    safe_benchmarks = [
        ("list_directory", {"path": "."}),
        ("system_info", {}),
    ]

    results = []
    for tool_name, args in safe_benchmarks:
        tool = registry.get(tool_name)
        if tool:
            result = benchmark_tool(registry, tool_name, args, iterations)
            results.append(result)
        else:
            log.warning("Skipping benchmark for %s (not found)", tool_name)

    return results


def generate_report(results: list[BenchmarkResult]) -> str:
    """Generate a formatted benchmark report."""
    lines = ["=" * 60, "Jarvis Benchmark Report", "=" * 60, ""]

    for r in sorted(results, key=lambda x: x.mean_ms, reverse=True):
        lines.append(str(r))

    lines.append("")
    lines.append("=" * 60)
    if results:
        total_mean = sum(r.mean_ms for r in results)
        lines.append(f"Total mean execution time: {total_mean:.1f}ms across {len(results)} tools")
    return "\n".join(lines)
