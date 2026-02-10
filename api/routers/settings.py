"""Settings endpoint: user preferences for backend, model, API keys, tools."""

import json
import logging
import os
import threading

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.crypto import decrypt, encrypt
from api.deps import get_current_user
from api.models import UserInfo
from jarvis.templates import list_templates

log = logging.getLogger("jarvis.api.settings")

router = APIRouter()

_session_manager = None

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SETTINGS_FILE = os.path.join(DATA_DIR, "user_settings.json")
_lock = threading.Lock()

# Available models per backend
AVAILABLE_MODELS = {
    "claude": [
        {"id": "claude-sonnet-4-5-20250929", "name": "Claude Sonnet 4.5", "description": "Fast and capable"},
        {"id": "claude-opus-4-6", "name": "Claude Opus 4.6", "description": "Most intelligent"},
        {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "description": "Fastest and cheapest"},
    ],
    "openai": [
        {"id": "gpt-4o", "name": "GPT-4o", "description": "Most capable OpenAI model"},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "description": "Fast and affordable"},
        {"id": "o1", "name": "o1", "description": "Reasoning model"},
    ],
    "gemini": [
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "description": "Most capable Gemini"},
        {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "description": "Fast and efficient"},
    ],
}

AVAILABLE_BACKENDS = [
    {"id": "claude", "name": "Claude (Anthropic)", "key_env": "ANTHROPIC_API_KEY"},
    {"id": "openai", "name": "OpenAI", "key_env": "OPENAI_API_KEY"},
    {"id": "gemini", "name": "Gemini (Google)", "key_env": "GOOGLE_API_KEY"},
]


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


def _load_all_settings() -> dict:
    with _lock:
        if not os.path.exists(SETTINGS_FILE):
            return {}
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)


def _save_all_settings(data: dict):
    with _lock:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def _get_user_settings(user_id: str) -> dict:
    all_settings = _load_all_settings()
    return all_settings.get(user_id, {})


def _set_user_settings(user_id: str, settings: dict):
    all_settings = _load_all_settings()
    all_settings[user_id] = settings
    _save_all_settings(all_settings)


# --- Request/Response models ---

class PreferencesUpdate(BaseModel):
    theme: str | None = None  # "light", "dark", "auto"
    language: str | None = None  # ISO 639-1 code
    notifications: bool | None = None
    default_session_name: str | None = None
    show_tool_calls: bool | None = None


class PreferencesResponse(BaseModel):
    theme: str
    language: str
    notifications: bool
    default_session_name: str
    show_tool_calls: bool


class SettingsUpdate(BaseModel):
    backend: str | None = None
    model: str | None = None
    api_key: str | None = None
    max_tokens: int | None = None
    disabled_tools: list[str] | None = None


class SettingsResponse(BaseModel):
    backend: str
    model: str
    has_api_key: bool
    max_tokens: int
    disabled_tools: list[str]


class ModelsResponse(BaseModel):
    backends: list[dict]
    models: dict[str, list[dict]]


# --- Routes ---

def _get_decrypted_api_key(user_settings: dict, fallback: str = "") -> str:
    """Decrypt stored API key. Handles both encrypted and legacy plain-text values."""
    stored = user_settings.get("api_key", "")
    if not stored:
        return fallback
    # Fernet tokens start with 'gAAAAA' - if it doesn't, it's a legacy plain-text key
    if stored.startswith("gAAAAA"):
        return decrypt(stored) or fallback
    return stored


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(user: UserInfo = Depends(get_current_user)):
    user_settings = _get_user_settings(user.id)
    config = _session_manager.config
    has_key = bool(_get_decrypted_api_key(user_settings, config.api_key))

    return SettingsResponse(
        backend=user_settings.get("backend", config.backend),
        model=user_settings.get("model", config.model),
        has_api_key=has_key,
        max_tokens=user_settings.get("max_tokens", config.max_tokens),
        disabled_tools=user_settings.get("disabled_tools", []),
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(
    update: SettingsUpdate,
    user: UserInfo = Depends(get_current_user),
):
    user_settings = _get_user_settings(user.id)
    config = _session_manager.config

    if update.backend is not None:
        if update.backend not in ("claude", "openai", "gemini"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid backend")
        user_settings["backend"] = update.backend

    if update.model is not None:
        # Validate model exists for the current backend
        current_backend = update.backend or user_settings.get("backend", config.backend)
        valid_models = [m["id"] for m in AVAILABLE_MODELS.get(current_backend, [])]
        if valid_models and update.model not in valid_models:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Invalid model '{update.model}' for backend '{current_backend}'",
            )
        user_settings["model"] = update.model

    if update.api_key is not None:
        user_settings["api_key"] = encrypt(update.api_key)

    if update.max_tokens is not None:
        if not (256 <= update.max_tokens <= 32768):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "max_tokens must be 256-32768")
        user_settings["max_tokens"] = update.max_tokens

    if update.disabled_tools is not None:
        user_settings["disabled_tools"] = update.disabled_tools

    _set_user_settings(user.id, user_settings)
    has_key = bool(_get_decrypted_api_key(user_settings, config.api_key))

    return SettingsResponse(
        backend=user_settings.get("backend", config.backend),
        model=user_settings.get("model", config.model),
        has_api_key=has_key,
        max_tokens=user_settings.get("max_tokens", config.max_tokens),
        disabled_tools=user_settings.get("disabled_tools", []),
    )


@router.get("/settings/models", response_model=ModelsResponse)
async def get_available_models(user: UserInfo = Depends(get_current_user)):
    return ModelsResponse(
        backends=AVAILABLE_BACKENDS,
        models=AVAILABLE_MODELS,
    )


_DEFAULT_PREFS = {
    "theme": "auto",
    "language": "en",
    "notifications": True,
    "default_session_name": "New Chat",
    "show_tool_calls": True,
}


@router.get("/settings/preferences", response_model=PreferencesResponse)
async def get_preferences(user: UserInfo = Depends(get_current_user)):
    """Get user UI preferences."""
    user_settings = _get_user_settings(user.id)
    prefs = user_settings.get("preferences", {})
    return PreferencesResponse(**{**_DEFAULT_PREFS, **prefs})


@router.put("/settings/preferences", response_model=PreferencesResponse)
async def update_preferences(
    update: PreferencesUpdate,
    user: UserInfo = Depends(get_current_user),
):
    """Update user UI preferences."""
    user_settings = _get_user_settings(user.id)
    prefs = user_settings.get("preferences", dict(_DEFAULT_PREFS))

    if update.theme is not None:
        if update.theme not in ("light", "dark", "auto"):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "theme must be light, dark, or auto")
        prefs["theme"] = update.theme
    if update.language is not None:
        if len(update.language) != 2:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "language must be 2-letter ISO 639-1 code")
        prefs["language"] = update.language
    if update.notifications is not None:
        prefs["notifications"] = update.notifications
    if update.default_session_name is not None:
        prefs["default_session_name"] = update.default_session_name[:50]
    if update.show_tool_calls is not None:
        prefs["show_tool_calls"] = update.show_tool_calls

    user_settings["preferences"] = prefs
    _set_user_settings(user.id, user_settings)
    return PreferencesResponse(**{**_DEFAULT_PREFS, **prefs})


@router.get("/settings/templates")
async def get_templates(user: UserInfo = Depends(get_current_user)):
    """Return available conversation templates."""
    return {"templates": list_templates()}
