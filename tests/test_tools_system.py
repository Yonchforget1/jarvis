"""Tests for system utility tools."""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

from jarvis.tools.system import (
    system_info,
    get_env_var,
    list_env_vars,
    clipboard_read,
    clipboard_write,
)


def test_system_info():
    result = system_info()
    assert "Platform:" in result
    assert "Python:" in result
    assert "CPU Cores:" in result


def test_get_env_var_exists():
    with patch.dict(os.environ, {"TEST_VAR": "hello123"}):
        result = get_env_var("TEST_VAR")
        assert "hello123" in result


def test_get_env_var_not_set():
    result = get_env_var("DEFINITELY_NOT_SET_XYZ_123")
    assert "not set" in result


def test_get_env_var_sensitive_masked():
    with patch.dict(os.environ, {"MY_API_KEY": "sk-1234567890abcdef"}):
        result = get_env_var("MY_API_KEY")
        # Should mask middle portion
        assert "sk-1" in result
        assert "cdef" in result
        assert "1234567890abcdef" not in result


def test_get_env_var_short_sensitive():
    with patch.dict(os.environ, {"MY_SECRET": "short"}):
        result = get_env_var("MY_SECRET")
        assert "****" in result
        assert "short" not in result


def test_list_env_vars():
    result = list_env_vars()
    assert "variables:" in result
    assert "PATH" in result or "Path" in result


def test_list_env_vars_with_prefix():
    with patch.dict(os.environ, {"JARVIS_TEST_1": "a", "JARVIS_TEST_2": "b"}):
        result = list_env_vars("JARVIS_TEST")
        assert "JARVIS_TEST_1" in result
        assert "JARVIS_TEST_2" in result


def test_list_env_vars_no_match():
    result = list_env_vars("ZZZZZ_NONEXISTENT_PREFIX")
    assert "No environment variables found" in result


def test_clipboard_read_fallback():
    """Test clipboard read with powershell fallback when pyperclip missing."""
    import sys
    # Remove pyperclip from available modules to trigger ImportError fallback
    with patch.dict(sys.modules, {"pyperclip": None}):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="clipboard content\n")
            result = clipboard_read()
            assert "clipboard content" in result


def test_clipboard_write_fallback():
    """Test clipboard write with powershell fallback when pyperclip missing."""
    import sys
    with patch.dict(sys.modules, {"pyperclip": None}):
        with patch("subprocess.Popen") as mock_popen:
            proc = MagicMock()
            proc.communicate.return_value = ("", "")
            mock_popen.return_value = proc
            result = clipboard_write("test text")
            assert "9 characters" in result
