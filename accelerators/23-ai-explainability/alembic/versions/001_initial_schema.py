"""Initial schema for AI Explainability.

Revision ID: 001
Revises:
Create Date: 2025-11-17 04:00:00

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
    # Create explanations table
    op.create_table(
        'explanations',
        sa.Column('explanation_id', sa.String(36), primary_key=True),
        sa.Column('model_id', sa.String(100), nullable=False, index=True),
        sa.Column('model_name', sa.String(200), nullable=True),
        sa.Column('explanation_type', sa.String(50), nullable=False),
        sa.Column('scope', sa.String(20), nullable=False),
        sa.Column('feature_importances', sa.JSON(), nullable=False),
        sa.Column('prediction', sa.JSON(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('base_value', sa.Float(), nullable=True),
        sa.Column('instance_data', sa.JSON(), nullable=True),
        sa.Column('instance_id', sa.String(100), nullable=True, index=True),
        sa.Column('explanation_text', sa.Text(), nullable=True),
        sa.Column('visualization_urls', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('generation_time_ms', sa.Float(), nullable=True),
        sa.Column('num_features', sa.Float(), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index('idx_model_type', 'explanations', ['model_id', 'explanation_type'])
    op.create_index('idx_created_at', 'explanations', ['created_at'])
    op.create_index('idx_scope', 'explanations', ['scope'])

    # Create bias_reports table
    op.create_table(
        'bias_reports',
        sa.Column('report_id', sa.String(36), primary_key=True),
        sa.Column('model_id', sa.String(100), nullable=False, index=True),
        sa.Column('model_name', sa.String(200), nullable=True),
        sa.Column('protected_attributes', sa.JSON(), nullable=False),
        sa.Column('reference_group', sa.String(100), nullable=True),
        sa.Column('metrics_analyzed', sa.JSON(), nullable=False),
        sa.Column('bias_metrics', sa.JSON(), nullable=False),
        sa.Column('overall_fairness_score', sa.Float(), nullable=False),
        sa.Column('compliant', sa.Boolean(), default=False, nullable=False),
        sa.Column('issues_detected', sa.JSON(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.Column('severity', sa.String(20), nullable=True),
        sa.Column('group_statistics', sa.JSON(), nullable=True),
        sa.Column('disparate_impact_ratio', sa.Float(), nullable=True),
        sa.Column('statistical_parity_difference', sa.Float(), nullable=True),
        sa.Column('dataset_size', sa.Float(), nullable=True),
        sa.Column('group_distributions', sa.JSON(), nullable=True),
        sa.Column('summary_text', sa.Text(), nullable=True),
        sa.Column('detailed_findings', sa.Text(), nullable=True),
        sa.Column('visualization_urls', sa.JSON(), nullable=True),
        sa.Column('analysis_duration_ms', sa.Float(), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index('idx_model_compliant', 'bias_reports', ['model_id', 'compliant'])
    op.create_index('idx_bias_created_at', 'bias_reports', ['created_at'])
    op.create_index('idx_severity', 'bias_reports', ['severity'])
    op.create_index('idx_fairness_score', 'bias_reports', ['overall_fairness_score'])

    # Create trust_metrics table
    op.create_table(
        'trust_metrics',
        sa.Column('metric_id', sa.String(36), primary_key=True),
        sa.Column('model_id', sa.String(100), nullable=False, index=True),
        sa.Column('model_name', sa.String(200), nullable=True),
        sa.Column('explainability_score', sa.Float(), nullable=False),
        sa.Column('fairness_score', sa.Float(), nullable=False),
        sa.Column('robustness_score', sa.Float(), nullable=False),
        sa.Column('privacy_score', sa.Float(), nullable=False),
        sa.Column('transparency_score', sa.Float(), nullable=True),
        sa.Column('accountability_score', sa.Float(), nullable=True),
        sa.Column('overall_trust_score', sa.Float(), nullable=False),
        sa.Column('trust_level', sa.String(20), nullable=False),
        sa.Column('dimension_details', sa.JSON(), nullable=True),
        sa.Column('weights', sa.JSON(), nullable=True),
        sa.Column('assessment_type', sa.String(50), nullable=True),
        sa.Column('assessment_criteria', sa.JSON(), nullable=True),
        sa.Column('regulatory_framework', sa.String(100), nullable=True),
        sa.Column('strengths', sa.JSON(), nullable=True),
        sa.Column('weaknesses', sa.JSON(), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.Column('certification_status', sa.String(50), nullable=True),
        sa.Column('previous_score', sa.Float(), nullable=True),
        sa.Column('score_trend', sa.String(20), nullable=True),
        sa.Column('changes_since_last', sa.JSON(), nullable=True),
        sa.Column('summary_text', sa.Text(), nullable=True),
        sa.Column('detailed_report', sa.Text(), nullable=True),
        sa.Column('visualization_urls', sa.JSON(), nullable=True),
        sa.Column('model_version', sa.String(50), nullable=True),
        sa.Column('environment', sa.String(50), nullable=True),
        sa.Column('assessed_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index('idx_model_trust_level', 'trust_metrics', ['model_id', 'trust_level'])
    op.create_index('idx_trust_created_at', 'trust_metrics', ['created_at'])
    op.create_index('idx_overall_score', 'trust_metrics', ['overall_trust_score'])
    op.create_index('idx_environment', 'trust_metrics', ['environment'])

    # Create hallucination_checks table
    op.create_table(
        'hallucination_checks',
        sa.Column('check_id', sa.String(36), primary_key=True),
        sa.Column('model_name', sa.String(200), nullable=False, index=True),
        sa.Column('model_version', sa.String(50), nullable=True),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('output', sa.Text(), nullable=False),
        sa.Column('prompt_hash', sa.String(64), nullable=True, index=True),
        sa.Column('hallucination_risk', sa.String(20), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('hallucination_score', sa.Float(), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('prompt_attribution', sa.JSON(), nullable=True),
        sa.Column('fact_checks', sa.JSON(), nullable=True),
        sa.Column('sources', sa.JSON(), nullable=True),
        sa.Column('grounding_quality', sa.Float(), nullable=True),
        sa.Column('detection_methods', sa.JSON(), nullable=True),
        sa.Column('detection_details', sa.JSON(), nullable=True),
        sa.Column('hallucinated', sa.Boolean(), default=False, nullable=False),
        sa.Column('issues_detected', sa.JSON(), nullable=True),
        sa.Column('severity', sa.String(20), nullable=True),
        sa.Column('recommendations', sa.JSON(), nullable=True),
        sa.Column('alternative_responses', sa.JSON(), nullable=True),
        sa.Column('domain', sa.String(100), nullable=True),
        sa.Column('use_case', sa.String(100), nullable=True),
        sa.Column('user_context', sa.JSON(), nullable=True),
        sa.Column('check_duration_ms', sa.Float(), nullable=True),
        sa.Column('explanation_text', sa.Text(), nullable=True),
        sa.Column('visualization_urls', sa.JSON(), nullable=True),
        sa.Column('checked_by', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_index('idx_model_risk', 'hallucination_checks', ['model_name', 'hallucination_risk'])
    op.create_index('idx_halluc_created_at', 'hallucination_checks', ['created_at'])
    op.create_index('idx_hallucinated', 'hallucination_checks', ['hallucinated'])
    op.create_index('idx_halluc_severity', 'hallucination_checks', ['severity'])


def downgrade() -> None:
    op.drop_table('hallucination_checks')
    op.drop_table('trust_metrics')
    op.drop_table('bias_reports')
    op.drop_table('explanations')
