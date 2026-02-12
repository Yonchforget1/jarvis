"""Tests for email tool."""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

from jarvis.tools.email_tool import send_email


def test_send_email_no_config():
    """Should fail gracefully when SMTP is not configured."""
    with patch.dict(os.environ, {}, clear=True):
        result = send_email("user@example.com", "Test", "Hello")
        assert "not configured" in result.lower()


def test_send_email_invalid_recipient():
    with patch.dict(os.environ, {
        "SMTP_HOST": "smtp.test.com",
        "SMTP_USER": "user@test.com",
        "SMTP_PASS": "pass",
    }):
        result = send_email("invalid-email", "Test", "Hello")
        assert "invalid" in result.lower()


def test_send_email_success():
    with patch.dict(os.environ, {
        "SMTP_HOST": "smtp.test.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "sender@test.com",
        "SMTP_PASS": "password123",
        "SMTP_FROM": "sender@test.com",
    }):
        with patch("jarvis.tools.email_tool.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            result = send_email("recipient@test.com", "Hello", "Test body")
            assert "sent successfully" in result
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("sender@test.com", "password123")
            mock_server.sendmail.assert_called_once()


def test_send_email_html():
    with patch.dict(os.environ, {
        "SMTP_HOST": "smtp.test.com",
        "SMTP_USER": "user@test.com",
        "SMTP_PASS": "pass",
    }):
        with patch("jarvis.tools.email_tool.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            result = send_email(
                "user@test.com",
                "HTML Test",
                "<h1>Hello</h1>",
                html=True,
            )
            assert "sent successfully" in result


def test_send_email_auth_failure():
    import smtplib
    with patch.dict(os.environ, {
        "SMTP_HOST": "smtp.test.com",
        "SMTP_USER": "user@test.com",
        "SMTP_PASS": "wrong",
    }):
        with patch("jarvis.tools.email_tool.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Auth failed")
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

            result = send_email("user@test.com", "Test", "body")
            assert "authentication failed" in result.lower()
