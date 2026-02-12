"""Tests for HTTP tools."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from jarvis.tools.http_tools import http_get, http_post, http_request


def _mock_response(status_code=200, text="OK", headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.reason_phrase = "OK"
    resp.text = text
    resp.headers = headers or {"content-type": "text/plain"}
    return resp


@pytest.fixture
def mock_httpx():
    """Mock httpx module so http_request can import it."""
    mock_mod = MagicMock()
    client = MagicMock()
    client.__enter__ = MagicMock(return_value=client)
    client.__exit__ = MagicMock(return_value=False)
    mock_mod.Client.return_value = client
    with patch.dict(sys.modules, {"httpx": mock_mod}):
        yield client


def test_http_get(mock_httpx):
    mock_httpx.request.return_value = _mock_response(text='{"msg":"hi"}')
    result = http_get("https://example.com/api")
    assert "HTTP 200" in result
    assert "hi" in result


def test_http_post(mock_httpx):
    mock_httpx.request.return_value = _mock_response(text='{"id":1}')
    result = http_post("https://example.com/api", body='{"name":"test"}')
    assert "HTTP 200" in result
    assert "id" in result


def test_http_request_put(mock_httpx):
    mock_httpx.request.return_value = _mock_response(text="updated")
    result = http_request("PUT", "https://example.com/api/1", body='{"x":1}')
    assert "HTTP 200" in result


def test_http_request_invalid_method():
    result = http_request("INVALID", "https://example.com")
    assert "unsupported method" in result.lower()


def test_http_request_private_url():
    result = http_request("GET", "http://127.0.0.1/admin")
    assert "SSRF" in result or "blocked" in result.lower()


def test_http_request_private_url_localhost():
    result = http_request("GET", "http://localhost:8080/secret")
    assert "SSRF" in result or "blocked" in result.lower()


def test_http_request_truncates_long_response(mock_httpx):
    long_text = "x" * 15000
    mock_httpx.request.return_value = _mock_response(text=long_text)
    result = http_request("GET", "https://example.com/big")
    assert "truncated" in result


def test_http_request_json_pretty_print(mock_httpx):
    mock_httpx.request.return_value = _mock_response(text='{"a":1,"b":2}')
    result = http_request("GET", "https://example.com/json")
    assert '"a": 1' in result


def test_http_request_connection_error(mock_httpx):
    mock_httpx.request.side_effect = Exception("Connection refused")
    result = http_request("GET", "https://example.com/down")
    assert "error" in result.lower()
