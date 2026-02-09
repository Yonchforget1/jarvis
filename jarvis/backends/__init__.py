from .base import Backend, BackendResponse, ToolCall

__all__ = ["Backend", "BackendResponse", "ToolCall", "create_backend"]


def create_backend(config) -> Backend:
    """Factory: create the right backend from config."""
    name = config.backend
    if name == "claude":
        from .claude import ClaudeBackend

        return ClaudeBackend(api_key=config.api_key, model=config.model)
    elif name == "openai":
        from .openai_backend import OpenAIBackend

        return OpenAIBackend(api_key=config.api_key, model=config.model)
    elif name == "gemini":
        from .gemini import GeminiBackend

        return GeminiBackend(api_key=config.api_key, model=config.model)
    elif name == "ollama":
        from .ollama_backend import OllamaBackend

        base_url = getattr(config, "ollama_base_url", "http://localhost:11434")
        return OllamaBackend(model=config.model, base_url=base_url)
    else:
        raise ValueError(f"Unknown backend: {name}")
