"""Tests for shell tools."""

from jarvis.tools.shell import run_shell, run_python, _is_dangerous


def test_dangerous_rm_rf():
    assert _is_dangerous("rm -rf /") is not None


def test_dangerous_shutdown():
    assert _is_dangerous("shutdown -h now") is not None


def test_dangerous_fork_bomb():
    assert _is_dangerous(":(){ :|:& };:") is not None


def test_dangerous_format():
    assert _is_dangerous("format c:") is not None


def test_safe_command():
    assert _is_dangerous("echo hello") is None
    assert _is_dangerous("ls -la") is None
    assert _is_dangerous("python --version") is None


def test_run_shell():
    result = run_shell("echo hello")
    assert "hello" in result


def test_run_shell_blocked():
    result = run_shell("rm -rf /")
    assert "blocked" in result.lower()


def test_run_shell_timeout():
    # Very short timeout
    result = run_shell("python -c \"import time; time.sleep(10)\"", timeout=1)
    assert "timed out" in result.lower()


def test_run_python():
    result = run_python("print(2 + 2)")
    assert "4" in result


def test_run_python_error():
    result = run_python("raise ValueError('boom')")
    assert "ValueError" in result or "boom" in result
