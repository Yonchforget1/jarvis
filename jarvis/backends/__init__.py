from .base import Backend, BackendResponse, ToolCall


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
    else:
        raise ValueError(f"Unknown backend: {name}")
