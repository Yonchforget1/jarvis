import os
from dataclasses import dataclass

import yaml
from dotenv import load_dotenv


@dataclass
class Config:
    backend: str = "claude"
    model: str = "claude-sonnet-4-5-20250929"
    api_key_env: str = "ANTHROPIC_API_KEY"
    max_tokens: int = 4096
    system_prompt: str = "You are Jarvis, a helpful AI assistant."
    api_key: str = ""
    tool_timeout: int = 30  # Default timeout for tool execution in seconds
    max_tool_turns: int = 25  # Max tool calls per conversation turn

    @classmethod
    def load(cls, config_path: str = "config.yaml") -> "Config":
        load_dotenv()
        data = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                data = yaml.safe_load(f) or {}
        config = cls(
            backend=data.get("backend", cls.backend),
            model=data.get("model", cls.model),
            api_key_env=data.get("api_key_env", cls.api_key_env),
            max_tokens=data.get("max_tokens", cls.max_tokens),
            system_prompt=data.get("system_prompt", cls.system_prompt),
            tool_timeout=data.get("tool_timeout", cls.tool_timeout),
            max_tool_turns=data.get("max_tool_turns", cls.max_tool_turns),
        )
        config.api_key = os.getenv(config.api_key_env, "")
        if not config.api_key:
            raise ValueError(
                f"API key not found. Set {config.api_key_env} in your .env file."
            )
        return config
