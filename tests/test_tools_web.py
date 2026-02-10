"""Tests for web tools: search, fetch, SSRF protection."""

import pytest

from jarvis.tools.web import _is_internal_url, fetch_url


class TestSSRFProtection:
    def test_blocks_localhost(self):
        assert _is_internal_url("http://localhost/admin") is True

    def test_blocks_127(self):
        assert _is_internal_url("http://127.0.0.1/secret") is True

    def test_blocks_private_10(self):
        assert _is_internal_url("http://10.0.0.1/internal") is True

    def test_blocks_private_192(self):
        assert _is_internal_url("http://192.168.1.1/router") is True

    def test_blocks_private_172(self):
        assert _is_internal_url("http://172.16.0.1/internal") is True

    def test_blocks_ipv6_loopback(self):
        assert _is_internal_url("http://[::1]/") is True

    def test_blocks_zero(self):
        assert _is_internal_url("http://0.0.0.0/") is True

    def test_allows_public_domain(self):
        assert _is_internal_url("https://example.com") is False

    def test_allows_public_ip(self):
        assert _is_internal_url("http://8.8.8.8/") is False

    def test_blocks_no_hostname(self):
        assert _is_internal_url("not-a-url") is True


class TestFetchUrl:
    def test_fetch_internal_blocked(self):
        result = fetch_url("http://localhost/secret")
        assert "SSRF" in result or "internal" in result.lower()

    def test_fetch_private_ip_blocked(self):
        result = fetch_url("http://10.0.0.1/admin")
        assert "SSRF" in result or "internal" in result.lower()
