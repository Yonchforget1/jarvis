"""Tests for Memory: save_learning, get_relevant, get_summary, all_learnings."""

import json
import os
import tempfile

import pytest

from jarvis.memory import Memory


@pytest.fixture
def memory(tmp_path):
    """Return a Memory instance backed by a temp file."""
    return Memory(path=str(tmp_path / "learnings.json"))


def test_save_and_count(memory):
    assert memory.count == 0
    memory.save_learning("test", "Insight 1", "some context", "task desc")
    assert memory.count == 1


def test_save_creates_file(memory):
    memory.save_learning("test", "data", "", "")
    assert os.path.exists(memory.path)
    with open(memory.path) as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["category"] == "test"


def test_all_learnings(memory):
    memory.save_learning("cat1", "insight1", "", "")
    memory.save_learning("cat2", "insight2", "", "")
    all_l = memory.all_learnings
    assert len(all_l) == 2
    # Verify it's a copy (modifying it doesn't affect internal state)
    all_l.clear()
    assert memory.count == 2


def test_get_relevant(memory):
    memory.save_learning("python", "Use list comprehensions", "", "")
    memory.save_learning("javascript", "Use arrow functions", "", "")
    memory.save_learning("python", "Virtual envs are important", "", "")
    results = memory.get_relevant("python")
    assert len(results) >= 2
    categories = [r["category"] for r in results]
    assert "python" in categories


def test_get_summary(memory):
    memory.save_learning("test", "Important insight", "", "")
    summary = memory.get_summary()
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_get_summary_empty(memory):
    summary = memory.get_summary()
    assert isinstance(summary, str)


def test_persistence(tmp_path):
    path = str(tmp_path / "learn.json")
    m1 = Memory(path=path)
    m1.save_learning("cat", "data", "ctx", "task")

    m2 = Memory(path=path)
    assert m2.count == 1
    assert m2.all_learnings[0]["insight"] == "data"
