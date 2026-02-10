"""Token pricing for different AI backends and models."""

# Pricing per 1M tokens (USD)
PRICING: dict[str, dict[str, dict[str, float]]] = {
    "claude": {
        "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
        "claude-opus-4-6": {"input": 15.0, "output": 75.0},
        "claude-haiku-4-5-20251001": {"input": 0.8, "output": 4.0},
    },
    "openai": {
        "gpt-4o": {"input": 2.5, "output": 10.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "o1": {"input": 15.0, "output": 60.0},
        "o3-mini": {"input": 1.10, "output": 4.40},
    },
    "gemini": {
        "gemini-2.5-pro": {"input": 1.25, "output": 10.0},
        "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    },
    "ollama": {},  # Local models have no API cost
}

# Default fallback (Claude Sonnet pricing)
_DEFAULT_PRICING = {"input": 3.0, "output": 15.0}


def get_cost_estimate(backend: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate estimated cost in USD for token usage."""
    backend_models = PRICING.get(backend, {})
    pricing = backend_models.get(model, _DEFAULT_PRICING)
    if not pricing:
        return 0.0
    return (input_tokens * pricing["input"] / 1_000_000) + (output_tokens * pricing["output"] / 1_000_000)
