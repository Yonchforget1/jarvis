import json
import os
from datetime import datetime, timezone


class Memory:
    """Persistent memory for learnings across sessions."""

    def __init__(self, path: str = "memory/learnings.json"):
        self.path = path
        self._learnings: list[dict] = []
        self.load()

    def load(self):
        """Load learnings from disk."""
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Handle both formats: plain list or {"learnings": [...]}
            if isinstance(data, dict):
                self._learnings = data.get("learnings", [])
            elif isinstance(data, list):
                self._learnings = data
            else:
                self._learnings = []
        else:
            self._learnings = []

    def _save(self):
        """Write learnings to disk."""
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._learnings, f, indent=2, ensure_ascii=False)

    def save_learning(
        self,
        category: str,
        insight: str,
        context: str = "",
        task_description: str = "",
    ) -> dict:
        """Append a learning entry and persist to disk."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category,
            "insight": insight,
            "context": context,
            "task_description": task_description,
        }
        self._learnings.append(entry)
        self._save()
        return entry

    def get_summary(self, max_entries: int = 20) -> str:
        """Return a formatted string of recent learnings for prompt injection."""
        if not self._learnings:
            return ""
        recent = self._learnings[-max_entries:]
        lines = []
        for entry in recent:
            category = entry.get("category", entry.get("task", "general"))
            insight = entry.get("insight", entry.get("lesson", str(entry)))
            line = f"- [{category}] {insight}"
            context = entry.get("context", "")
            if context:
                line += f" (context: {context})"
            lines.append(line)
        return "\n".join(lines)

    def get_relevant(self, topic: str) -> list[dict]:
        """Return learnings matching a topic keyword across all fields."""
        topic_lower = topic.lower()
        return [
            e
            for e in self._learnings
            if topic_lower in e.get("category", "").lower()
            or topic_lower in e.get("insight", "").lower()
            or topic_lower in e.get("context", "").lower()
            or topic_lower in e.get("task_description", "").lower()
        ]

    @property
    def count(self) -> int:
        return len(self._learnings)

    @property
    def all_learnings(self) -> list[dict]:
        """Public accessor for all learnings."""
        return list(self._learnings)
