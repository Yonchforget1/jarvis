"""A/B testing framework for prompts and models.

Allows defining experiments that route a percentage of traffic to
different variants, collecting metrics for comparison.
"""

import json
import logging
import os
import random
import threading
import time
from dataclasses import dataclass, field, asdict

log = logging.getLogger("jarvis.ab_testing")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api", "data")
EXPERIMENTS_FILE = os.path.join(DATA_DIR, "ab_experiments.json")
_lock = threading.Lock()


@dataclass
class Variant:
    """A single variant in an A/B test."""

    name: str
    weight: float = 0.5  # Traffic percentage (0.0-1.0)
    config: dict = field(default_factory=dict)  # Model, system prompt, etc.
    impressions: int = 0
    successes: int = 0  # Positive outcomes
    total_latency_ms: float = 0.0
    total_tokens: int = 0

    @property
    def success_rate(self) -> float:
        return self.successes / self.impressions if self.impressions else 0.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.impressions if self.impressions else 0.0

    @property
    def avg_tokens(self) -> float:
        return self.total_tokens / self.impressions if self.impressions else 0.0


@dataclass
class Experiment:
    """An A/B test experiment."""

    id: str
    name: str
    description: str = ""
    variants: list[Variant] = field(default_factory=list)
    active: bool = True
    created_at: float = field(default_factory=time.time)

    def select_variant(self) -> Variant | None:
        """Select a variant based on weights."""
        if not self.variants or not self.active:
            return None
        r = random.random()
        cumulative = 0.0
        for variant in self.variants:
            cumulative += variant.weight
            if r <= cumulative:
                return variant
        return self.variants[-1]


class ABTestManager:
    """Manages A/B testing experiments."""

    def __init__(self):
        self._experiments: dict[str, Experiment] = {}
        self._load()

    def _load(self) -> None:
        with _lock:
            if not os.path.exists(EXPERIMENTS_FILE):
                return
            try:
                with open(EXPERIMENTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for exp_data in data:
                    variants = [Variant(**v) for v in exp_data.pop("variants", [])]
                    exp = Experiment(**exp_data, variants=variants)
                    self._experiments[exp.id] = exp
            except Exception as e:
                log.error("Failed to load experiments: %s", e)

    def _save(self) -> None:
        with _lock:
            os.makedirs(DATA_DIR, exist_ok=True)
            data = []
            for exp in self._experiments.values():
                d = asdict(exp)
                data.append(d)
            with open(EXPERIMENTS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    def create_experiment(
        self,
        name: str,
        variants: list[dict],
        description: str = "",
    ) -> Experiment:
        """Create a new experiment.

        Args:
            name: Experiment name.
            variants: List of variant dicts with 'name', 'weight', and 'config'.
            description: Optional description.
        """
        exp_id = f"exp_{int(time.time())}_{len(self._experiments)}"
        variant_objs = [
            Variant(name=v["name"], weight=v.get("weight", 0.5), config=v.get("config", {}))
            for v in variants
        ]
        exp = Experiment(id=exp_id, name=name, description=description, variants=variant_objs)
        self._experiments[exp_id] = exp
        self._save()
        log.info("Created experiment '%s' with %d variants", name, len(variant_objs))
        return exp

    def get_variant(self, experiment_id: str) -> tuple[str, dict] | None:
        """Get a variant assignment for an experiment.

        Returns (variant_name, config) or None if experiment not found/inactive.
        """
        exp = self._experiments.get(experiment_id)
        if not exp or not exp.active:
            return None
        variant = exp.select_variant()
        if not variant:
            return None
        variant.impressions += 1
        self._save()
        return variant.name, variant.config

    def record_outcome(
        self,
        experiment_id: str,
        variant_name: str,
        success: bool = True,
        latency_ms: float = 0.0,
        tokens: int = 0,
    ) -> None:
        """Record the outcome of a variant assignment."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return
        for variant in exp.variants:
            if variant.name == variant_name:
                if success:
                    variant.successes += 1
                variant.total_latency_ms += latency_ms
                variant.total_tokens += tokens
                self._save()
                return

    def get_results(self, experiment_id: str) -> dict | None:
        """Get results for an experiment."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        return {
            "id": exp.id,
            "name": exp.name,
            "active": exp.active,
            "variants": [
                {
                    "name": v.name,
                    "weight": v.weight,
                    "impressions": v.impressions,
                    "success_rate": round(v.success_rate, 4),
                    "avg_latency_ms": round(v.avg_latency_ms, 1),
                    "avg_tokens": round(v.avg_tokens, 1),
                }
                for v in exp.variants
            ],
        }

    def list_experiments(self) -> list[dict]:
        """List all experiments."""
        return [
            {
                "id": e.id,
                "name": e.name,
                "active": e.active,
                "variant_count": len(e.variants),
                "total_impressions": sum(v.impressions for v in e.variants),
            }
            for e in self._experiments.values()
        ]

    def toggle_experiment(self, experiment_id: str) -> bool | None:
        """Toggle an experiment's active state."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        exp.active = not exp.active
        self._save()
        return exp.active
