"""Initial schema for MLOps

Revision ID: 001
Revises:
Create Date: 2025-01-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ml_models table
    op.create_table(
        'ml_models',
        sa.Column('model_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('framework', sa.String(length=50), nullable=False),
        sa.Column('algorithm', sa.String(length=100), nullable=True),
        sa.Column('mlflow_run_id', sa.String(length=100), nullable=True),
        sa.Column('mlflow_model_uri', sa.String(length=500), nullable=True),
        sa.Column('mlflow_experiment_id', sa.String(length=100), nullable=True),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('parameters', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('accuracy', sa.Float(), nullable=True),
        sa.Column('precision', sa.Float(), nullable=True),
        sa.Column('recall', sa.Float(), nullable=True),
        sa.Column('f1_score', sa.Float(), nullable=True),
        sa.Column('auc_roc', sa.Float(), nullable=True),
        sa.Column('custom_metrics', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='registered'),
        sa.Column('is_production', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('artifact_path', sa.String(length=500), nullable=True),
        sa.Column('model_size_bytes', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('model_id')
    )
    op.create_index('idx_model_name_version', 'ml_models', ['name', 'version'])
    op.create_index('idx_model_production', 'ml_models', ['is_production'])
    op.create_index('idx_model_status', 'ml_models', ['status'])
    op.create_index(op.f('ix_ml_models_mlflow_run_id'), 'ml_models', ['mlflow_run_id'], unique=True)
    op.create_index(op.f('ix_ml_models_name'), 'ml_models', ['name'])

    # Create experiments table
    op.create_table(
        'experiments',
        sa.Column('experiment_id', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('mlflow_experiment_id', sa.String(length=100), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('artifact_location', sa.String(length=500), nullable=True),
        sa.Column('run_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('experiment_id'),
        sa.UniqueConstraint('mlflow_experiment_id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_experiments_name'), 'experiments', ['name'], unique=True)

    # Create deployments table
    op.create_table(
        'deployments',
        sa.Column('deployment_id', sa.String(length=100), nullable=False),
        sa.Column('model_id', sa.String(length=100), nullable=False),
        sa.Column('deployment_name', sa.String(length=200), nullable=False),
        sa.Column('environment', sa.String(length=50), nullable=False),
        sa.Column('strategy', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('health_status', sa.String(length=50), nullable=True, server_default='unknown'),
        sa.Column('replicas', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('resource_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('endpoint_url', sa.String(length=500), nullable=True),
        sa.Column('traffic_percentage', sa.Integer(), nullable=True, server_default='100'),
        sa.Column('rollout_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('deployed_at', sa.DateTime(), nullable=True),
        sa.Column('last_health_check', sa.DateTime(), nullable=True),
        sa.Column('request_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('error_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('avg_latency_ms', sa.Integer(), nullable=True),
        sa.Column('deployed_by', sa.String(length=100), nullable=True),
        sa.Column('deployment_notes', sa.String(length=1000), nullable=True),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['model_id'], ['ml_models.model_id'], ),
        sa.PrimaryKeyConstraint('deployment_id')
    )
    op.create_index('idx_deployment_environment', 'deployments', ['environment'])
    op.create_index('idx_deployment_model', 'deployments', ['model_id'])
    op.create_index('idx_deployment_status', 'deployments', ['status'])

    # Create drift_detections table
    op.create_table(
        'drift_detections',
        sa.Column('drift_id', sa.String(length=100), nullable=False),
        sa.Column('model_id', sa.String(length=100), nullable=False),
        sa.Column('deployment_id', sa.String(length=100), nullable=True),
        sa.Column('detection_timestamp', sa.DateTime(), nullable=False),
        sa.Column('drift_type', sa.String(length=50), nullable=False),
        sa.Column('drift_score', sa.Float(), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=True, server_default='0.7'),
        sa.Column('is_drift_detected', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('affected_features', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('statistical_tests', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('comparison_window', sa.String(length=100), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('recommendations', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('auto_retrain_triggered', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('detection_method', sa.String(length=100), nullable=True),
        sa.Column('config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['deployment_id'], ['deployments.deployment_id'], ),
        sa.ForeignKeyConstraint(['model_id'], ['ml_models.model_id'], ),
        sa.PrimaryKeyConstraint('drift_id')
    )
    op.create_index('idx_drift_detected', 'drift_detections', ['is_drift_detected'])
    op.create_index('idx_drift_model_timestamp', 'drift_detections', ['model_id', 'detection_timestamp'])


def downgrade() -> None:
    op.drop_table('drift_detections')
    op.drop_table('deployments')
    op.drop_table('experiments')
    op.drop_table('ml_models')
