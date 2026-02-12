"""Tests for filesystem tools."""

import pytest
from pathlib import Path
from jarvis.tools.filesystem import (
    read_file, write_file, delete_path, move_copy,
    list_directory, file_info, file_search, make_directory,
    _is_blocked,
)


def test_blocked_paths():
    assert _is_blocked(".env") is True
    assert _is_blocked(".git/config") is True
    assert _is_blocked("safe/path.txt") is False


def test_read_file(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello world")
    assert read_file(str(f)) == "hello world"


def test_read_file_not_exists():
    result = read_file("/nonexistent/file.txt")
    assert "does not exist" in result


def test_read_file_max_lines(tmp_path):
    f = tmp_path / "big.txt"
    f.write_text("\n".join(f"line {i}" for i in range(1000)))
    result = read_file(str(f), max_lines=10)
    assert "more lines" in result


def test_write_file(tmp_path):
    f = tmp_path / "out.txt"
    result = write_file(str(f), "content")
    assert "Wrote" in result
    assert f.read_text() == "content"


def test_write_file_creates_parents(tmp_path):
    f = tmp_path / "a" / "b" / "c.txt"
    write_file(str(f), "deep")
    assert f.read_text() == "deep"


def test_write_file_blocked():
    result = write_file(".env", "secret")
    assert "blocked" in result.lower()


def test_delete_file(tmp_path):
    f = tmp_path / "del.txt"
    f.write_text("bye")
    result = delete_path(str(f))
    assert "Deleted" in result
    assert not f.exists()


def test_delete_dir(tmp_path):
    d = tmp_path / "mydir"
    d.mkdir()
    (d / "file.txt").write_text("x")
    result = delete_path(str(d))
    assert "Deleted" in result


def test_delete_blocked():
    result = delete_path(".git")
    assert "blocked" in result.lower()


def test_move_copy(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("data")
    dst = tmp_path / "dst.txt"
    result = move_copy(str(src), str(dst), "copy")
    assert "Copied" in result
    assert dst.read_text() == "data"
    assert src.exists()  # original still exists for copy


def test_move(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("data")
    dst = tmp_path / "moved.txt"
    result = move_copy(str(src), str(dst), "move")
    assert "Moved" in result
    assert not src.exists()
    assert dst.exists()


def test_list_directory(tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "subdir").mkdir()
    result = list_directory(str(tmp_path))
    assert "a.txt" in result
    assert "subdir" in result
    assert "[DIR]" in result
    assert "[FILE]" in result


def test_list_directory_not_exists():
    result = list_directory("/nonexistent")
    assert "does not exist" in result


def test_file_info(tmp_path):
    f = tmp_path / "info.txt"
    f.write_text("hello")
    result = file_info(str(f))
    assert "file" in result.lower()
    assert "Size:" in result


def test_file_search(tmp_path):
    (tmp_path / "a.py").write_text("")
    (tmp_path / "b.txt").write_text("")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.py").write_text("")
    result = file_search(str(tmp_path), "*.py")
    assert "a.py" in result
    assert "c.py" in result
    assert "b.txt" not in result


def test_make_directory(tmp_path):
    d = tmp_path / "new" / "nested"
    result = make_directory(str(d))
    assert "Created" in result
    assert d.is_dir()
