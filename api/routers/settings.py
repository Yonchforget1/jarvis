"""Settings router – read and update configuration."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException, status

from api.deps import get_current_user
from api.models import SettingsResponse, SettingsUpdateRequest, UserInfo

router = APIRouter(prefix="/api/settings", tags=["settings"])

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.yaml"
_AVAILABLE_BACKENDS = ["claude_code", "anthropic", "openai", "gemini"]


@router.get("", response_model=SettingsResponse)
async def get_settings(user: UserInfo = Depends(get_current_user)):
    from api.main import session_mgr

    config = session_mgr.config
    return SettingsResponse(
        backend=config.backend,
        model=config.model,
        max_tokens=config.max_tokens,
        system_prompt=config.system_prompt,
        available_backends=_AVAILABLE_BACKENDS,
    )


@router.patch("")
async def update_settings(
    req: SettingsUpdateRequest,
    user: UserInfo = Depends(get_current_user),
):
    from api.main import session_mgr

    # Only admin can change settings
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change settings",
        )

    # Load current config file
    data: dict = {}
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            data = yaml.safe_load(f) or {}

    changed = []

    if req.backend is not None:
        if req.backend not in _AVAILABLE_BACKENDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown backend: {req.backend}. Available: {_AVAILABLE_BACKENDS}",
            )
        data["backend"] = req.backend
        session_mgr.config.backend = req.backend
        changed.append("backend")

    if req.model is not None:
        data["model"] = req.model
        session_mgr.config.model = req.model
        changed.append("model")

    if req.max_tokens is not None:
        if req.max_tokens < 256 or req.max_tokens > 200000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="max_tokens must be between 256 and 200000",
            )
        data["max_tokens"] = req.max_tokens
        session_mgr.config.max_tokens = req.max_tokens
        changed.append("max_tokens")

    if req.system_prompt is not None:
        data["system_prompt"] = req.system_prompt
        session_mgr.config.system_prompt = req.system_prompt
        changed.append("system_prompt")

    if req.api_key is not None:
        # Store API key in the env var for the current backend
        env_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "gemini": "GOOGLE_API_KEY",
        }
        backend = req.backend or session_mgr.config.backend
        env_var = env_map.get(backend)
        if env_var:
            os.environ[env_var] = req.api_key
            session_mgr.config.api_key = req.api_key
            changed.append("api_key")

    # Save config to disk (excluding api_key for security)
    _CONFIG_PATH.write_text(yaml.dump(data, default_flow_style=False))

    return {"status": "updated", "changed": changed}
