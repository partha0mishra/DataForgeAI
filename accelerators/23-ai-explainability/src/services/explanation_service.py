"""Service for generating model explanations using SHAP, LIME, and Alibi."""

from typing import Dict, List, Optional, Any, Union
import numpy as np
import pandas as pd
from datetime import datetime
import time
import logging

from sqlalchemy.orm import Session

from src.repositories.explanation_repository import ExplanationRepository
from src.models.explanation import Explanation

# Try to import explanation libraries
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

try:
    from lime import lime_tabular
    LIME_AVAILABLE = True
except ImportError:
    LIME_AVAILABLE = False

try:
    import alibi
    from alibi.explainers import AnchorTabular, CounterfactualProto
    ALIBI_AVAILABLE = True
except ImportError:
    ALIBI_AVAILABLE = False

logger = logging.getLogger(__name__)


class ExplanationService:
    """Service for generating and managing model explanations."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.explanation_repo = ExplanationRepository(db)

    def generate_shap_explanation(
        self,
        model: Any,
        instance: Optional[np.ndarray] = None,
        background_data: Optional[np.ndarray] = None,
        feature_names: Optional[List[str]] = None,
        model_id: Optional[str] = None,
        model_name: Optional[str] = None,
        num_features: int = 10,
        created_by: Optional[str] = None
    ) -> Explanation:
        """
        Generate SHAP explanation for a model.

        Args:
            model: The ML model to explain
            instance: Single instance for local explanation (optional)
            background_data: Background dataset for SHAP explainer
            feature_names: Names of features
            model_id: Model identifier
            model_name: Model name
            num_features: Number of top features to include
            created_by: User who requested explanation

        Returns:
            Explanation object with SHAP values
        """
        if not SHAP_AVAILABLE:
            raise ValueError("SHAP library is not available. Install with: pip install shap")

        start_time = time.time()
        scope = 'local' if instance is not None else 'global'

        try:
            # Create SHAP explainer
            if background_data is not None:
                explainer = shap.Explainer(model, background_data)
            else:
                explainer = shap.Explainer(model)

            if instance is not None:
                # Local explanation
                shap_values = explainer(instance)

                # Get feature importances
                if hasattr(shap_values, 'values'):
                    values = shap_values.values
                    if len(values.shape) > 1:
                        values = values[0]  # First instance
                else:
                    values = shap_values

                feature_importances = {}
                if feature_names:
                    for idx, name in enumerate(feature_names[:len(values)]):
                        feature_importances[name] = float(values[idx])
                else:
                    for idx, val in enumerate(values):
                        feature_importances[f'feature_{idx}'] = float(val)

                # Get prediction
                prediction = model.predict(instance.reshape(1, -1))[0] if hasattr(model, 'predict') else None
                confidence = None
                if hasattr(model, 'predict_proba'):
                    proba = model.predict_proba(instance.reshape(1, -1))[0]
                    confidence = float(max(proba))

                base_value = explainer.expected_value if hasattr(explainer, 'expected_value') else 0.0

            else:
                # Global explanation
                if background_data is not None:
                    shap_values = explainer(background_data[:100])  # Limit for performance

                    # Aggregate feature importances
                    if hasattr(shap_values, 'values'):
                        values = shap_values.values
                    else:
                        values = shap_values

                    # Calculate mean absolute SHAP values
                    mean_abs_shap = np.abs(values).mean(axis=0)

                    feature_importances = {}
                    if feature_names:
                        for idx, name in enumerate(feature_names[:len(mean_abs_shap)]):
                            feature_importances[name] = float(mean_abs_shap[idx])
                    else:
                        for idx, val in enumerate(mean_abs_shap):
                            feature_importances[f'feature_{idx}'] = float(val)
                else:
                    raise ValueError("Background data required for global SHAP explanation")

                prediction = None
                confidence = None
                base_value = 0.0

            # Sort features by importance
            sorted_features = dict(
                sorted(feature_importances.items(), key=lambda x: abs(x[1]), reverse=True)[:num_features]
            )

            # Generate explanation text
            explanation_text = self._generate_shap_text(sorted_features, scope)

            generation_time = (time.time() - start_time) * 1000

            # Create explanation record
            explanation_data = {
                'model_id': model_id or 'unknown',
                'model_name': model_name,
                'explanation_type': 'shap',
                'scope': scope,
                'feature_importances': sorted_features,
                'prediction': prediction.tolist() if isinstance(prediction, np.ndarray) else prediction,
                'confidence': confidence,
                'base_value': float(base_value) if isinstance(base_value, (int, float, np.number)) else 0.0,
                'instance_data': instance.tolist() if instance is not None else None,
                'explanation_text': explanation_text,
                'generation_time_ms': generation_time,
                'num_features': num_features,
                'created_by': created_by
            }

            return self.explanation_repo.create(explanation_data)

        except Exception as e:
            logger.error(f"Error generating SHAP explanation: {str(e)}")
            raise

    def generate_lime_explanation(
        self,
        model: Any,
        instance: np.ndarray,
        training_data: np.ndarray,
        feature_names: Optional[List[str]] = None,
        model_id: Optional[str] = None,
        model_name: Optional[str] = None,
        num_features: int = 10,
        created_by: Optional[str] = None
    ) -> Explanation:
        """
        Generate LIME explanation for a single instance.

        Args:
            model: The ML model to explain
            instance: Single instance to explain
            training_data: Training data for LIME
            feature_names: Names of features
            model_id: Model identifier
            model_name: Model name
            num_features: Number of features to include
            created_by: User who requested explanation

        Returns:
            Explanation object with LIME values
        """
        if not LIME_AVAILABLE:
            raise ValueError("LIME library is not available. Install with: pip install lime")

        start_time = time.time()

        try:
            # Create LIME explainer
            explainer = lime_tabular.LimeTabularExplainer(
                training_data,
                feature_names=feature_names,
                mode='classification' if hasattr(model, 'predict_proba') else 'regression'
            )

            # Generate explanation
            if hasattr(model, 'predict_proba'):
                exp = explainer.explain_instance(
                    instance,
                    model.predict_proba,
                    num_features=num_features
                )
            else:
                exp = explainer.explain_instance(
                    instance,
                    model.predict,
                    num_features=num_features
                )

            # Extract feature importances
            feature_importances = {}
            for feature_idx, importance in exp.as_list():
                if feature_names and isinstance(feature_idx, int):
                    feature_name = feature_names[feature_idx]
                else:
                    feature_name = str(feature_idx).split('<=')[0].split('>')[0].strip()
                feature_importances[feature_name] = float(importance)

            # Get prediction
            prediction = model.predict(instance.reshape(1, -1))[0] if hasattr(model, 'predict') else None
            confidence = None
            if hasattr(model, 'predict_proba'):
                proba = model.predict_proba(instance.reshape(1, -1))[0]
                confidence = float(max(proba))

            # Generate explanation text
            explanation_text = self._generate_lime_text(feature_importances)

            generation_time = (time.time() - start_time) * 1000

            # Create explanation record
            explanation_data = {
                'model_id': model_id or 'unknown',
                'model_name': model_name,
                'explanation_type': 'lime',
                'scope': 'local',
                'feature_importances': feature_importances,
                'prediction': prediction.tolist() if isinstance(prediction, np.ndarray) else prediction,
                'confidence': confidence,
                'base_value': None,
                'instance_data': instance.tolist(),
                'explanation_text': explanation_text,
                'generation_time_ms': generation_time,
                'num_features': num_features,
                'created_by': created_by
            }

            return self.explanation_repo.create(explanation_data)

        except Exception as e:
            logger.error(f"Error generating LIME explanation: {str(e)}")
            raise

    def generate_feature_importance_explanation(
        self,
        model: Any,
        feature_names: List[str],
        model_id: Optional[str] = None,
        model_name: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Explanation:
        """
        Generate explanation from model's built-in feature importances.

        Works for tree-based models (Random Forest, XGBoost, etc.)

        Args:
            model: Model with feature_importances_ attribute
            feature_names: Names of features
            model_id: Model identifier
            model_name: Model name
            created_by: User who requested explanation

        Returns:
            Explanation object
        """
        start_time = time.time()

        try:
            if not hasattr(model, 'feature_importances_'):
                raise ValueError("Model does not have feature_importances_ attribute")

            importances = model.feature_importances_
            feature_importances = {
                name: float(imp)
                for name, imp in zip(feature_names, importances)
            }

            # Sort by importance
            sorted_features = dict(
                sorted(feature_importances.items(), key=lambda x: x[1], reverse=True)
            )

            explanation_text = self._generate_feature_importance_text(sorted_features)

            generation_time = (time.time() - start_time) * 1000

            explanation_data = {
                'model_id': model_id or 'unknown',
                'model_name': model_name,
                'explanation_type': 'feature_importance',
                'scope': 'global',
                'feature_importances': sorted_features,
                'explanation_text': explanation_text,
                'generation_time_ms': generation_time,
                'num_features': len(feature_names),
                'created_by': created_by
            }

            return self.explanation_repo.create(explanation_data)

        except Exception as e:
            logger.error(f"Error generating feature importance explanation: {str(e)}")
            raise

    def _generate_shap_text(self, features: Dict[str, float], scope: str) -> str:
        """Generate human-readable explanation from SHAP values."""
        if scope == 'global':
            text = "Model-level SHAP analysis shows the following key features:\\n\\n"
        else:
            text = "Instance-level SHAP analysis for this prediction:\\n\\n"

        sorted_features = sorted(features.items(), key=lambda x: abs(x[1]), reverse=True)

        for feature, value in sorted_features[:5]:
            direction = "increases" if value > 0 else "decreases"
            text += f"- {feature}: {direction} prediction (SHAP value: {value:.4f})\\n"

        return text

    def _generate_lime_text(self, features: Dict[str, float]) -> str:
        """Generate human-readable explanation from LIME values."""
        text = "LIME local explanation for this instance:\\n\\n"

        sorted_features = sorted(features.items(), key=lambda x: abs(x[1]), reverse=True)

        for feature, value in sorted_features[:5]:
            direction = "supports" if value > 0 else "opposes"
            text += f"- {feature}: {direction} the prediction (weight: {value:.4f})\\n"

        return text

    def _generate_feature_importance_text(self, features: Dict[str, float]) -> str:
        """Generate human-readable explanation from feature importances."""
        text = "Model feature importances (globally across all predictions):\\n\\n"

        sorted_features = sorted(features.items(), key=lambda x: x[1], reverse=True)

        for feature, value in sorted_features[:5]:
            text += f"- {feature}: {value:.4f} importance\\n"

        return text

    def get_explanation_by_id(self, explanation_id: str) -> Optional[Explanation]:
        """Get explanation by ID."""
        return self.explanation_repo.get_by_id(explanation_id)

    def get_model_explanations(
        self,
        model_id: str,
        explanation_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Explanation]:
        """Get all explanations for a model."""
        return self.explanation_repo.get_by_model_id(model_id, explanation_type, limit)

    def get_top_features(
        self,
        model_id: str,
        explanation_type: str = 'shap',
        top_n: int = 10
    ) -> Dict[str, float]:
        """Get aggregated top features for a model."""
        return self.explanation_repo.get_top_features_by_model(model_id, explanation_type, top_n)

    def get_explanation_stats(
        self,
        model_id: Optional[str] = None,
        hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get explanation statistics."""
        return self.explanation_repo.get_explanation_stats(model_id, hours)

    def delete_explanation(self, explanation_id: str) -> bool:
        """Delete an explanation."""
        return self.explanation_repo.delete(explanation_id)
