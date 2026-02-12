"""Configuration management for Jarvis."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _ROOT / "config.yaml"


@dataclass
class Config:
    backend: str = "claude_code"
    model: str = ""
    max_tokens: int = 4096
    system_prompt: str = "You are Jarvis, an advanced AI agent."
    api_key: str = ""
    api_key_env: str = ""
    tool_timeout: int = 120
    max_tool_turns: int = 25

    @classmethod
    def load(cls) -> Config:
        load_dotenv(_ROOT / ".env")
        data: dict = {}
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH) as f:
                data = yaml.safe_load(f) or {}

        config = cls(
            backend=data.get("backend", cls.backend),
            model=data.get("model", cls.model),
            max_tokens=data.get("max_tokens", cls.max_tokens),
            system_prompt=data.get("system_prompt", cls.system_prompt),
            api_key_env=data.get("api_key_env", cls.api_key_env),
            tool_timeout=data.get("tool_timeout", cls.tool_timeout),
            max_tool_turns=data.get("max_tool_turns", cls.max_tool_turns),
        )

        # claude_code backend needs no API key
        if config.backend == "claude_code":
            config.api_key = ""
        else:
            # Auto-detect env var name from backend if not explicitly set
            if not config.api_key_env:
                env_map = {
                    "anthropic": "ANTHROPIC_API_KEY",
                    "openai": "OPENAI_API_KEY",
                    "gemini": "GOOGLE_API_KEY",
                }
                config.api_key_env = env_map.get(config.backend, "")

            if config.api_key_env:
                config.api_key = os.getenv(config.api_key_env, "")
                if not config.api_key:
                    raise ValueError(
                        f"API key not found in env var {config.api_key_env!r}. "
                        f"Set it in .env or your environment."
                    )
        return config
