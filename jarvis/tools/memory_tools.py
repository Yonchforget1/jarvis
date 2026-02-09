import os
import subprocess

from jarvis.tool_registry import ToolDef


def register(registry, memory):
    """Register memory-related tools. Requires a Memory instance."""

    def reflect_on_task(
        category: str,
        insight: str,
        context: str = "",
        task_description: str = "",
    ) -> str:
        """Log a learning from the current task."""
        memory.save_learning(category, insight, context, task_description)
        return f"Learning saved: [{category}] {insight}"

    def recall_learnings(topic: str = "") -> str:
        """Retrieve past learnings, optionally filtered by topic."""
        if topic:
            entries = memory.get_relevant(topic)
            if not entries:
                return f"No learnings found related to '{topic}'."
            lines = [f"- [{e['category']}] {e['insight']}" for e in entries]
            return f"Found {len(entries)} relevant learnings:\n" + "\n".join(lines)
        else:
            summary = memory.get_summary()
            return summary if summary else "No learnings recorded yet."

    def self_improve(
        file_path: str, description: str, branch_name: str = ""
    ) -> str:
        """Create a git branch for improving Jarvis's own source code."""
        jarvis_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        if not branch_name:
            safe_desc = description[:30].replace(" ", "-").lower()
            safe_desc = "".join(c for c in safe_desc if c.isalnum() or c == "-")
            branch_name = f"self-improve/{safe_desc}"

        try:
            abs_path = os.path.abspath(file_path)
            if not abs_path.startswith(jarvis_root):
                return f"Error: Can only improve files within {jarvis_root}"

            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=jarvis_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return (
                f"Created branch '{branch_name}'. "
                f"Now use read_file and write_file to make changes to {file_path}, "
                f"then use run_shell to 'git add' and 'git commit' on this branch. "
                f"When done, use run_shell to 'git checkout master' to return. "
                f"The improvement branch can be reviewed and merged manually."
            )
        except subprocess.CalledProcessError as e:
            return f"Git error: {e.stderr}"
        except Exception as e:
            return f"Error: {e}"

    registry.register(
        ToolDef(
            name="reflect_on_task",
            description=(
                "Log a learning or insight from the current task. Call this after completing "
                "a task to record what worked, what failed, and what to do differently. "
                "Categories: error_handling, tool_usage, user_preference, coding, "
                "workflow, debugging, game_dev, general."
            ),
            parameters={
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category of the learning.",
                    },
                    "insight": {
                        "type": "string",
                        "description": "The insight or lesson learned.",
                    },
                    "context": {
                        "type": "string",
                        "description": "What triggered this learning.",
                        "default": "",
                    },
                    "task_description": {
                        "type": "string",
                        "description": "Brief description of the task.",
                        "default": "",
                    },
                },
                "required": ["category", "insight"],
            },
            func=reflect_on_task,
        )
    )

    registry.register(
        ToolDef(
            name="recall_learnings",
            description=(
                "Recall past learnings, optionally filtered by topic. Use this before "
                "starting a task to check what you've learned from similar work."
            ),
            parameters={
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Optional topic to filter by.",
                        "default": "",
                    },
                },
                "required": [],
            },
            func=recall_learnings,
        )
    )

    registry.register(
        ToolDef(
            name="self_improve",
            description=(
                "Start a self-improvement: creates a new git branch for modifying "
                "Jarvis's own source code. After calling this, use read_file/write_file "
                "to make changes, then git add/commit via run_shell. Changes go on a "
                "separate branch for human review -- never auto-merged."
            ),
            parameters={
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the source file to improve.",
                    },
                    "description": {
                        "type": "string",
                        "description": "What improvement to make and why.",
                    },
                    "branch_name": {
                        "type": "string",
                        "description": "Optional branch name. Auto-generated if empty.",
                        "default": "",
                    },
                },
                "required": ["file_path", "description"],
            },
            func=self_improve,
        )
    )
