import json
import os
from datetime import datetime, timezone


class Memory:
    """Persistent memory for learnings across sessions."""

    def __init__(self, path: str = "memory/learnings.json", use_vectors: bool = False):
        self.path = path
        self._learnings: list[dict] = []
        self._summary_cache: str | None = None
        self._summary_cache_count: int = 0
        self.load()

    def load(self) -> None:
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
        self._summary_cache = None  # Invalidate cache
        return entry

    def get_summary(self, max_entries: int = 20) -> str:
        """Return a formatted string of recent learnings for prompt injection.

        Results are cached and invalidated when new learnings are saved.
        """
        if not self._learnings:
            return ""
        # Return cached summary if nothing changed
        if self._summary_cache is not None and self._summary_cache_count == len(self._learnings):
            return self._summary_cache
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
        result = "\n".join(lines)
        self._summary_cache = result
        self._summary_cache_count = len(self._learnings)
        return result

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
