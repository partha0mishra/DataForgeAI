"""A/B testing framework for model evaluation."""

import secrets
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

from dataforge_common.logging import get_logger
from dataforge_common.tracing import trace_method

logger = get_logger(__name__)


class ExperimentStatus(str, Enum):
    """Experiment status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ABTestingManager:
    """Manages A/B testing experiments."""

    def __init__(self):
        """Initialize A/B testing manager."""
        self.experiments: Dict[str, Dict[str, Any]] = {}
        logger.info("ABTestingManager initialized")

    @trace_method()
    async def create_experiment(
        self,
        name: str,
        model_a: str,
        model_b: str,
        traffic_split: Dict[str, int],
        success_metric: str,
        duration_days: int
    ) -> Dict[str, Any]:
        """Create A/B test experiment."""
        experiment_id = f"exp_{secrets.token_hex(8)}"

        experiment = {
            "experiment_id": experiment_id,
            "name": name,
            "model_a": model_a,
            "model_b": model_b,
            "traffic_split": traffic_split,
            "success_metric": success_metric,
            "duration_days": duration_days,
            "status": ExperimentStatus.ACTIVE,
            "created_at": datetime.utcnow(),
            "end_date": datetime.utcnow() + timedelta(days=duration_days),
            "results": None
        }

        self.experiments[experiment_id] = experiment
        logger.info(f"A/B test experiment {experiment_id} created: {name}")

        return experiment

    @trace_method()
    async def get_results(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Get experiment results."""
        experiment = self.experiments.get(experiment_id)
        if not experiment:
            return None

        # Simulate results calculation
        results = {
            "experiment_id": experiment_id,
            "status": experiment["status"],
            "model_a_metrics": {
                "requests": 5000,
                "accuracy": 0.92,
                "latency_ms": 50.5
            },
            "model_b_metrics": {
                "requests": 5000,
                "accuracy": 0.94,
                "latency_ms": 48.2
            },
            "winner": "model_b",
            "confidence": 0.95,
            "statistical_significance": True
        }

        return results

    @trace_method()
    async def promote_winner(self, experiment_id: str) -> Dict[str, Any]:
        """Promote winning model."""
        results = await self.get_results(experiment_id)
        if not results:
            raise ValueError(f"Experiment not found: {experiment_id}")

        experiment = self.experiments[experiment_id]
        experiment["status"] = ExperimentStatus.COMPLETED

        winner_model = experiment[results["winner"]]

        logger.info(f"Promoting winner from experiment {experiment_id}: {winner_model}")

        return {
            "experiment_id": experiment_id,
            "winner": results["winner"],
            "promoted_model": winner_model,
            "timestamp": datetime.utcnow().isoformat()
        }
