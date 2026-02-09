"""Twilio WhatsApp webhook: receive messages, process with Jarvis, reply."""

import asyncio
import hashlib
import hmac
import logging
import os
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Request, Response

log = logging.getLogger("jarvis.whatsapp")

router = APIRouter()

_session_manager = None

# Per-phone-number session tracking (WhatsApp number -> Jarvis session_id)
_phone_sessions: dict[str, str] = {}


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


def _verify_twilio_signature(request: Request, body: bytes) -> bool:
    """Verify the X-Twilio-Signature header to ensure the request is from Twilio.

    Returns True if verification passes or if TWILIO_AUTH_TOKEN is not set
    (development mode).
    """
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    if not auth_token:
        log.warning("TWILIO_AUTH_TOKEN not set -- skipping signature verification")
        return True

    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        return False

    # Reconstruct the full URL Twilio used to call us
    url = str(request.url)

    # Parse form params and sort them
    from urllib.parse import parse_qs
    params = parse_qs(body.decode("utf-8"), keep_blank_values=True)
    sorted_params = sorted(params.items())
    param_string = url + "".join(f"{k}{v[0]}" for k, v in sorted_params)

    # HMAC-SHA1
    computed = hmac.new(
        auth_token.encode("utf-8"),
        param_string.encode("utf-8"),
        hashlib.sha1,
    ).digest()

    import base64
    expected = base64.b64encode(computed).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def _twiml_reply(message: str) -> str:
    """Build a minimal TwiML response to send a WhatsApp reply."""
    # Escape XML special characters
    safe = (
        message
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        f"<Message>{safe}</Message>"
        "</Response>"
    )


@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(""),
    Body: str = Form(""),
    To: str = Form(""),
    MessageSid: str = Form(""),
    NumMedia: str = Form("0"),
):
    """Twilio WhatsApp incoming message webhook.

    Twilio sends POST with form-encoded data. We process the message
    through Jarvis and reply with TwiML.
    """
    if not _session_manager:
        raise HTTPException(503, "Service not initialized")

    if not From or not Body:
        log.warning("WhatsApp webhook called with missing From/Body")
        return Response(
            content=_twiml_reply("Sorry, I couldn't process that message."),
            media_type="application/xml",
        )

    # Use phone number as a stable user ID
    phone = From.replace("whatsapp:", "")
    user_id = f"wa_{phone}"
    log.info("WhatsApp from %s: %s", phone, Body[:100])

    # Get or create a session for this phone number
    session_id = _phone_sessions.get(phone)
    session = _session_manager.get_or_create(session_id, user_id)
    _phone_sessions[phone] = session.session_id

    # Process message through Jarvis
    try:
        loop = asyncio.get_event_loop()
        response_text = await loop.run_in_executor(
            None, session.conversation.send, Body
        )
    except Exception as e:
        log.error("WhatsApp processing error for %s: %s", phone, e)
        response_text = "Sorry, I encountered an error processing your request. Please try again."

    # Twilio WhatsApp has a 1600 character limit per message
    if len(response_text) > 1500:
        response_text = response_text[:1500] + "..."

    log.info("WhatsApp reply to %s: %s", phone, response_text[:100])

    return Response(
        content=_twiml_reply(response_text),
        media_type="application/xml",
    )


@router.get("/whatsapp/status")
async def whatsapp_status():
    """Check WhatsApp integration status."""
    auth_token_set = bool(os.getenv("TWILIO_AUTH_TOKEN", ""))
    account_sid_set = bool(os.getenv("TWILIO_ACCOUNT_SID", ""))
    whatsapp_from = os.getenv("TWILIO_WHATSAPP_FROM", "")

    return {
        "enabled": auth_token_set and account_sid_set,
        "auth_token_set": auth_token_set,
        "account_sid_set": account_sid_set,
        "whatsapp_from": whatsapp_from or "not configured",
        "active_conversations": len(_phone_sessions),
    }
