"""Model serving for inference."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from dataforge_common.logging import get_logger
from dataforge_common.monitoring import increment_counter, track_duration

logger = get_logger(__name__)


@dataclass
class PredictionRequest:
    """Prediction request."""

    model_name: str
    model_version: Optional[str] = None
    model_stage: Optional[str] = None
    features: Dict[str, Any] = None
    instances: List[Dict[str, Any]] = None


@dataclass
class PredictionResponse:
    """Prediction response."""

    predictions: List[Any]
    model_name: str
    model_version: str
    prediction_count: int
    timestamp: str
    latency_ms: float


class ModelServer:
    """
    Model serving for real-time inference.

    Provides:
    - Model loading and caching
    - Batch prediction
    - Input validation
    - Prediction logging
    - Performance monitoring

    Example:
        server = ModelServer(registry=model_registry)

        # Load model
        server.load_model("customer_churn", stage="Production")

        # Predict
        response = server.predict(
            model_name="customer_churn",
            features={
                "age": 35,
                "tenure_months": 24,
                "monthly_charges": 79.99
            }
        )

        print(f"Prediction: {response.predictions[0]}")
    """

    def __init__(self, registry: Any, cache_size: int = 10):
        """
        Initialize model server.

        Args:
            registry: Model registry instance
            cache_size: Number of models to keep in cache
        """
        self.registry = registry
        self.cache_size = cache_size
        self.logger = logger

        # Model cache: {(name, version): model}
        self.model_cache: Dict[tuple, Any] = {}

        # Model metadata cache
        self.metadata_cache: Dict[tuple, Dict] = {}

        self.logger.info("Model server initialized", cache_size=cache_size)

    def load_model(
        self,
        name: str,
        version: Optional[str] = None,
        stage: Optional[str] = None,
    ) -> None:
        """
        Load model into cache.

        Args:
            name: Model name
            version: Specific version (optional)
            stage: Stage to load from (optional)
        """
        # Get model version info
        if version:
            model_version = self.registry.get_model_version(name, version)
        elif stage:
            versions = self.registry.client.get_latest_versions(name, stages=[stage])
            if not versions:
                raise ValueError(f"No model in stage {stage}")
            model_version = self.registry.get_model_version(name, versions[0].version)
        else:
            # Get latest version
            model = self.registry.list_models()
            matching = [m for m in model if m.name == name]
            if not matching:
                raise ValueError(f"Model not found: {name}")
            model_version = self.registry.get_model_version(name, matching[0].latest_version)

        cache_key = (name, model_version.version)

        # Check if already cached
        if cache_key in self.model_cache:
            self.logger.debug("Model already in cache", name=name, version=model_version.version)
            return

        # Load model
        model = self.registry.get_model(name, version=model_version.version)

        # Evict old models if cache full
        if len(self.model_cache) >= self.cache_size:
            oldest_key = list(self.model_cache.keys())[0]
            del self.model_cache[oldest_key]
            del self.metadata_cache[oldest_key]
            self.logger.debug("Evicted model from cache", model=oldest_key)

        # Add to cache
        self.model_cache[cache_key] = model
        self.metadata_cache[cache_key] = {
            "name": name,
            "version": model_version.version,
            "stage": model_version.stage.value,
            "loaded_at": datetime.utcnow(),
            "prediction_count": 0,
        }

        self.logger.info(
            "Model loaded",
            name=name,
            version=model_version.version,
            stage=model_version.stage.value,
        )

    @track_duration("prediction_duration_ms")
    def predict(
        self,
        model_name: str,
        features: Optional[Dict[str, Any]] = None,
        instances: Optional[List[Dict[str, Any]]] = None,
        model_version: Optional[str] = None,
        model_stage: Optional[str] = None,
    ) -> PredictionResponse:
        """
        Make predictions.

        Args:
            model_name: Model name
            features: Single instance features
            instances: Multiple instances
            model_version: Specific version
            model_stage: Specific stage

        Returns:
            Prediction response
        """
        import time

        start_time = time.time()

        # Determine which model to use
        cache_key = self._get_cache_key(model_name, model_version, model_stage)

        # Load model if not cached
        if cache_key not in self.model_cache:
            self.load_model(model_name, version=model_version, stage=model_stage)
            cache_key = self._get_cache_key(model_name, model_version, model_stage)

        model = self.model_cache[cache_key]
        metadata = self.metadata_cache[cache_key]

        # Prepare input
        if features:
            # Single instance
            input_data = pd.DataFrame([features])
        elif instances:
            # Multiple instances
            input_data = pd.DataFrame(instances)
        else:
            raise ValueError("Either 'features' or 'instances' must be provided")

        # Make predictions
        try:
            predictions = model.predict(input_data)

            # Convert to list
            if isinstance(predictions, np.ndarray):
                predictions = predictions.tolist()
            elif not isinstance(predictions, list):
                predictions = [predictions]

        except Exception as e:
            self.logger.error(
                "Prediction failed",
                model=model_name,
                error=str(e),
                exc_info=True,
            )
            raise

        # Update metadata
        metadata["prediction_count"] += len(predictions)
        metadata["last_prediction"] = datetime.utcnow()

        # Calculate latency
        latency_ms = (time.time() - start_time) * 1000

        # Increment counter
        increment_counter(
            "predictions_total",
            labels={
                "model_name": model_name,
                "model_version": metadata["version"],
            },
        )

        response = PredictionResponse(
            predictions=predictions,
            model_name=model_name,
            model_version=metadata["version"],
            prediction_count=len(predictions),
            timestamp=datetime.utcnow().isoformat(),
            latency_ms=latency_ms,
        )

        self.logger.info(
            "Prediction complete",
            model=model_name,
            version=metadata["version"],
            count=len(predictions),
            latency_ms=latency_ms,
        )

        return response

    def predict_proba(
        self,
        model_name: str,
        features: Optional[Dict[str, Any]] = None,
        instances: Optional[List[Dict[str, Any]]] = None,
        model_version: Optional[str] = None,
        model_stage: Optional[str] = None,
    ) -> PredictionResponse:
        """
        Make probability predictions (for classifiers).

        Args:
            model_name: Model name
            features: Single instance features
            instances: Multiple instances
            model_version: Specific version
            model_stage: Specific stage

        Returns:
            Prediction response with probabilities
        """
        # Get model from cache
        cache_key = self._get_cache_key(model_name, model_version, model_stage)

        if cache_key not in self.model_cache:
            self.load_model(model_name, version=model_version, stage=model_stage)
            cache_key = self._get_cache_key(model_name, model_version, model_stage)

        model = self.model_cache[cache_key]
        metadata = self.metadata_cache[cache_key]

        # Prepare input
        if features:
            input_data = pd.DataFrame([features])
        elif instances:
            input_data = pd.DataFrame(instances)
        else:
            raise ValueError("Either 'features' or 'instances' must be provided")

        # Get underlying sklearn model
        if hasattr(model, "_model_impl"):
            sklearn_model = model._model_impl
        else:
            sklearn_model = model

        # Check if model supports predict_proba
        if not hasattr(sklearn_model, "predict_proba"):
            raise ValueError(f"Model {model_name} does not support probability predictions")

        # Make predictions
        probabilities = sklearn_model.predict_proba(input_data)

        # Convert to list of lists
        predictions = probabilities.tolist()

        response = PredictionResponse(
            predictions=predictions,
            model_name=model_name,
            model_version=metadata["version"],
            prediction_count=len(predictions),
            timestamp=datetime.utcnow().isoformat(),
            latency_ms=0.0,  # TODO: track latency
        )

        return response

    def _get_cache_key(
        self,
        name: str,
        version: Optional[str] = None,
        stage: Optional[str] = None,
    ) -> tuple:
        """Get cache key for model."""
        # Try to find in cache
        for (cached_name, cached_version), metadata in self.metadata_cache.items():
            if cached_name != name:
                continue

            if version and cached_version == version:
                return (cached_name, cached_version)

            if stage and metadata["stage"] == stage:
                return (cached_name, cached_version)

        # If not in cache and no specific version/stage, return with "unknown"
        # This will trigger a load
        return (name, version or "unknown")

    def unload_model(self, name: str, version: str) -> None:
        """
        Unload model from cache.

        Args:
            name: Model name
            version: Model version
        """
        cache_key = (name, version)

        if cache_key in self.model_cache:
            del self.model_cache[cache_key]
            del self.metadata_cache[cache_key]

            self.logger.info("Model unloaded", name=name, version=version)

    def get_loaded_models(self) -> List[Dict[str, Any]]:
        """Get list of loaded models."""
        return [
            {
                "name": metadata["name"],
                "version": metadata["version"],
                "stage": metadata["stage"],
                "loaded_at": metadata["loaded_at"].isoformat(),
                "prediction_count": metadata["prediction_count"],
            }
            for metadata in self.metadata_cache.values()
        ]

    def get_server_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        total_predictions = sum(
            m["prediction_count"] for m in self.metadata_cache.values()
        )

        return {
            "loaded_models": len(self.model_cache),
            "cache_size": self.cache_size,
            "total_predictions": total_predictions,
            "models": self.get_loaded_models(),
        }
