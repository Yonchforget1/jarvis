"""Tests for web tools - focusing on SSRF protection."""

from jarvis.tools.web import _is_private_url


def test_block_localhost():
    assert _is_private_url("http://localhost/secret") is True
    assert _is_private_url("http://127.0.0.1/admin") is True


def test_block_private_10():
    assert _is_private_url("http://10.0.0.1/") is True


def test_block_private_172():
    assert _is_private_url("http://172.16.0.1/") is True


def test_block_private_192():
    assert _is_private_url("http://192.168.1.1/") is True


def test_allow_public():
    # These should NOT be blocked (they're public IPs)
    assert _is_private_url("http://8.8.8.8/") is False


def test_block_empty_host():
    assert _is_private_url("http:///path") is True
