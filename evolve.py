#!/usr/bin/env python3
"""
JARVIS Evolution Engine - Autonomous Self-Improvement Loop

Reads the Jarvis codebase, researches latest AI agent techniques, compares against
competitors, generates improvement plans via LLM, implements changes on isolated
git branches, tests them, logs everything, and repeats.

Usage:
    python evolve.py                     # Run forever with dashboard
    python evolve.py --once              # Run one cycle and exit
    python evolve.py --dry-run           # Analyze and plan but don't write files
    python evolve.py --dry-run --once    # Single dry-run cycle
    python evolve.py --no-dashboard      # Plain text output instead of rich UI
    python evolve.py --interval 120      # Custom interval in seconds
"""

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import textwrap
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
EVOLUTION_LOG_PATH = os.path.join(PROJECT_ROOT, "memory", "evolution_log.json")

SAFE_DIRS = [
    "jarvis/tools/",
    "plugins/",
    "jarvis/core/",
    "tests/",
]

FORBIDDEN_PATHS = [
    "evolve.py",
    ".env",
    ".git",
    "config.yaml",
    "memory/",
    "jarvis/config.py",
    "jarvis/conversation.py",
    "jarvis/memory.py",
    "jarvis/tool_registry.py",
    "jarvis/backends/",
    "agent.py",
    "api/",
]

COMPETITORS = [
    {
        "name": "AutoGPT",
        "search": "AutoGPT latest features autonomous agent 2026",
    },
    {
        "name": "CrewAI",
        "search": "CrewAI multi-agent framework capabilities 2026",
    },
    {
        "name": "LangGraph",
        "search": "LangGraph agent orchestration state machines 2026",
    },
    {
        "name": "OpenDevin",
        "search": "OpenDevin AI coding agent capabilities 2026",
    },
]

DEFAULT_INTERVAL = 300  # 5 minutes

EVOLUTION_SYSTEM_PROMPT = textwrap.dedent("""\
    You are the JARVIS Evolution Engine -- an autonomous self-improvement system
    for the JARVIS AI agent platform.

    Your role: analyze the codebase, review competitor capabilities and latest
    research, then propose small, safe, high-impact improvements.

    CONSTRAINTS:
    - You may ONLY create or modify files in: jarvis/tools/, plugins/, jarvis/core/, tests/
    - You may NEVER modify: evolve.py, .env, config.yaml, agent.py, jarvis/config.py,
      jarvis/conversation.py, jarvis/backends/*, jarvis/memory.py, jarvis/tool_registry.py
    - Each improvement must be a COMPLETE, WORKING Python file (not a diff or partial snippet)
    - Each improvement must include test code that validates it works
    - Prefer NEW files over modifying existing ones (safer, easier to review)
    - Maximum 3 improvements per cycle
    - Each file must be under 500 lines
    - All new tools MUST follow the existing ToolDef registration pattern
    - Code must be production-quality with proper error handling

    OUTPUT FORMAT: Return ONLY valid JSON (no markdown fences, no commentary) matching:
    {
      "reasoning": "1-2 sentences on why these improvements matter",
      "improvements": [
        {
          "id": "kebab-case-identifier",
          "description": "What this does and why",
          "target_file": "relative/path/to/file.py",
          "category": "new_tool|enhancement|refactor",
          "priority": "high|medium|low",
          "file_content": "complete python file content...",
          "test_code": "python code that exits 0 on success, 1 on failure"
        }
      ]
    }
""")


# ============================================================================
# EvolutionLog -- Persistent JSON log of all evolution cycles
# ============================================================================

class EvolutionLog:
    """Manages structured logging of every evolution cycle to JSON."""

    def __init__(self, path: str = EVOLUTION_LOG_PATH):
        self.path = path
        self._cycles: list[dict] = []
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._cycles = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._cycles = []
        else:
            self._cycles = []

    def _save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._cycles, f, indent=2, ensure_ascii=False)

    def start_cycle(self) -> int:
        cycle_id = len(self._cycles) + 1
        entry = {
            "cycle_id": cycle_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "started",
            "duration_seconds": 0,
            "research_summary": "",
            "plan": None,
            "changes_made": [],
            "test_results": None,
            "git_branch": "",
            "outcome": "in_progress",
            "error": None,
        }
        self._cycles.append(entry)
        self._save()
        return cycle_id

    def update_cycle(self, cycle_id: int, **fields):
        idx = cycle_id - 1
        if 0 <= idx < len(self._cycles):
            self._cycles[idx].update(fields)
            self._save()

    def complete_cycle(self, cycle_id: int, outcome: str, duration: float):
        self.update_cycle(
            cycle_id,
            outcome=outcome,
            phase="complete",
            duration_seconds=round(duration, 1),
        )

    def get_stats(self) -> dict:
        total = len(self._cycles)
        successful = sum(1 for c in self._cycles if c.get("outcome") == "success")
        total_improvements = sum(
            len(c.get("changes_made") or [])
            for c in self._cycles
            if c.get("outcome") == "success"
        )
        return {
            "total_cycles": total,
            "successful": successful,
            "success_rate": round(successful / total * 100, 1) if total else 0,
            "total_improvements": total_improvements,
        }

    def get_recent(self, n: int = 5) -> list[dict]:
        return self._cycles[-n:] if self._cycles else []


# ============================================================================
# CodebaseAnalyzer -- Reads own source tree to build self-awareness snapshot
# ============================================================================

class CodebaseAnalyzer:
    """Scans the Jarvis codebase and produces a structured state snapshot."""

    def __init__(self, root: str = PROJECT_ROOT):
        self.root = root

    def analyze(self) -> dict:
        files = self._collect_files()
        tools = self._collect_tools(files)
        git_log = self._git_log()
        return {
            "files": files,
            "tools": tools,
            "git_log": git_log,
            "total_lines": sum(f["lines"] for f in files),
            "total_files": len(files),
        }

    def _collect_files(self) -> list[dict]:
        result = []
        scan_dirs = ["jarvis", "plugins"]
        scan_root_files = ["agent.py", "evolve.py"]

        for d in scan_dirs:
            full = os.path.join(self.root, d)
            if not os.path.isdir(full):
                continue
            for dirpath, _, filenames in os.walk(full):
                for fn in filenames:
                    if fn.endswith(".py"):
                        fpath = os.path.join(dirpath, fn)
                        rel = os.path.relpath(fpath, self.root).replace("\\", "/")
                        try:
                            lines = len(Path(fpath).read_text(encoding="utf-8").splitlines())
                        except Exception:
                            lines = 0
                        result.append({"path": rel, "lines": lines})

        for fn in scan_root_files:
            fpath = os.path.join(self.root, fn)
            if os.path.isfile(fpath):
                try:
                    lines = len(Path(fpath).read_text(encoding="utf-8").splitlines())
                except Exception:
                    lines = 0
                result.append({"path": fn, "lines": lines})

        return result

    def _collect_tools(self, files: list[dict]) -> list[str]:
        tools = []
        for f in files:
            fpath = os.path.join(self.root, f["path"])
            try:
                content = Path(fpath).read_text(encoding="utf-8")
                for m in re.finditer(r'ToolDef\(\s*name\s*=\s*["\']([^"\']+)["\']', content):
                    tools.append(m.group(1))
            except Exception:
                pass
        return tools

    def _git_log(self) -> str:
        try:
            r = subprocess.run(
                ["git", "log", "--oneline", "-15"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return r.stdout.strip()
        except Exception:
            return "(git log unavailable)"

    def to_prompt_text(self, analysis: dict) -> str:
        lines = ["## Codebase Snapshot"]
        lines.append(f"Total files: {analysis['total_files']} | Total lines: {analysis['total_lines']}")
        lines.append("")
        lines.append("### File Tree")
        for f in analysis["files"]:
            lines.append(f"  {f['path']} ({f['lines']} lines)")
        lines.append("")
        lines.append("### Registered Tools")
        for t in analysis["tools"]:
            lines.append(f"  - {t}")
        lines.append("")
        lines.append("### Recent Git History")
        lines.append(analysis["git_log"])
        return "\n".join(lines)


# ============================================================================
# ResearchEngine -- Searches the internet for latest AI agent techniques
# ============================================================================

class ResearchEngine:
    """Performs web research on AI agent techniques and competitor capabilities."""

    def __init__(self):
        # Import from existing jarvis tools
        from jarvis.tools.web import search_web, fetch_url
        self._search = search_web
        self._fetch = fetch_url

    def research(self, cycle_num: int, dashboard=None) -> str:
        findings = []

        # 1. General AI agent research
        self._log(dashboard, "Searching: latest AI agent techniques 2026")
        result = self._search("latest AI agent framework techniques autonomous 2026")
        findings.append(f"## General AI Agent Research\n{result[:3000]}")
        time.sleep(2)

        # 2. Competitor deep-dive (rotate)
        competitor = COMPETITORS[cycle_num % len(COMPETITORS)]
        self._log(dashboard, f"Researching competitor: {competitor['name']}")
        result = self._search(competitor["search"])
        findings.append(f"## {competitor['name']} Analysis\n{result[:3000]}")
        time.sleep(2)

        # 3. Self-improvement / autonomous coding research
        self._log(dashboard, "Searching: AI self-improvement patterns")
        result = self._search("AI agent self-improvement autonomous code generation best practices 2026")
        findings.append(f"## Self-Improvement Techniques\n{result[:3000]}")
        time.sleep(2)

        return "\n\n".join(findings)

    @staticmethod
    def _log(dashboard, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        if dashboard:
            dashboard.add_research_line(f"[{ts}] {msg}")


# ============================================================================
# EvolutionPlanner -- Sends state + research to LLM, gets improvement plan
# ============================================================================

class EvolutionPlanner:
    """Uses the configured LLM backend to generate improvement plans."""

    def __init__(self):
        from jarvis.config import Config
        from jarvis.backends import create_backend

        self.config = Config.load()
        self.backend = create_backend(self.config)

    def plan(
        self,
        codebase_text: str,
        research_text: str,
        recent_cycles: list[dict],
    ) -> dict | None:
        # Build the user prompt
        history_text = self._format_history(recent_cycles)
        user_msg = (
            f"{codebase_text}\n\n"
            f"## Recent Evolution History\n{history_text}\n\n"
            f"## Latest Research\n{research_text}\n\n"
            "## Your Task\n"
            "Produce exactly 1-2 concrete improvements for this cycle.\n\n"
            "CRITICAL: Your entire response must be a single JSON object. "
            "No markdown, no code fences, no commentary before or after. "
            "Start your response with { and end with }."
        )

        messages = [self.backend.format_user_message(user_msg)]

        # First attempt
        raw, response = self._call_llm(messages)
        self._log_raw_response(raw)
        result = self._parse_plan(raw)
        if result is not None:
            return result

        # Retry: ask explicitly for JSON only
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": (
            "That response was not valid JSON and could not be parsed. "
            "Please return ONLY a raw JSON object with no markdown fences, "
            "no explanation, no text before or after. Start with { and end with }."
        )})
        raw, _ = self._call_llm(messages)
        self._log_raw_response(raw)
        return self._parse_plan(raw)

    def _call_llm(self, messages: list) -> tuple[str, object]:
        try:
            response = self.backend.send(
                messages=messages,
                system=EVOLUTION_SYSTEM_PROMPT,
                tools=[],
                max_tokens=8192,
            )
        except Exception as e:
            raise RuntimeError(f"LLM API error: {e}") from e
        return response.text or "", response

    @staticmethod
    def _log_raw_response(raw: str):
        """Log raw LLM response for debugging."""
        log_path = os.path.join(PROJECT_ROOT, "memory", "evolution_raw_response.log")
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n")
                f.write(f"Response length: {len(raw)}\n")
                f.write(raw[:5000])
                f.write(f"\n{'='*60}\n")
        except Exception:
            pass

    def _parse_plan(self, raw: str) -> dict | None:
        # Strip markdown fences if present
        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

        try:
            plan = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON from mixed text
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if match:
                try:
                    plan = json.loads(match.group())
                except json.JSONDecodeError:
                    return None
            else:
                return None

        if "improvements" not in plan or not isinstance(plan["improvements"], list):
            return None
        return plan

    @staticmethod
    def _format_history(cycles: list[dict]) -> str:
        if not cycles:
            return "(No previous cycles)"
        lines = []
        for c in cycles:
            changes = c.get("changes_made") or []
            change_desc = ", ".join(ch.get("description", "?") for ch in changes) if changes else "none"
            lines.append(
                f"- Cycle {c['cycle_id']}: outcome={c.get('outcome','?')} | "
                f"changes: {change_desc}"
            )
        return "\n".join(lines)


# ============================================================================
# SafeExecutor -- Git-branched self-modification with safety checks
# ============================================================================

class SafeExecutor:
    """Implements improvements on isolated git branches with safety validation."""

    def __init__(self, root: str = PROJECT_ROOT, dry_run: bool = False):
        self.root = root
        self.dry_run = dry_run
        self.original_branch = self._current_branch()
        self._recover_if_needed()

    def _run_git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git"] + list(args),
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def _current_branch(self) -> str:
        r = self._run_git("rev-parse", "--abbrev-ref", "HEAD")
        return r.stdout.strip() or "main"

    def _recover_if_needed(self):
        """If a previous run crashed on an evolve/ branch, clean up."""
        current = self._current_branch()
        if current.startswith("evolve/"):
            self._run_git("checkout", ".")
            self._run_git("checkout", self.original_branch)
            self.original_branch = self._current_branch()

    def has_clean_tree(self) -> bool:
        r = self._run_git("status", "--porcelain")
        return r.stdout.strip() == ""

    def create_branch(self, cycle_id: int) -> str:
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        branch = f"evolve/cycle-{cycle_id}-{ts}"
        self._run_git("checkout", "-b", branch)
        return branch

    def validate_path(self, relative_path: str) -> tuple[bool, str]:
        normalized = relative_path.replace("\\", "/")
        abs_path = os.path.normpath(os.path.join(self.root, normalized))

        # Must stay within project root
        if not abs_path.startswith(self.root):
            return False, f"Path escapes project root: {normalized}"

        # Must not be forbidden
        for forbidden in FORBIDDEN_PATHS:
            if normalized == forbidden or normalized.startswith(forbidden):
                return False, f"Forbidden path: {normalized}"

        # Must be in an allowed directory
        if not any(normalized.startswith(safe) for safe in SAFE_DIRS):
            return False, f"Not in allowed directories: {normalized}"

        # Must be Python
        if not normalized.endswith(".py"):
            return False, f"Only .py files allowed: {normalized}"

        return True, "OK"

    def validate_content(self, content: str, filename: str) -> tuple[bool, str]:
        # Syntax check
        try:
            compile(content, filename, "exec")
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        # Size check
        lines = content.count("\n") + 1
        if lines > 500:
            return False, f"File too large: {lines} lines (max 500)"
        if len(content.encode("utf-8")) > 20480:
            return False, f"File too large: {len(content.encode('utf-8'))} bytes (max 20KB)"

        return True, "OK"

    def write_file(self, relative_path: str, content: str) -> tuple[bool, str]:
        ok, msg = self.validate_path(relative_path)
        if not ok:
            return False, msg
        ok, msg = self.validate_content(content, relative_path)
        if not ok:
            return False, msg

        if self.dry_run:
            return True, f"[DRY RUN] Would write {relative_path}"

        abs_path = os.path.join(self.root, relative_path.replace("\\", "/"))
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True, f"Wrote {relative_path}"

    def run_test(self, test_code: str, test_id: str) -> dict:
        """Write test code to a temp file and execute it."""
        if self.dry_run:
            return {"passed": 1, "failed": 0, "errors": [], "output": "[DRY RUN]"}

        test_dir = os.path.join(self.root, "tests")
        os.makedirs(test_dir, exist_ok=True)
        test_file = os.path.join(test_dir, f"_evolve_test_{test_id}.py")

        try:
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(test_code)

            r = subprocess.run(
                [sys.executable, test_file],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if r.returncode == 0:
                return {"passed": 1, "failed": 0, "errors": [], "output": r.stdout}
            else:
                return {
                    "passed": 0,
                    "failed": 1,
                    "errors": [r.stderr or r.stdout or "Non-zero exit code"],
                    "output": r.stdout + r.stderr,
                }
        except subprocess.TimeoutExpired:
            return {"passed": 0, "failed": 1, "errors": ["Test timed out (60s)"], "output": ""}
        except Exception as e:
            return {"passed": 0, "failed": 1, "errors": [str(e)], "output": ""}
        finally:
            # Clean up test file
            try:
                os.remove(test_file)
            except OSError:
                pass

    def commit(self, message: str) -> bool:
        if self.dry_run:
            return True
        self._run_git("add", "-A")
        r = self._run_git("commit", "-m", message)
        return r.returncode == 0

    def rollback(self):
        if not self.dry_run:
            self._run_git("checkout", ".")
        self.return_to_original()

    def return_to_original(self):
        if not self.dry_run:
            current = self._current_branch()
            if current != self.original_branch:
                self._run_git("checkout", self.original_branch)


# ============================================================================
# Dashboard -- Rich live terminal UI
# ============================================================================

class Dashboard:
    """Live terminal dashboard using the Rich library."""

    def __init__(self):
        from rich.console import Console
        from rich.layout import Layout
        from rich.panel import Panel
        from rich.table import Table
        from rich.live import Live
        from rich.text import Text

        self._Console = Console
        self._Layout = Layout
        self._Panel = Panel
        self._Table = Table
        self._Live = Live
        self._Text = Text

        self.console = Console()
        self._live: Live | None = None
        self._start_time = time.time()
        self._cycle_num = 0
        self._phase = "Initializing"
        self._phase_detail = ""
        self._countdown = 0
        self._research_lines: list[str] = []
        self._change_lines: list[str] = []
        self._plan_lines: list[str] = []
        self._stats = {
            "total_cycles": 0,
            "successful": 0,
            "success_rate": 0,
            "total_improvements": 0,
        }

    def start(self):
        self._live = self._Live(
            self._build_layout(),
            console=self.console,
            refresh_per_second=1,
            screen=False,
        )
        self._live.start()

    def stop(self):
        if self._live:
            self._live.stop()
            self._live = None

    def update_status(self, phase: str, detail: str = "", countdown: int = 0):
        self._phase = phase
        self._phase_detail = detail
        self._countdown = countdown
        self._refresh()

    def set_cycle(self, num: int):
        self._cycle_num = num
        self._refresh()

    def add_research_line(self, text: str):
        self._research_lines.append(text)
        if len(self._research_lines) > 15:
            self._research_lines = self._research_lines[-15:]
        self._refresh()

    def add_change(self, description: str):
        self._change_lines.append(description)
        if len(self._change_lines) > 20:
            self._change_lines = self._change_lines[-20:]
        self._refresh()

    def update_plan(self, items: list[str]):
        self._plan_lines = items
        self._refresh()

    def update_stats(self, stats: dict):
        self._stats = stats
        self._refresh()

    def _refresh(self):
        if self._live:
            self._live.update(self._build_layout())

    def _uptime(self) -> str:
        elapsed = int(time.time() - self._start_time)
        h, rem = divmod(elapsed, 3600)
        m, s = divmod(rem, 60)
        if h > 0:
            return f"{h}h {m}m {s}s"
        elif m > 0:
            return f"{m}m {s}s"
        return f"{s}s"

    def _build_layout(self):
        Panel = self._Panel
        Table = self._Table
        Layout = self._Layout
        Text = self._Text

        # -- Header --
        header_text = Text(justify="center")
        header_text.append("JARVIS EVOLUTION ENGINE", style="bold cyan")
        header_text.append(f"   Cycle #{self._cycle_num}", style="yellow")
        header_text.append(f"   Uptime: {self._uptime()}", style="dim")
        header = Panel(header_text, style="bold blue")

        # -- Status panel --
        status_lines = []
        status_lines.append(f"[bold]Phase:[/bold] [green]{self._phase}[/green]")
        if self._phase_detail:
            status_lines.append(f"  {self._phase_detail}")
        if self._countdown > 0:
            m, s = divmod(self._countdown, 60)
            status_lines.append(f"\n[dim]Next cycle: {m}m {s}s[/dim]")
        status_panel = Panel(
            "\n".join(status_lines) or "Starting...",
            title="[bold]Status[/bold]",
            border_style="green",
        )

        # -- Research feed --
        research_text = "\n".join(self._research_lines[-12:]) if self._research_lines else "[dim]Waiting...[/dim]"
        research_panel = Panel(
            research_text,
            title="[bold]Research Feed[/bold]",
            border_style="cyan",
        )

        # -- Changes panel --
        changes_text = "\n".join(self._change_lines[-10:]) if self._change_lines else "[dim]No changes yet[/dim]"
        changes_panel = Panel(
            changes_text,
            title="[bold]Changes[/bold]",
            border_style="yellow",
        )

        # -- Stats panel --
        stats_table = Table(show_header=False, box=None, padding=(0, 1))
        stats_table.add_column("Key", style="bold")
        stats_table.add_column("Value", style="cyan")
        stats_table.add_row("Total cycles", str(self._stats.get("total_cycles", 0)))
        stats_table.add_row("Successful", str(self._stats.get("successful", 0)))
        stats_table.add_row("Success rate", f"{self._stats.get('success_rate', 0)}%")
        stats_table.add_row("Improvements", str(self._stats.get("total_improvements", 0)))
        stats_panel = Panel(
            stats_table,
            title="[bold]Statistics[/bold]",
            border_style="magenta",
        )

        # -- Plan panel --
        plan_text = "\n".join(self._plan_lines) if self._plan_lines else "[dim]No active plan[/dim]"
        plan_panel = Panel(
            plan_text,
            title="[bold]Current Plan[/bold]",
            border_style="white",
        )

        # -- Layout assembly --
        layout = Layout()
        layout.split_column(
            Layout(header, name="header", size=3),
            Layout(name="top", ratio=3),
            Layout(name="bottom", ratio=3),
            Layout(plan_panel, name="plan", size=6),
        )
        layout["top"].split_row(
            Layout(status_panel, name="status", ratio=1),
            Layout(research_panel, name="research", ratio=2),
        )
        layout["bottom"].split_row(
            Layout(changes_panel, name="changes", ratio=1),
            Layout(stats_panel, name="stats", ratio=1),
        )

        return layout


class PlainDashboard:
    """Fallback dashboard that prints to stdout when Rich is not desired."""

    def start(self): pass
    def stop(self): pass

    def update_status(self, phase: str, detail: str = "", countdown: int = 0):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] Phase: {phase}" + (f" - {detail}" if detail else ""))

    def set_cycle(self, num: int):
        print(f"\n{'='*60}")
        print(f"  EVOLUTION CYCLE #{num}")
        print(f"{'='*60}")

    def add_research_line(self, text: str):
        print(f"  [Research] {text}")

    def add_change(self, description: str):
        print(f"  [Change] {description}")

    def update_plan(self, items: list[str]):
        for item in items:
            print(f"  [Plan] {item}")

    def update_stats(self, stats: dict):
        print(
            f"  [Stats] Cycles: {stats.get('total_cycles', 0)} | "
            f"Success: {stats.get('successful', 0)} | "
            f"Improvements: {stats.get('total_improvements', 0)}"
        )


# ============================================================================
# EvolutionCycle -- Orchestrates one full evolution cycle
# ============================================================================

class EvolutionCycle:
    """Runs one complete evolution cycle: analyze -> research -> plan -> execute -> test -> log."""

    def __init__(
        self,
        analyzer: CodebaseAnalyzer,
        researcher: ResearchEngine,
        planner: EvolutionPlanner,
        executor: SafeExecutor,
        log: EvolutionLog,
        dashboard,
        memory=None,
    ):
        self.analyzer = analyzer
        self.researcher = researcher
        self.planner = planner
        self.executor = executor
        self.log = log
        self.dash = dashboard
        self.memory = memory

    def run_one(self) -> dict:
        start = time.time()
        cycle_id = self.log.start_cycle()
        self.dash.set_cycle(cycle_id)

        try:
            # --- Phase 1: Analyze ---
            self.dash.update_status("Analyzing codebase", "Scanning files and tools...")
            self.log.update_cycle(cycle_id, phase="analyzing")
            analysis = self.analyzer.analyze()
            codebase_text = self.analyzer.to_prompt_text(analysis)
            self.dash.add_research_line(
                f"[{self._ts()}] Codebase: {analysis['total_files']} files, "
                f"{analysis['total_lines']} lines, {len(analysis['tools'])} tools"
            )

            # --- Phase 2: Research ---
            self.dash.update_status("Researching", "Searching latest AI agent techniques...")
            self.log.update_cycle(cycle_id, phase="researching")
            try:
                research_text = self.researcher.research(cycle_id, self.dash)
            except Exception as e:
                research_text = f"(Research failed: {e})"
                self.dash.add_research_line(f"[{self._ts()}] Research error: {e}")
            self.log.update_cycle(cycle_id, research_summary=research_text[:2000])

            # --- Phase 3: Plan ---
            self.dash.update_status("Planning improvements", "Consulting LLM...")
            self.log.update_cycle(cycle_id, phase="planning")
            recent = self.log.get_recent(5)
            try:
                plan = self.planner.plan(codebase_text, research_text, recent)
            except Exception as e:
                self._fail(cycle_id, start, f"LLM planning error: {e}")
                return self.log.get_recent(1)[0]

            if plan is None:
                self._fail(cycle_id, start, "LLM returned invalid plan (could not parse JSON)")
                return self.log.get_recent(1)[0]

            improvements = plan.get("improvements", [])
            if not improvements:
                self._fail(cycle_id, start, "LLM returned empty plan")
                return self.log.get_recent(1)[0]

            # Show plan on dashboard
            plan_display = []
            for imp in improvements:
                prio = imp.get("priority", "?").upper()
                desc = imp.get("description", "?")[:80]
                plan_display.append(f"[{prio}] {desc}")
            self.dash.update_plan(plan_display)
            self.log.update_cycle(cycle_id, plan={
                "reasoning": plan.get("reasoning", ""),
                "improvements": [
                    {"id": i.get("id"), "description": i.get("description"),
                     "target_file": i.get("target_file"), "category": i.get("category"),
                     "priority": i.get("priority")}
                    for i in improvements
                ],
            })

            # --- Phase 4: Validate plan ---
            self.dash.update_status("Validating plan", "Checking safety constraints...")
            valid_improvements = []
            for imp in improvements:
                target = imp.get("target_file", "")
                content = imp.get("file_content", "")
                ok, msg = self.executor.validate_path(target)
                if not ok:
                    self.dash.add_research_line(f"[{self._ts()}] Rejected {target}: {msg}")
                    continue
                ok, msg = self.executor.validate_content(content, target)
                if not ok:
                    self.dash.add_research_line(f"[{self._ts()}] Rejected {target}: {msg}")
                    continue
                valid_improvements.append(imp)

            if not valid_improvements:
                self._fail(cycle_id, start, "All improvements failed validation")
                return self.log.get_recent(1)[0]

            # --- Phase 5: Execute ---
            self.dash.update_status("Implementing changes", f"{len(valid_improvements)} improvement(s)...")
            self.log.update_cycle(cycle_id, phase="executing")

            # Check for clean working tree
            if not self.executor.dry_run and not self.executor.has_clean_tree():
                self._fail(cycle_id, start, "Working tree has uncommitted changes, skipping")
                return self.log.get_recent(1)[0]

            branch = self.executor.create_branch(cycle_id) if not self.executor.dry_run else f"evolve/cycle-{cycle_id}-dryrun"
            self.log.update_cycle(cycle_id, git_branch=branch)

            changes_made = []
            for imp in valid_improvements:
                target = imp.get("target_file", "")
                content = imp.get("file_content", "")
                ok, msg = self.executor.write_file(target, content)
                self.dash.add_change(f"Cycle {cycle_id}: {'+' if ok else '!'} {target}")
                if ok:
                    changes_made.append({
                        "file": target,
                        "action": "created",
                        "lines_changed": content.count("\n") + 1,
                        "description": imp.get("description", "")[:100],
                    })

            if not changes_made:
                self.executor.rollback()
                self._fail(cycle_id, start, "No files were successfully written")
                return self.log.get_recent(1)[0]

            # --- Phase 6: Test ---
            self.dash.update_status("Testing changes", f"Running {len(valid_improvements)} test(s)...")
            self.log.update_cycle(cycle_id, phase="testing")

            total_passed = 0
            total_failed = 0
            all_errors = []

            for imp in valid_improvements:
                test_code = imp.get("test_code", "")
                if not test_code:
                    total_passed += 1
                    continue
                result = self.executor.run_test(test_code, imp.get("id", "unknown"))
                total_passed += result["passed"]
                total_failed += result["failed"]
                all_errors.extend(result.get("errors", []))

            test_results = {
                "passed": total_passed,
                "failed": total_failed,
                "errors": all_errors[:5],  # Keep first 5 errors
            }
            self.log.update_cycle(cycle_id, test_results=test_results)

            if total_failed > 0:
                self.dash.add_research_line(f"[{self._ts()}] Tests failed: {all_errors[:2]}")
                self.executor.rollback()
                self.log.update_cycle(cycle_id, changes_made=changes_made)
                self.log.complete_cycle(cycle_id, "rolled_back", time.time() - start)
                self.dash.update_status("Cycle complete", "Rolled back (test failures)")
                self.dash.update_stats(self.log.get_stats())
                return self.log.get_recent(1)[0]

            # --- Phase 7: Commit ---
            self.dash.update_status("Committing changes", branch)
            self.log.update_cycle(cycle_id, phase="committing", changes_made=changes_made)

            descriptions = [imp.get("description", "?")[:60] for imp in valid_improvements]
            commit_msg = f"evolve(cycle-{cycle_id}): {'; '.join(descriptions)}"
            committed = self.executor.commit(commit_msg)
            self.executor.return_to_original()

            self.log.update_cycle(cycle_id, git_committed=committed)

            # --- Phase 8: Log and learn ---
            self.log.complete_cycle(cycle_id, "success", time.time() - start)
            self.dash.update_status("Cycle complete", f"Success - {len(changes_made)} improvement(s)")
            self.dash.update_stats(self.log.get_stats())

            # Write to memory system
            if self.memory:
                try:
                    change_summary = "; ".join(
                        ch["description"] for ch in changes_made
                    )
                    self.memory.save_learning(
                        category="self_improvement",
                        insight=f"Evolution cycle {cycle_id}: {change_summary}",
                        context=f"Branch: {branch}. Tests: {total_passed} passed, {total_failed} failed.",
                        task_description=f"Autonomous evolution cycle #{cycle_id}",
                    )
                except Exception:
                    pass  # Memory write failure is non-critical

            return self.log.get_recent(1)[0]

        except Exception as e:
            tb = traceback.format_exc()
            self._fail(cycle_id, start, f"Unexpected error: {e}\n{tb}")
            self.executor.return_to_original()
            return self.log.get_recent(1)[0]

    def _fail(self, cycle_id: int, start_time: float, error: str):
        self.log.update_cycle(cycle_id, error=error)
        self.log.complete_cycle(cycle_id, "error", time.time() - start_time)
        self.dash.update_status("Cycle failed", error[:80])
        self.dash.update_stats(self.log.get_stats())

    @staticmethod
    def _ts() -> str:
        return datetime.now().strftime("%H:%M:%S")


# ============================================================================
# Main entry point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="JARVIS Evolution Engine - Autonomous Self-Improvement Loop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python evolve.py                     Run forever with live dashboard
              python evolve.py --once              Single cycle then exit
              python evolve.py --dry-run --once    Plan without writing files
              python evolve.py --interval 120      2-minute intervals
        """),
    )
    parser.add_argument("--dry-run", action="store_true", help="Analyze and plan but don't write files")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL, help=f"Seconds between cycles (default: {DEFAULT_INTERVAL})")
    parser.add_argument("--no-dashboard", action="store_true", help="Plain text output instead of Rich UI")
    parser.add_argument("--max-cycles", type=int, default=0, help="Stop after N cycles (0 = unlimited)")
    args = parser.parse_args()

    # Initialize components
    print("Initializing JARVIS Evolution Engine...")

    log = EvolutionLog()
    analyzer = CodebaseAnalyzer()
    researcher = ResearchEngine()
    planner = EvolutionPlanner()
    executor = SafeExecutor(dry_run=args.dry_run)

    # Memory (optional, non-critical)
    memory = None
    try:
        from jarvis.memory import Memory
        memory = Memory(
            path=os.path.join(PROJECT_ROOT, "memory", "learnings.json"),
            use_vectors=False,  # Skip vector DB for evolution engine
        )
    except Exception:
        pass

    # Dashboard
    if args.no_dashboard:
        dashboard = PlainDashboard()
    else:
        try:
            dashboard = Dashboard()
        except ImportError:
            print("Rich library not available, falling back to plain output.")
            print("Install with: pip install rich")
            dashboard = PlainDashboard()

    cycle = EvolutionCycle(analyzer, researcher, planner, executor, log, dashboard, memory)

    # Graceful shutdown
    shutdown = False

    def handle_signal(signum, frame):
        nonlocal shutdown
        shutdown = True
        dashboard.update_status("Shutting down...", "Ctrl+C received")

    signal.signal(signal.SIGINT, handle_signal)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, handle_signal)

    # Main loop
    dashboard.start()
    cycles_run = 0

    try:
        while not shutdown:
            try:
                cycle.run_one()
                cycles_run += 1
            except Exception as e:
                dashboard.update_status("Error", str(e)[:80])
                traceback.print_exc()

            if args.once:
                break
            if args.max_cycles > 0 and cycles_run >= args.max_cycles:
                break

            # Countdown wait
            for remaining in range(args.interval, 0, -1):
                if shutdown:
                    break
                dashboard.update_status(
                    "Waiting for next cycle",
                    countdown=remaining,
                )
                time.sleep(1)
    finally:
        dashboard.stop()
        executor.return_to_original()

        # Summary
        stats = log.get_stats()
        print(f"\nJARVIS Evolution Engine stopped.")
        print(f"  Cycles run:    {stats['total_cycles']}")
        print(f"  Successful:    {stats['successful']}")
        print(f"  Success rate:  {stats['success_rate']}%")
        print(f"  Improvements:  {stats['total_improvements']}")


if __name__ == "__main__":
    main()
