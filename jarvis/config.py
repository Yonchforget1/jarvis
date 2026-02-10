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
    ollama_base_url: str = "http://localhost:11434"

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
            ollama_base_url=data.get("ollama_base_url", cls.ollama_base_url),
        )
        # Ollama runs locally -- no API key required
        if config.backend == "ollama":
            config.api_key = ""
        else:
            config.api_key = os.getenv(config.api_key_env, "")
            if not config.api_key:
                raise ValueError(
                    f"API key not found. Set {config.api_key_env} in your .env file."
                )
        config._validate()
        return config

    def _validate(self):
        """Validate config values are within acceptable ranges."""
        if self.max_tokens < 1:
            raise ValueError(f"max_tokens must be >= 1, got {self.max_tokens}")
        if self.max_tokens > 200_000:
            raise ValueError(f"max_tokens must be <= 200000, got {self.max_tokens}")
        if self.tool_timeout < 1:
            raise ValueError(f"tool_timeout must be >= 1, got {self.tool_timeout}")
        if self.max_tool_turns < 1:
            raise ValueError(f"max_tool_turns must be >= 1, got {self.max_tool_turns}")
        valid_backends = ("claude", "openai", "gemini", "ollama")
        if self.backend not in valid_backends:
            raise ValueError(f"backend must be one of {valid_backends}, got '{self.backend}'")
