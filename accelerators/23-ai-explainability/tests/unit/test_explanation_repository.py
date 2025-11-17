"""Unit tests for ExplanationRepository."""

import pytest
from datetime import datetime, timedelta

from src.repositories.explanation_repository import ExplanationRepository


class TestExplanationRepository:
    """Test cases for ExplanationRepository."""

    def test_create_explanation(self, test_db):
        """Test creating an explanation."""
        repo = ExplanationRepository(test_db)

        explanation_data = {
            'model_id': 'test-model',
            'model_name': 'Test Model',
            'explanation_type': 'shap',
            'scope': 'global',
            'feature_importances': {'age': 0.5, 'income': 0.3},
            'explanation_text': 'Test explanation',
            'num_features': 2,
            'created_by': 'test_user'
        }

        explanation = repo.create(explanation_data)

        assert explanation.explanation_id is not None
        assert explanation.model_id == 'test-model'
        assert explanation.explanation_type == 'shap'
        assert explanation.scope == 'global'

    def test_get_by_id(self, test_db, sample_explanation):
        """Test getting explanation by ID."""
        repo = ExplanationRepository(test_db)

        explanation = repo.get_by_id(sample_explanation.explanation_id)

        assert explanation is not None
        assert explanation.explanation_id == sample_explanation.explanation_id
        assert explanation.model_id == sample_explanation.model_id

    def test_get_by_id_not_found(self, test_db):
        """Test getting non-existent explanation."""
        repo = ExplanationRepository(test_db)

        explanation = repo.get_by_id('non-existent-id')

        assert explanation is None

    def test_get_by_model_id(self, test_db, sample_explanation):
        """Test getting explanations for a model."""
        repo = ExplanationRepository(test_db)

        explanations = repo.get_by_model_id('test-model-1')

        assert len(explanations) == 1
        assert explanations[0].model_id == 'test-model-1'

    def test_get_by_model_id_with_type_filter(self, test_db, sample_explanation):
        """Test getting explanations filtered by type."""
        repo = ExplanationRepository(test_db)

        # Add another explanation with different type
        lime_exp_data = {
            'model_id': 'test-model-1',
            'explanation_type': 'lime',
            'scope': 'local',
            'feature_importances': {'age': 0.4},
            'num_features': 1
        }
        repo.create(lime_exp_data)

        shap_explanations = repo.get_by_model_id('test-model-1', explanation_type='shap')
        lime_explanations = repo.get_by_model_id('test-model-1', explanation_type='lime')

        assert len(shap_explanations) == 1
        assert len(lime_explanations) == 1
        assert shap_explanations[0].explanation_type == 'shap'
        assert lime_explanations[0].explanation_type == 'lime'

    def test_get_global_explanations(self, test_db, sample_explanation):
        """Test getting global explanations."""
        repo = ExplanationRepository(test_db)

        # Add local explanation
        local_exp_data = {
            'model_id': 'test-model-2',
            'explanation_type': 'shap',
            'scope': 'local',
            'feature_importances': {'age': 0.3},
            'num_features': 1
        }
        repo.create(local_exp_data)

        global_explanations = repo.get_global_explanations()

        assert len(global_explanations) == 1
        assert global_explanations[0].scope == 'global'

    def test_get_explanation_stats(self, test_db, sample_explanation):
        """Test getting explanation statistics."""
        repo = ExplanationRepository(test_db)

        # Add more explanations
        for i in range(3):
            repo.create({
                'model_id': f'model-{i}',
                'explanation_type': 'lime',
                'scope': 'local',
                'feature_importances': {'f1': 0.5},
                'num_features': 1
            })

        stats = repo.get_explanation_stats()

        assert stats['total_explanations'] == 4
        assert 'shap' in stats['by_type']
        assert 'lime' in stats['by_type']
        assert stats['by_type']['lime'] == 3
        assert stats['unique_models'] >= 1

    def test_delete_explanation(self, test_db, sample_explanation):
        """Test deleting an explanation."""
        repo = ExplanationRepository(test_db)

        result = repo.delete(sample_explanation.explanation_id)

        assert result is True

        # Verify deletion
        deleted = repo.get_by_id(sample_explanation.explanation_id)
        assert deleted is None

    def test_delete_nonexistent(self, test_db):
        """Test deleting non-existent explanation."""
        repo = ExplanationRepository(test_db)

        result = repo.delete('non-existent-id')

        assert result is False

    def test_update_explanation(self, test_db, sample_explanation):
        """Test updating an explanation."""
        repo = ExplanationRepository(test_db)

        updates = {
            'explanation_text': 'Updated explanation text',
            'num_features': 5
        }

        updated = repo.update(sample_explanation.explanation_id, updates)

        assert updated is not None
        assert updated.explanation_text == 'Updated explanation text'
        assert updated.num_features == 5
