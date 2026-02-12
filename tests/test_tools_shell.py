"""Tests for shell tools."""

from jarvis.tools.shell import run_shell, run_python, run_javascript, run_code, _is_dangerous


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


def test_run_javascript():
    result = run_javascript("console.log(3 * 7)")
    # Node might not be installed; that's OK
    assert "21" in result or "not found" in result.lower()


def test_run_code_python():
    result = run_code("python", "print('hello from run_code')")
    assert "hello from run_code" in result


def test_run_code_shell():
    result = run_code("shell", "echo test123")
    assert "test123" in result


def test_run_code_shell_blocked():
    result = run_code("shell", "rm -rf /")
    assert "blocked" in result.lower()


def test_run_code_unsupported():
    result = run_code("brainfuck", "++++++++++")
    assert "Unsupported" in result
