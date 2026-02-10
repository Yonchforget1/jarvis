"""White-label configuration: custom branding, domain, colors.

Allows resellers to rebrand the Jarvis platform with their own
identity. Configuration is loaded from a white_label.yaml file
or environment variables.
"""

import logging
import os
from dataclasses import dataclass, field

import yaml

log = logging.getLogger("jarvis.white_label")

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "white_label.yaml")


@dataclass
class WhiteLabelConfig:
    """White-label branding configuration."""

    # Branding
    product_name: str = "Jarvis AI Agent"
    company_name: str = "Jarvis"
    tagline: str = "AI Agent Platform"
    logo_url: str = ""
    favicon_url: str = ""

    # Colors (CSS custom properties)
    primary_color: str = "#38bdf8"
    secondary_color: str = "#1e293b"
    accent_color: str = "#22c55e"
    background_color: str = "#0f172a"
    text_color: str = "#e2e8f0"

    # Domain
    custom_domain: str = ""
    api_base_url: str = ""

    # Features
    show_powered_by: bool = True
    custom_footer_html: str = ""
    custom_css: str = ""

    # Email
    support_email: str = ""
    from_email: str = ""

    @classmethod
    def load(cls) -> "WhiteLabelConfig":
        """Load white-label config from file or environment."""
        data = {}

        # Load from YAML if exists
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = yaml.safe_load(f) or {}
                log.info("Loaded white-label config from %s", CONFIG_FILE)
            except Exception as e:
                log.warning("Failed to load white-label config: %s", e)

        # Environment overrides (JARVIS_WL_ prefix)
        env_map = {
            "JARVIS_WL_PRODUCT_NAME": "product_name",
            "JARVIS_WL_COMPANY_NAME": "company_name",
            "JARVIS_WL_TAGLINE": "tagline",
            "JARVIS_WL_LOGO_URL": "logo_url",
            "JARVIS_WL_PRIMARY_COLOR": "primary_color",
            "JARVIS_WL_CUSTOM_DOMAIN": "custom_domain",
            "JARVIS_WL_API_BASE_URL": "api_base_url",
            "JARVIS_WL_SUPPORT_EMAIL": "support_email",
        }
        for env_var, field_name in env_map.items():
            value = os.getenv(env_var)
            if value:
                data[field_name] = value

        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_css_vars(self) -> str:
        """Generate CSS custom properties for theming."""
        return f""":root {{
    --wl-primary: {self.primary_color};
    --wl-secondary: {self.secondary_color};
    --wl-accent: {self.accent_color};
    --wl-bg: {self.background_color};
    --wl-text: {self.text_color};
}}"""

    def to_dict(self) -> dict:
        """Export config as dict (safe for API responses)."""
        return {
            "product_name": self.product_name,
            "company_name": self.company_name,
            "tagline": self.tagline,
            "logo_url": self.logo_url,
            "favicon_url": self.favicon_url,
            "primary_color": self.primary_color,
            "secondary_color": self.secondary_color,
            "accent_color": self.accent_color,
            "show_powered_by": self.show_powered_by,
            "custom_domain": self.custom_domain,
            "support_email": self.support_email,
        }
