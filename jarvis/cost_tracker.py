"""Cost tracking for AI API usage.

Estimates costs based on token usage and model pricing.
Supports budget limits per session.
"""

import logging
from dataclasses import dataclass, field

log = logging.getLogger("jarvis.cost")

# Pricing per 1M tokens (input, output) in USD
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # Claude
    "claude-sonnet-4-5-20250929": (3.0, 15.0),
    "claude-opus-4-6": (15.0, 75.0),
    "claude-haiku-4-5-20251001": (0.80, 4.0),
    # OpenAI
    "gpt-4o": (2.50, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
    "o1": (15.0, 60.0),
    # Gemini
    "gemini-2.5-pro": (1.25, 10.0),
    "gemini-2.0-flash": (0.075, 0.30),
    # Ollama (free, local)
    "llama3": (0.0, 0.0),
}

# Default pricing if model not found
DEFAULT_PRICING = (3.0, 15.0)


@dataclass
class CostTracker:
    """Tracks estimated API costs for a session."""

    model: str = ""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    budget_usd: float = 0.0  # 0 = no limit

    @property
    def input_price_per_m(self) -> float:
        return MODEL_PRICING.get(self.model, DEFAULT_PRICING)[0]

    @property
    def output_price_per_m(self) -> float:
        return MODEL_PRICING.get(self.model, DEFAULT_PRICING)[1]

    @property
    def estimated_cost_usd(self) -> float:
        """Calculate estimated cost in USD."""
        input_cost = (self.total_input_tokens / 1_000_000) * self.input_price_per_m
        output_cost = (self.total_output_tokens / 1_000_000) * self.output_price_per_m
        return input_cost + output_cost

    @property
    def budget_remaining_usd(self) -> float | None:
        """Returns remaining budget or None if no limit set."""
        if self.budget_usd <= 0:
            return None
        return max(0.0, self.budget_usd - self.estimated_cost_usd)

    @property
    def is_over_budget(self) -> bool:
        """Check if spending exceeds budget."""
        if self.budget_usd <= 0:
            return False
        return self.estimated_cost_usd >= self.budget_usd

    def record_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Record token usage from an API call."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        if self.is_over_budget:
            log.warning(
                "Budget exceeded: $%.4f spent of $%.2f budget",
                self.estimated_cost_usd, self.budget_usd,
            )

    def summary(self) -> dict:
        """Return a cost summary dict."""
        result = {
            "model": self.model,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
        }
        if self.budget_usd > 0:
            result["budget_usd"] = self.budget_usd
            result["budget_remaining_usd"] = round(self.budget_remaining_usd or 0, 6)
            result["over_budget"] = self.is_over_budget
        return result
