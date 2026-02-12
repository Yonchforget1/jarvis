"""Tests for the memory system."""

from __future__ import annotations

import json

import pytest

from jarvis.memory import Memory


@pytest.fixture
def memory(tmp_path):
    return Memory(memory_dir=tmp_path / "memory")


def test_save_and_get(memory):
    memory.save_learning("coding", "Always test first", "During refactor")
    learnings = memory.get_learnings()
    assert len(learnings) == 1
    assert learnings[0]["category"] == "coding"
    assert learnings[0]["insight"] == "Always test first"


def test_count(memory):
    assert memory.count == 0
    memory.save_learning("test", "insight 1")
    assert memory.count == 1
    memory.save_learning("test", "insight 2")
    assert memory.count == 2


def test_filter_by_category(memory):
    memory.save_learning("coding", "Use pytest")
    memory.save_learning("debugging", "Check logs first")
    memory.save_learning("coding", "Type hints help")

    coding = memory.get_learnings(category="coding")
    assert len(coding) == 2
    debugging = memory.get_learnings(category="debugging")
    assert len(debugging) == 1


def test_keyword_search(memory):
    memory.save_learning("coding", "Python type hints improve readability")
    memory.save_learning("debugging", "Always check error logs")
    memory.save_learning("coding", "Use pytest for testing")

    results = memory._keyword_search("pytest testing", 5)
    assert len(results) >= 1
    assert "pytest" in results[0]["text"].lower()


def test_limit(memory):
    for i in range(20):
        memory.save_learning("test", f"Insight {i}")
    learnings = memory.get_learnings(limit=5)
    assert len(learnings) == 5


def test_learning_has_timestamp(memory):
    memory.save_learning("test", "timestamped")
    learnings = memory.get_learnings()
    assert "timestamp" in learnings[0]


def test_learning_has_id(memory):
    lid = memory.save_learning("test", "with id")
    assert len(lid) == 12
    learnings = memory.get_learnings()
    assert learnings[0]["id"] == lid
