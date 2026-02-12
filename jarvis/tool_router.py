"""Smart tool router – selects the most relevant tools per message.

Uses TF-IDF scoring to pick the top-N tools based on the user's message,
reducing token cost by only sending relevant tool schemas to the LLM.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.tool_registry import ToolDef

# Default number of tools to select
DEFAULT_TOP_K = 8


def _tokenize(text: str) -> list[str]:
    """Simple word tokenizer – lowercase, split on non-alpha."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _build_doc(tool: ToolDef) -> str:
    """Build a searchable document from a tool definition."""
    parts = [tool.name.replace("_", " "), tool.description]
    if tool.parameters:
        props = tool.parameters.get("properties", {})
        for key, val in props.items():
            parts.append(key.replace("_", " "))
            if isinstance(val, dict):
                desc = val.get("description", "")
                if desc:
                    parts.append(desc)
    return " ".join(parts)


class ToolRouter:
    """Scores tools against a query using TF-IDF and returns the top matches."""

    def __init__(self, tools: list[ToolDef]) -> None:
        self.tools = tools
        self._docs: list[list[str]] = []
        self._idf: dict[str, float] = {}
        self._build_index()

    def _build_index(self) -> None:
        """Compute IDF values across all tool documents."""
        self._docs = [_tokenize(_build_doc(t)) for t in self.tools]
        n = len(self._docs)
        if n == 0:
            return

        # Document frequency
        df: Counter[str] = Counter()
        for doc in self._docs:
            for word in set(doc):
                df[word] += 1

        # IDF = log(N / df)
        self._idf = {word: math.log(n / freq) for word, freq in df.items()}

    def score(self, query: str) -> list[tuple[ToolDef, float]]:
        """Score all tools against the query. Returns (tool, score) pairs sorted desc."""
        query_tokens = _tokenize(query)
        if not query_tokens:
            return [(t, 0.0) for t in self.tools]

        query_tf = Counter(query_tokens)
        results = []

        for i, tool in enumerate(self.tools):
            doc_tokens = self._docs[i]
            if not doc_tokens:
                results.append((tool, 0.0))
                continue

            doc_tf = Counter(doc_tokens)
            score = 0.0

            for word, q_count in query_tf.items():
                if word in doc_tf:
                    tf = doc_tf[word] / len(doc_tokens)
                    idf = self._idf.get(word, 0.0)
                    score += tf * idf * q_count

            results.append((tool, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def select(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[ToolDef]:
        """Select the top-K most relevant tools for a query."""
        scored = self.score(query)
        # Always include tools with score > 0, up to top_k
        selected = [t for t, s in scored[:top_k] if s > 0]

        # If fewer than top_k have positive scores, pad with highest-scoring zeros
        if len(selected) < top_k:
            remaining = [t for t, s in scored if s == 0]
            selected.extend(remaining[: top_k - len(selected)])

        return selected
