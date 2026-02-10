"""Tests for filesystem tools: read, write, delete, list, info."""

import os
import tempfile

import pytest

from jarvis.tools.filesystem import (
    read_file, write_file, list_directory, delete_path,
    move_copy, make_directory, file_info, _validate_path,
)


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def test_read_file(tmp_dir):
    path = os.path.join(tmp_dir, "test.txt")
    with open(path, "w") as f:
        f.write("hello world")
    result = read_file(path)
    assert "hello world" in result


def test_read_file_missing():
    result = read_file("/nonexistent/path/file.txt")
    assert "Error" in result


def test_write_file(tmp_dir):
    path = os.path.join(tmp_dir, "out.txt")
    result = write_file(path, "test content")
    assert "Successfully wrote" in result
    assert os.path.exists(path)
    with open(path) as f:
        assert f.read() == "test content"


def test_write_file_creates_dirs(tmp_dir):
    path = os.path.join(tmp_dir, "sub", "dir", "file.txt")
    result = write_file(path, "nested")
    assert "Successfully" in result
    assert os.path.exists(path)


def test_list_directory(tmp_dir):
    # Create test files
    open(os.path.join(tmp_dir, "a.txt"), "w").close()
    open(os.path.join(tmp_dir, "b.txt"), "w").close()
    os.makedirs(os.path.join(tmp_dir, "subdir"))

    result = list_directory(tmp_dir)
    assert "a.txt" in result
    assert "b.txt" in result
    assert "[DIR]" in result


def test_list_directory_glob(tmp_dir):
    open(os.path.join(tmp_dir, "a.py"), "w").close()
    open(os.path.join(tmp_dir, "b.txt"), "w").close()
    result = list_directory(os.path.join(tmp_dir, "*.py"))
    assert "a.py" in result
    assert "b.txt" not in result


def test_delete_file(tmp_dir):
    path = os.path.join(tmp_dir, "del.txt")
    open(path, "w").close()
    result = delete_path(path)
    assert "Deleted" in result
    assert not os.path.exists(path)


def test_delete_directory(tmp_dir):
    path = os.path.join(tmp_dir, "deldir")
    os.makedirs(path)
    open(os.path.join(path, "file.txt"), "w").close()
    result = delete_path(path)
    assert "Deleted" in result
    assert not os.path.exists(path)


def test_move_copy_file(tmp_dir):
    src = os.path.join(tmp_dir, "src.txt")
    dst = os.path.join(tmp_dir, "dst.txt")
    with open(src, "w") as f:
        f.write("content")
    result = move_copy(src, dst, "copy")
    assert "Copied" in result
    assert os.path.exists(src)
    assert os.path.exists(dst)


def test_make_directory(tmp_dir):
    path = os.path.join(tmp_dir, "new", "nested")
    result = make_directory(path)
    assert "Created" in result
    assert os.path.isdir(path)


def test_file_info(tmp_dir):
    path = os.path.join(tmp_dir, "info.txt")
    with open(path, "w") as f:
        f.write("12345")
    result = file_info(path)
    assert "file" in result
    assert "5 bytes" in result


def test_validate_path_blocks_env():
    err = _validate_path(".env", write=True)
    assert err is not None
    assert "sensitive" in err.lower() or "refusing" in err.lower()


def test_validate_path_blocks_git():
    err = _validate_path(".git", write=True)
    assert err is not None


def test_validate_path_allows_read():
    # Read paths should not be blocked
    err = _validate_path(".env", write=False)
    assert err is None


def test_validate_path_null_bytes():
    err = _validate_path("test\x00.txt", write=False)
    assert err is not None
    assert "null" in err.lower()
