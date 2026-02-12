"""Email tool – send emails via SMTP."""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from jarvis.tool_registry import ToolDef, ToolRegistry

log = logging.getLogger("jarvis.tools.email")


def send_email(
    to: str,
    subject: str,
    body: str,
    html: bool = False,
    cc: str = "",
    bcc: str = "",
) -> str:
    """Send an email via SMTP.

    Requires SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM env vars.
    """
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    smtp_from = os.environ.get("SMTP_FROM", smtp_user or "")

    if not all([smtp_host, smtp_user, smtp_pass]):
        return "Error: SMTP not configured. Set SMTP_HOST, SMTP_USER, SMTP_PASS environment variables."

    # Validate recipient
    if not to or "@" not in to:
        return f"Error: invalid recipient address '{to}'"

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = smtp_from
        msg["To"] = to
        msg["Subject"] = subject

        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc

        content_type = "html" if html else "plain"
        msg.attach(MIMEText(body, content_type, "utf-8"))

        # Build full recipient list
        recipients = [addr.strip() for addr in to.split(",")]
        if cc:
            recipients.extend(addr.strip() for addr in cc.split(","))
        if bcc:
            recipients.extend(addr.strip() for addr in bcc.split(","))

        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, recipients, msg.as_string())

        log.info("Email sent to %s: %s", to, subject)
        return f"Email sent successfully to {to}"

    except smtplib.SMTPAuthenticationError:
        return "Error: SMTP authentication failed. Check SMTP_USER and SMTP_PASS."
    except smtplib.SMTPException as e:
        return f"SMTP error: {e}"
    except Exception as e:
        return f"Error sending email: {e}"


def register(registry: ToolRegistry) -> None:
    registry.register(ToolDef(
        name="send_email",
        description="Send an email via SMTP (requires SMTP env vars configured)",
        parameters={
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address(es), comma-separated"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body text"},
                "html": {"type": "boolean", "description": "Send as HTML (default: plain text)"},
                "cc": {"type": "string", "description": "CC recipients, comma-separated"},
                "bcc": {"type": "string", "description": "BCC recipients, comma-separated"},
            },
            "required": ["to", "subject", "body"],
        },
        func=send_email,
    ))
