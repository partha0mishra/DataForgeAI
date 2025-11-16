"""MLOps Automation Accelerator."""

__version__ = "1.0.0"

from .model_deployment import ModelDeploymentManager
from .drift_detection import DriftDetectionManager
from .retraining import RetrainingManager
from .ab_testing import ABTestingManager
from .model_registry import ModelRegistryClient

__all__ = [
    "ModelDeploymentManager",
    "DriftDetectionManager",
    "RetrainingManager",
    "ABTestingManager",
    "ModelRegistryClient"
]
