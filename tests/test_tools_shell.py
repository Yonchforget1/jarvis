"""Tests for shell tools: run_python, run_shell, command safety."""

import sys

import pytest

from jarvis.tools.shell import run_python, run_shell, _check_dangerous


def test_run_python_basic():
    result = run_python("print('hello')")
    assert "hello" in result


def test_run_python_error():
    result = run_python("raise ValueError('boom')")
    assert "boom" in result


def test_run_python_timeout():
    result = run_python("import time; time.sleep(60)")
    assert "timed out" in result.lower()


def test_run_shell_echo():
    if sys.platform == "win32":
        result = run_shell("echo hello")
    else:
        result = run_shell("echo hello")
    assert "hello" in result


def test_run_shell_exit_code():
    if sys.platform == "win32":
        result = run_shell("cmd /c exit 1")
    else:
        result = run_shell("false")
    assert "exit code" in result.lower() or "(no output)" in result


def test_check_dangerous_rm_rf():
    assert _check_dangerous("rm -rf /") is not None


def test_check_dangerous_shutdown():
    assert _check_dangerous("shutdown -h now") is not None


def test_check_dangerous_safe_command():
    assert _check_dangerous("ls -la") is None
    assert _check_dangerous("git status") is None
    assert _check_dangerous("pip install requests") is None
