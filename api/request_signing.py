"""Request signing/HMAC verification for sensitive operations.

Clients can sign requests by including:
- X-Jarvis-Timestamp: Unix timestamp (must be within 5 minutes)
- X-Jarvis-Signature: HMAC-SHA256(secret, method+path+timestamp+body)

This provides an additional layer of security beyond JWT/API key auth.
"""

import hashlib
import hmac
import logging
import os
import time

from fastapi import HTTPException, Request, status

log = logging.getLogger("jarvis.signing")

SIGNING_SECRET = os.getenv("JARVIS_SIGNING_SECRET", "")
MAX_TIMESTAMP_DRIFT_SECONDS = 300  # 5 minutes


async def verify_request_signature(request: Request) -> None:
    """Verify HMAC signature on a request.

    Only enforced when JARVIS_SIGNING_SECRET is configured.
    Raises HTTPException if signature is missing or invalid.
    """
    if not SIGNING_SECRET:
        return  # Signing not configured, skip verification

    timestamp = request.headers.get("X-Jarvis-Timestamp", "")
    signature = request.headers.get("X-Jarvis-Signature", "")

    if not timestamp or not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Jarvis-Timestamp or X-Jarvis-Signature headers",
        )

    # Check timestamp freshness
    try:
        ts = float(timestamp)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Jarvis-Timestamp",
        )

    drift = abs(time.time() - ts)
    if drift > MAX_TIMESTAMP_DRIFT_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Request timestamp too old ({drift:.0f}s drift, max {MAX_TIMESTAMP_DRIFT_SECONDS}s)",
        )

    # Reconstruct signing string
    body = b""
    if request.method in ("POST", "PUT", "PATCH"):
        body = await request.body()

    signing_string = f"{request.method}{request.url.path}{timestamp}".encode() + body
    expected = hmac.new(SIGNING_SECRET.encode(), signing_string, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature, expected):
        log.warning("Invalid request signature for %s %s", request.method, request.url.path)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid request signature",
        )


def sign_request(method: str, path: str, body: bytes = b"") -> dict:
    """Helper for clients to sign a request. Returns headers dict.

    Usage from Python:
        headers = sign_request("POST", "/api/chat", json.dumps(payload).encode())
        requests.post(url, headers=headers, json=payload)
    """
    if not SIGNING_SECRET:
        return {}
    timestamp = str(int(time.time()))
    signing_string = f"{method}{path}{timestamp}".encode() + body
    signature = hmac.new(SIGNING_SECRET.encode(), signing_string, hashlib.sha256).hexdigest()
    return {
        "X-Jarvis-Timestamp": timestamp,
        "X-Jarvis-Signature": signature,
    }
