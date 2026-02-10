"""Tiered rate limiting: different limits for free, pro, and enterprise users.

Extends the base slowapi rate limiting with per-user tier awareness.
"""

import logging
import os

log = logging.getLogger("jarvis.rate_limits")

# Rate limit tiers (requests per minute)
TIER_LIMITS = {
    "free": {
        "chat": "10/minute",
        "chat_batch": "2/minute",
        "default": "30/minute",
    },
    "pro": {
        "chat": "60/minute",
        "chat_batch": "10/minute",
        "default": "120/minute",
    },
    "enterprise": {
        "chat": "200/minute",
        "chat_batch": "50/minute",
        "default": "500/minute",
    },
}

# Default tier for new users
DEFAULT_TIER = os.getenv("JARVIS_DEFAULT_TIER", "free")


def get_user_tier(user_id: str) -> str:
    """Get the rate limit tier for a user.

    In production, this would look up the user's subscription.
    For now, uses a simple JSON file or env var.
    """
    import json
    tiers_file = os.path.join(os.path.dirname(__file__), "data", "user_tiers.json")
    if os.path.exists(tiers_file):
        try:
            with open(tiers_file, "r") as f:
                tiers = json.load(f)
            return tiers.get(user_id, DEFAULT_TIER)
        except Exception:
            pass
    return DEFAULT_TIER


def get_rate_limit(user_id: str, endpoint: str = "default") -> str:
    """Get the rate limit string for a user and endpoint.

    Returns slowapi-compatible rate limit string like "60/minute".
    """
    tier = get_user_tier(user_id)
    limits = TIER_LIMITS.get(tier, TIER_LIMITS["free"])
    return limits.get(endpoint, limits["default"])


def set_user_tier(user_id: str, tier: str) -> bool:
    """Set a user's rate limit tier. Returns False if tier is invalid."""
    if tier not in TIER_LIMITS:
        return False

    import json
    tiers_file = os.path.join(os.path.dirname(__file__), "data", "user_tiers.json")
    os.makedirs(os.path.dirname(tiers_file), exist_ok=True)

    tiers = {}
    if os.path.exists(tiers_file):
        with open(tiers_file, "r") as f:
            tiers = json.load(f)

    tiers[user_id] = tier
    with open(tiers_file, "w") as f:
        json.dump(tiers, f, indent=2)

    log.info("Set user %s to tier %s", user_id, tier)
    return True


def get_tier_info() -> dict:
    """Get information about all available tiers."""
    return {
        tier: {
            "chat_per_minute": limits["chat"],
            "batch_per_minute": limits["chat_batch"],
            "default_per_minute": limits["default"],
        }
        for tier, limits in TIER_LIMITS.items()
    }
