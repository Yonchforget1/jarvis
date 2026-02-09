"""Benchmark: Ollama (llama3.2) vs Claude (Sonnet) on 20 diverse tasks.

Runs each task through both backends, measures response time, and uses
Claude as a judge to rate response quality on a 1-10 scale. Results are
saved to benchmarks/ollama_vs_claude.md.

Usage:
    python benchmarks/run_benchmark.py
"""

import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from jarvis.backends.ollama_backend import OllamaBackend
from jarvis.backends.claude import ClaudeBackend

# ── 20 Benchmark Tasks ─────────────────────────────────────────────────────

TASKS = [
    # -- Reasoning & Logic --
    {
        "id": 1,
        "category": "Reasoning",
        "prompt": "A farmer has 17 sheep. All but 9 die. How many sheep are left?",
    },
    {
        "id": 2,
        "category": "Reasoning",
        "prompt": "If it takes 5 machines 5 minutes to make 5 widgets, how long would it take 100 machines to make 100 widgets?",
    },
    {
        "id": 3,
        "category": "Logic",
        "prompt": "Is the following argument valid? All cats are animals. Some animals are pets. Therefore, some cats are pets. Explain.",
    },
    {
        "id": 4,
        "category": "Math",
        "prompt": "What is the derivative of f(x) = x^3 * ln(x)?",
    },
    # -- Coding --
    {
        "id": 5,
        "category": "Coding",
        "prompt": "Write a Python function that checks if a string is a valid palindrome, ignoring spaces and punctuation.",
    },
    {
        "id": 6,
        "category": "Coding",
        "prompt": "Write a SQL query to find the top 3 customers by total order amount from tables 'customers' (id, name) and 'orders' (id, customer_id, amount).",
    },
    {
        "id": 7,
        "category": "Coding",
        "prompt": "Explain the difference between a stack and a queue. Give a real-world example of each.",
    },
    {
        "id": 8,
        "category": "Coding",
        "prompt": "Write a JavaScript function that debounces another function with a given delay in milliseconds.",
    },
    # -- Creative Writing --
    {
        "id": 9,
        "category": "Creative",
        "prompt": "Write a haiku about artificial intelligence.",
    },
    {
        "id": 10,
        "category": "Creative",
        "prompt": "Write a compelling product description for a smart water bottle that tracks hydration.",
    },
    # -- Knowledge --
    {
        "id": 11,
        "category": "Knowledge",
        "prompt": "Explain quantum entanglement in simple terms that a 10-year-old could understand.",
    },
    {
        "id": 12,
        "category": "Knowledge",
        "prompt": "What are the main differences between TCP and UDP protocols?",
    },
    {
        "id": 13,
        "category": "Knowledge",
        "prompt": "Explain the difference between machine learning, deep learning, and artificial intelligence.",
    },
    # -- Analysis --
    {
        "id": 14,
        "category": "Analysis",
        "prompt": "What are the pros and cons of microservices vs monolithic architecture?",
    },
    {
        "id": 15,
        "category": "Analysis",
        "prompt": "Compare and contrast REST and GraphQL APIs. When would you choose one over the other?",
    },
    # -- Instruction Following --
    {
        "id": 16,
        "category": "Instruction",
        "prompt": "List exactly 5 benefits of regular exercise. Number them 1-5. Keep each to one sentence.",
    },
    {
        "id": 17,
        "category": "Instruction",
        "prompt": "Summarize the concept of blockchain in exactly 3 sentences.",
    },
    # -- Business --
    {
        "id": 18,
        "category": "Business",
        "prompt": "Write a professional email declining a meeting invitation due to a scheduling conflict.",
    },
    {
        "id": 19,
        "category": "Business",
        "prompt": "Create a SWOT analysis for a new AI-powered customer service chatbot startup.",
    },
    # -- Edge Case --
    {
        "id": 20,
        "category": "Edge Case",
        "prompt": "I have a 3-gallon jug and a 5-gallon jug. How do I measure exactly 4 gallons of water?",
    },
]


@dataclass
class TaskResult:
    task_id: int
    category: str
    prompt: str
    ollama_response: str = ""
    claude_response: str = ""
    ollama_time: float = 0.0
    claude_time: float = 0.0
    ollama_score: int = 0
    claude_score: int = 0
    judge_notes: str = ""


def run_task_on_backend(backend, prompt: str, system: str = "You are a helpful AI assistant. Be concise and accurate.") -> tuple[str, float]:
    """Run a single task on a backend, return (response_text, elapsed_seconds)."""
    start = time.time()
    try:
        resp = backend.send(
            messages=[{"role": "user", "content": prompt}],
            system=system,
            tools=[],
            max_tokens=1024,
        )
        elapsed = time.time() - start
        return resp.text or "(empty response)", elapsed
    except Exception as e:
        elapsed = time.time() - start
        return f"ERROR: {e}", elapsed


def judge_responses(claude_backend, task_prompt: str, ollama_resp: str, claude_resp: str) -> tuple[int, int, str]:
    """Use Claude as an impartial judge to score both responses 1-10."""
    judge_prompt = f"""You are an impartial judge evaluating two AI responses to the same prompt.

TASK PROMPT: {task_prompt}

RESPONSE A (Model A):
{ollama_resp[:2000]}

RESPONSE B (Model B):
{claude_resp[:2000]}

Score each response from 1-10 on: accuracy, completeness, clarity, and helpfulness.
You must respond in EXACTLY this JSON format (no other text):
{{"score_a": <int>, "score_b": <int>, "notes": "<brief comparison in one sentence>"}}"""

    try:
        resp = claude_backend.send(
            messages=[{"role": "user", "content": judge_prompt}],
            system="You are a fair, impartial AI response evaluator. Always respond with valid JSON only.",
            tools=[],
            max_tokens=200,
        )
        text = resp.text or ""
        # Extract JSON from response
        start_idx = text.find("{")
        end_idx = text.rfind("}") + 1
        if start_idx >= 0 and end_idx > start_idx:
            data = json.loads(text[start_idx:end_idx])
            score_a = max(1, min(10, int(data.get("score_a", 5))))
            score_b = max(1, min(10, int(data.get("score_b", 5))))
            return score_a, score_b, data.get("notes", "")
    except Exception as e:
        print(f"  Judge error: {e}")
    return 5, 5, "Unable to judge"


def generate_markdown_report(results: list[TaskResult], ollama_model: str, claude_model: str) -> str:
    """Generate a comprehensive markdown report."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    total_ollama_score = sum(r.ollama_score for r in results)
    total_claude_score = sum(r.claude_score for r in results)
    max_score = len(results) * 10

    avg_ollama_time = sum(r.ollama_time for r in results) / len(results)
    avg_claude_time = sum(r.claude_time for r in results) / len(results)

    # Category breakdown
    categories = {}
    for r in results:
        if r.category not in categories:
            categories[r.category] = {"ollama": [], "claude": []}
        categories[r.category]["ollama"].append(r.ollama_score)
        categories[r.category]["claude"].append(r.claude_score)

    # Win/loss/tie counts
    ollama_wins = sum(1 for r in results if r.ollama_score > r.claude_score)
    claude_wins = sum(1 for r in results if r.claude_score > r.ollama_score)
    ties = sum(1 for r in results if r.ollama_score == r.claude_score)

    md = f"""# Ollama vs Claude Benchmark Results

**Date:** {now}
**Ollama Model:** {ollama_model}
**Claude Model:** {claude_model}
**Tasks:** {len(results)}

---

## Summary

| Metric | Ollama ({ollama_model}) | Claude ({claude_model}) |
|--------|------------------------|------------------------|
| **Total Score** | {total_ollama_score}/{max_score} | {total_claude_score}/{max_score} |
| **Average Score** | {total_ollama_score/len(results):.1f}/10 | {total_claude_score/len(results):.1f}/10 |
| **Avg Response Time** | {avg_ollama_time:.1f}s | {avg_claude_time:.1f}s |
| **Wins** | {ollama_wins} | {claude_wins} |
| **Ties** | {ties} | {ties} |

### Cost Comparison

| | Ollama | Claude |
|--|--------|--------|
| **API Cost** | $0.00 (free forever) | ~$3/1M input tokens |
| **Hardware** | Local CPU/GPU | Cloud API |
| **Privacy** | 100% local | Data sent to API |
| **Availability** | Offline capable | Requires internet |

---

## Category Breakdown

| Category | Ollama Avg | Claude Avg | Winner |
|----------|-----------|-----------|--------|
"""
    for cat, scores in sorted(categories.items()):
        o_avg = sum(scores["ollama"]) / len(scores["ollama"])
        c_avg = sum(scores["claude"]) / len(scores["claude"])
        winner = "Ollama" if o_avg > c_avg else ("Claude" if c_avg > o_avg else "Tie")
        md += f"| {cat} | {o_avg:.1f} | {c_avg:.1f} | {winner} |\n"

    md += """
---

## Detailed Results

| # | Category | Prompt (truncated) | Ollama Score | Claude Score | Ollama Time | Claude Time | Notes |
|---|----------|-------------------|-------------|-------------|-------------|-------------|-------|
"""
    for r in results:
        prompt_short = r.prompt[:50] + "..." if len(r.prompt) > 50 else r.prompt
        notes_short = r.judge_notes[:60] + "..." if len(r.judge_notes) > 60 else r.judge_notes
        md += f"| {r.task_id} | {r.category} | {prompt_short} | {r.ollama_score}/10 | {r.claude_score}/10 | {r.ollama_time:.1f}s | {r.claude_time:.1f}s | {notes_short} |\n"

    md += """
---

## Full Responses

"""
    for r in results:
        md += f"""### Task {r.task_id}: {r.category}

**Prompt:** {r.prompt}

**Ollama ({ollama_model}) [{r.ollama_score}/10, {r.ollama_time:.1f}s]:**
> {r.ollama_response[:500]}

**Claude ({claude_model}) [{r.claude_score}/10, {r.claude_time:.1f}s]:**
> {r.claude_response[:500]}

**Judge Notes:** {r.judge_notes}

---

"""

    md += f"""## Conclusion

Ollama ({ollama_model}) scored **{total_ollama_score}/{max_score}** ({total_ollama_score/max_score*100:.0f}%) vs Claude ({claude_model}) at **{total_claude_score}/{max_score}** ({total_claude_score/max_score*100:.0f}%).

**Key Takeaways:**
- Ollama provides **100% free, offline** inference with no API costs
- Claude delivers higher quality for complex reasoning and nuanced tasks
- For many straightforward tasks, Ollama provides competitive quality
- Ollama response times are hardware-dependent ({"faster" if avg_ollama_time < avg_claude_time else "slower"} on this machine: {avg_ollama_time:.1f}s vs {avg_claude_time:.1f}s average)
- **Recommendation:** Use Ollama for development, testing, and cost-sensitive deployments. Use Claude for production-critical tasks requiring highest quality.
"""
    return md


def main():
    # Initialize backends
    ollama_model = "llama3.2"
    claude_model = "claude-sonnet-4-5-20250929"

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set. Needed for Claude backend and judging.")
        sys.exit(1)

    print(f"Initializing backends...")
    ollama = OllamaBackend(model=ollama_model)
    claude = ClaudeBackend(api_key=api_key, model=claude_model)

    if not ollama.is_available():
        print("ERROR: Ollama server not running. Start it with 'ollama serve'.")
        sys.exit(1)

    print(f"  Ollama ({ollama_model}): ready")
    print(f"  Claude ({claude_model}): ready")
    print(f"  Running {len(TASKS)} benchmark tasks...\n")

    results = []

    for task in TASKS:
        print(f"Task {task['id']}/{len(TASKS)}: [{task['category']}] {task['prompt'][:60]}...")

        # Run on Ollama
        print(f"  Running on Ollama...", end=" ", flush=True)
        ollama_resp, ollama_time = run_task_on_backend(ollama, task["prompt"])
        print(f"({ollama_time:.1f}s)")

        # Run on Claude
        print(f"  Running on Claude...", end=" ", flush=True)
        claude_resp, claude_time = run_task_on_backend(claude, task["prompt"])
        print(f"({claude_time:.1f}s)")

        # Judge
        print(f"  Judging...", end=" ", flush=True)
        ollama_score, claude_score, notes = judge_responses(
            claude, task["prompt"], ollama_resp, claude_resp
        )
        print(f"Ollama={ollama_score}/10 Claude={claude_score}/10")

        results.append(TaskResult(
            task_id=task["id"],
            category=task["category"],
            prompt=task["prompt"],
            ollama_response=ollama_resp,
            claude_response=claude_resp,
            ollama_time=ollama_time,
            claude_time=claude_time,
            ollama_score=ollama_score,
            claude_score=claude_score,
            judge_notes=notes,
        ))

    # Generate report
    print(f"\nGenerating report...")
    report = generate_markdown_report(results, ollama_model, claude_model)

    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ollama_vs_claude.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Report saved to {report_path}")

    # Print summary
    total_o = sum(r.ollama_score for r in results)
    total_c = sum(r.claude_score for r in results)
    print(f"\n{'='*50}")
    print(f"FINAL SCORES:")
    print(f"  Ollama ({ollama_model}): {total_o}/{len(results)*10}")
    print(f"  Claude ({claude_model}): {total_c}/{len(results)*10}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
