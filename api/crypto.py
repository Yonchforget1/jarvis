"""Simple symmetric encryption for sensitive data at rest (API keys, tokens).

Uses Fernet (AES-128-CBC + HMAC-SHA256) derived from JWT_SECRET.
"""

import base64
import hashlib
import logging
import os

from cryptography.fernet import Fernet, InvalidToken

log = logging.getLogger("jarvis.api.crypto")

_ENCRYPTION_KEY = os.getenv("JWT_SECRET", "jarvis-dev-secret-change-in-production")

# Derive a 32-byte key from JWT_SECRET using SHA-256, then base64-encode for Fernet
_derived = hashlib.sha256(_ENCRYPTION_KEY.encode()).digest()
_fernet = Fernet(base64.urlsafe_b64encode(_derived))


def encrypt(plaintext: str) -> str:
    """Encrypt a string and return a base64 token."""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a Fernet token back to plaintext. Returns empty string on failure."""
    try:
        return _fernet.decrypt(token.encode()).decode()
    except (InvalidToken, Exception):
        log.warning("Failed to decrypt value (key may have changed)")
        return ""
