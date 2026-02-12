"""Memory system – persistent learnings with vector search."""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("jarvis.memory")

_MEMORY_DIR = Path(__file__).resolve().parent.parent / "memory"
_LEARNINGS_FILE = _MEMORY_DIR / "learnings.json"
_VECTOR_DIR = _MEMORY_DIR / "vector_db"


class Memory:
    """Persistent memory with JSON learnings and optional vector search."""

    def __init__(self, memory_dir: Path | None = None) -> None:
        self.memory_dir = memory_dir or _MEMORY_DIR
        self.learnings_file = self.memory_dir / "learnings.json"
        self.vector_dir = self.memory_dir / "vector_db"
        self._collection = None

    def _ensure_dir(self) -> None:
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    # ── Learnings (JSON) ────────────────────────────────────

    def _load_learnings(self) -> list[dict]:
        if self.learnings_file.exists():
            try:
                return json.loads(self.learnings_file.read_text())
            except json.JSONDecodeError:
                return []
        return []

    def _save_learnings(self, learnings: list[dict]) -> None:
        self._ensure_dir()
        self.learnings_file.write_text(json.dumps(learnings, indent=2))

    def save_learning(
        self,
        category: str,
        insight: str,
        context: str = "",
        task_description: str = "",
    ) -> str:
        """Save a learning/insight to memory. Returns the learning ID."""
        learnings = self._load_learnings()
        learning_id = uuid.uuid4().hex[:12]
        entry = {
            "id": learning_id,
            "category": category,
            "insight": insight,
            "context": context,
            "task_description": task_description,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        learnings.append(entry)
        self._save_learnings(learnings)

        # Also add to vector DB if available
        self._add_to_vector(learning_id, f"{category}: {insight}\n{context}")

        log.info("Saved learning %s: %s", learning_id, insight[:80])
        return learning_id

    def get_learnings(self, category: str = "", limit: int = 50) -> list[dict]:
        """Get recent learnings, optionally filtered by category."""
        learnings = self._load_learnings()
        if category:
            learnings = [l for l in learnings if l.get("category") == category]
        return learnings[-limit:]

    @property
    def count(self) -> int:
        return len(self._load_learnings())

    # ── Vector Search (ChromaDB) ────────────────────────────

    def _get_collection(self):
        if self._collection is not None:
            return self._collection
        try:
            import chromadb

            client = chromadb.PersistentClient(path=str(self.vector_dir))
            self._collection = client.get_or_create_collection(
                name="jarvis_memory",
                metadata={"hnsw:space": "cosine"},
            )
            return self._collection
        except Exception as e:
            log.warning("ChromaDB not available: %s", e)
            return None

    def _add_to_vector(self, doc_id: str, text: str) -> None:
        col = self._get_collection()
        if col is None:
            return
        try:
            col.add(
                ids=[doc_id],
                documents=[text],
                metadatas=[{"timestamp": datetime.now(timezone.utc).isoformat()}],
            )
        except Exception as e:
            log.warning("Failed to add to vector DB: %s", e)

    def search(self, query: str, n_results: int = 5) -> list[dict]:
        """Semantic search over memory using vector DB."""
        col = self._get_collection()
        if col is None:
            # Fallback to keyword search in learnings
            return self._keyword_search(query, n_results)

        try:
            results = col.query(query_texts=[query], n_results=n_results)
            docs = results.get("documents", [[]])[0]
            dists = results.get("distances", [[]])[0]
            ids = results.get("ids", [[]])[0]
            return [
                {"id": ids[i], "text": docs[i], "distance": dists[i]}
                for i in range(len(docs))
            ]
        except Exception as e:
            log.warning("Vector search failed: %s", e)
            return self._keyword_search(query, n_results)

    def _keyword_search(self, query: str, limit: int) -> list[dict]:
        """Simple keyword-based fallback search."""
        query_lower = query.lower()
        learnings = self._load_learnings()
        scored = []
        for l in learnings:
            text = f"{l.get('category', '')} {l.get('insight', '')} {l.get('context', '')}".lower()
            score = sum(1 for word in query_lower.split() if word in text)
            if score > 0:
                scored.append((score, l))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {"id": l["id"], "text": l["insight"], "distance": 1.0 / (s + 1)}
            for s, l in scored[:limit]
        ]
