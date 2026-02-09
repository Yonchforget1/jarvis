"""Encrypted secrets management for API keys and sensitive configuration.

Uses Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256).
The master key is derived from JARVIS_MASTER_KEY env var or auto-generated.
"""

import base64
import hashlib
import json
import logging
import os
import threading

log = logging.getLogger("jarvis.secrets")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api", "data")
SECRETS_FILE = os.path.join(DATA_DIR, "secrets.enc")
KEY_FILE = os.path.join(DATA_DIR, ".master_key")
_lock = threading.Lock()


def _get_master_key() -> bytes:
    """Get or generate the master encryption key.

    Uses JARVIS_MASTER_KEY env var if set, otherwise generates and stores
    a key in .master_key file (which should be in .gitignore).
    """
    env_key = os.getenv("JARVIS_MASTER_KEY", "")
    if env_key:
        # Derive a 32-byte key from the env var
        return base64.urlsafe_b64encode(hashlib.sha256(env_key.encode()).digest())

    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            return f.read()

    # Generate new key
    try:
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
    except ImportError:
        # Fallback: generate a key manually
        key = base64.urlsafe_b64encode(os.urandom(32))

    with open(KEY_FILE, "wb") as f:
        f.write(key)
    log.info("Generated new master encryption key")
    return key


def _encrypt(plaintext: str) -> str:
    """Encrypt a string value."""
    try:
        from cryptography.fernet import Fernet
        f = Fernet(_get_master_key())
        return f.encrypt(plaintext.encode()).decode()
    except ImportError:
        # Fallback: base64 encoding (not truly secure, warns user)
        log.warning("cryptography package not installed; secrets stored with base64 only")
        return "b64:" + base64.b64encode(plaintext.encode()).decode()


def _decrypt(ciphertext: str) -> str:
    """Decrypt a string value."""
    if ciphertext.startswith("b64:"):
        return base64.b64decode(ciphertext[4:]).decode()
    try:
        from cryptography.fernet import Fernet
        f = Fernet(_get_master_key())
        return f.decrypt(ciphertext.encode()).decode()
    except ImportError:
        log.error("Cannot decrypt: cryptography package not installed")
        return ""
    except Exception as e:
        log.error("Decryption failed: %s", e)
        return ""


def _load_store() -> dict:
    with _lock:
        if not os.path.exists(SECRETS_FILE):
            return {}
        with open(SECRETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)


def _save_store(store: dict):
    with _lock:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SECRETS_FILE, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2, ensure_ascii=False)


def set_secret(user_id: str, key: str, value: str) -> None:
    """Store an encrypted secret for a user."""
    store = _load_store()
    user_secrets = store.setdefault(user_id, {})
    user_secrets[key] = _encrypt(value)
    _save_store(store)
    log.info("Secret '%s' stored for user %s", key, user_id)


def get_secret(user_id: str, key: str) -> str | None:
    """Retrieve a decrypted secret for a user."""
    store = _load_store()
    user_secrets = store.get(user_id, {})
    encrypted = user_secrets.get(key)
    if encrypted is None:
        return None
    return _decrypt(encrypted)


def delete_secret(user_id: str, key: str) -> bool:
    """Delete a secret. Returns True if it existed."""
    store = _load_store()
    user_secrets = store.get(user_id, {})
    if key not in user_secrets:
        return False
    del user_secrets[key]
    store[user_id] = user_secrets
    _save_store(store)
    log.info("Secret '%s' deleted for user %s", key, user_id)
    return True


def list_secrets(user_id: str) -> list[str]:
    """List secret keys for a user (values are not returned)."""
    store = _load_store()
    return list(store.get(user_id, {}).keys())
