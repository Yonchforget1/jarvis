"""WhatsApp integration: bridge endpoint for whatsapp-web.js + legacy Twilio webhook."""

import asyncio
import logging
import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

log = logging.getLogger("jarvis.whatsapp")

router = APIRouter()

_session_manager = None

# Per-phone-number session tracking (WhatsApp number -> Jarvis session_id)
_phone_sessions: dict[str, str] = {}


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


# ---------------------------------------------------------------------------
# Bridge endpoint (used by whatsapp_bridge.js — no auth required, localhost only)
# ---------------------------------------------------------------------------

class BridgeRequest(BaseModel):
    phone: str
    name: str = ""
    message: str
    session_id: str | None = None


class BridgeResponse(BaseModel):
    session_id: str
    response: str
    tool_calls: list = []


@router.post("/whatsapp/bridge", response_model=BridgeResponse)
async def whatsapp_bridge(body: BridgeRequest, request: Request):
    """Internal endpoint for the Node.js WhatsApp bridge.

    Receives a message from a WhatsApp user, processes it through Jarvis,
    and returns the response. No authentication — only accepts localhost.
    """
    if not _session_manager:
        raise HTTPException(503, "Service not initialized")

    # Security: only allow from localhost
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(403, "Bridge endpoint only accessible from localhost")

    phone = body.phone
    user_id = f"wa_{phone}"
    log.info("WhatsApp bridge from %s (%s): %s", body.name or phone, phone, body.message[:100])

    # Get or create session — prefer the one tracked server-side
    session_id = _phone_sessions.get(phone) or body.session_id
    session = _session_manager.get_or_create(session_id, user_id)
    _phone_sessions[phone] = session.session_id

    try:
        loop = asyncio.get_event_loop()
        response_text = await loop.run_in_executor(
            None, session.conversation.send, body.message
        )
    except Exception as e:
        log.error("WhatsApp bridge error for %s: %s", phone, e)
        response_text = "Sorry, I encountered an error processing your request."

    raw_calls = session.conversation.get_and_clear_tool_calls()
    log.info("WhatsApp bridge reply to %s: %s", phone, response_text[:100])

    return BridgeResponse(
        session_id=session.session_id,
        response=response_text,
        tool_calls=[{"name": tc["name"], "result": tc["result"][:200]} for tc in raw_calls],
    )


# ---------------------------------------------------------------------------
# OCR endpoint (used by whatsapp_bridge.js for image messages)
# ---------------------------------------------------------------------------

class OCRRequest(BaseModel):
    image_path: str


@router.post("/whatsapp/ocr")
async def whatsapp_ocr(body: OCRRequest, request: Request):
    """OCR an image file saved by the WhatsApp bridge. Localhost only."""
    client_host = request.client.host if request.client else ""
    if client_host not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(403, "OCR endpoint only accessible from localhost")

    if not os.path.isfile(body.image_path):
        raise HTTPException(400, f"Image not found: {body.image_path}")

    try:
        import pytesseract
        from PIL import Image
        tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(tesseract_path):
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
        img = Image.open(body.image_path)
        text = pytesseract.image_to_string(img).strip()
        log.info("OCR result for %s: %s", body.image_path, text[:100])
        return {"text": text, "chars": len(text)}
    except ImportError:
        return {"text": "(OCR not available — install pytesseract)", "chars": 0}
    except Exception as e:
        log.error("OCR error: %s", e)
        return {"text": f"(OCR error: {e})", "chars": 0}


# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------

@router.get("/whatsapp/status")
async def whatsapp_status():
    """Check WhatsApp integration status."""
    return {
        "mode": "bridge",
        "bridge_endpoint": "/api/whatsapp/bridge",
        "ocr_endpoint": "/api/whatsapp/ocr",
        "active_conversations": len(_phone_sessions),
        "sessions": {phone: sid for phone, sid in _phone_sessions.items()},
    }
