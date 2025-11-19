"""
Feast Feature Definitions for Customer Churn Prediction

This module defines:
- Entities: customer_id
- Feature Views: billing_features, usage_features, support_features
- Value types and TTLs for online serving
- Batch and streaming sources

Feature Store Architecture:
- Offline Store: Snowflake (historical features for training)
- Online Store: Redis (low-latency serving for inference)
- Registry: Local file (can be migrated to S3/GCS for production)
"""

from datetime import timedelta
from typing import Optional

from feast import (
    Entity,
    Feature,
    FeatureView,
    Field,
    FileSource,
    PushSource,
    RequestSource,
    SnowflakeSource,
    ValueType,
)
from feast.types import Float32, Float64, Int32, Int64, String, UnixTimestamp


# ============================================================================
# Entities
# ============================================================================

customer = Entity(
    name="customer_id",
    description="Customer unique identifier",
    value_type=ValueType.INT64,
)


# ============================================================================
# Data Sources
# ============================================================================

# Snowflake source for offline features (historical data)
snowflake_source = SnowflakeSource(
    database="ANALYTICS",
    schema="PUBLIC",
    table="FEAST_FEATURES",
    timestamp_field="event_timestamp",
    created_timestamp_column="event_timestamp",
)


# ============================================================================
# Feature Views
# ============================================================================

# ---------------------------------------------------------------------------
# Billing Features
# ---------------------------------------------------------------------------

billing_features_view = FeatureView(
    name="billing_features",
    description="Customer billing and payment behavior features",
    entities=[customer],
    ttl=timedelta(days=90),  # Features are valid for 90 days
    schema=[
        Field(name="spend_7d", dtype=Float64,
              description="Total spend in last 7 days"),
        Field(name="spend_30d", dtype=Float64,
              description="Total spend in last 30 days"),
        Field(name="spend_90d", dtype=Float64,
              description="Total spend in last 90 days"),
        Field(name="invoice_count_7d", dtype=Int64,
              description="Number of invoices in last 7 days"),
        Field(name="invoice_count_30d", dtype=Int64,
              description="Number of invoices in last 30 days"),
        Field(name="invoice_count_90d", dtype=Int64,
              description="Number of invoices in last 90 days"),
        Field(name="avg_invoice_amount_30d", dtype=Float64,
              description="Average invoice amount in last 30 days"),
        Field(name="avg_payment_delay_days_90d", dtype=Float64,
              description="Average payment delay in days (last 90 days)"),
        Field(name="late_payment_count_90d", dtype=Int64,
              description="Count of late payments in last 90 days"),
        Field(name="spend_trend_30d", dtype=Float64,
              description="Spend trend ratio (current 30d / previous 30d)"),
    ],
    source=snowflake_source,
    online=True,  # Enable online serving
    tags={
        "team": "billing",
        "use_case": "churn_prediction",
        "pii": "false",
    },
)


# ---------------------------------------------------------------------------
# Usage Features
# ---------------------------------------------------------------------------

usage_features_view = FeatureView(
    name="usage_features",
    description="Customer product usage and engagement features",
    entities=[customer],
    ttl=timedelta(days=90),
    schema=[
        Field(name="session_count_7d", dtype=Int64,
              description="Number of sessions in last 7 days"),
        Field(name="session_count_30d", dtype=Int64,
              description="Number of sessions in last 30 days"),
        Field(name="session_count_90d", dtype=Int64,
              description="Number of sessions in last 90 days"),
        Field(name="active_days_7d", dtype=Int64,
              description="Number of active days in last 7 days"),
        Field(name="active_days_30d", dtype=Int64,
              description="Number of active days in last 30 days"),
        Field(name="avg_session_duration_30d", dtype=Float64,
              description="Average session duration in minutes (last 30 days)"),
        Field(name="unique_features_used_30d", dtype=Int64,
              description="Count of unique product features used (last 30 days)"),
        Field(name="total_actions_30d", dtype=Int64,
              description="Total user actions/events (last 30 days)"),
        Field(name="avg_engagement_score_7d", dtype=Float64,
              description="Average engagement score (last 7 days)"),
    ],
    source=snowflake_source,
    online=True,
    tags={
        "team": "product",
        "use_case": "churn_prediction",
        "pii": "false",
    },
)


# ---------------------------------------------------------------------------
# Support Features
# ---------------------------------------------------------------------------

support_features_view = FeatureView(
    name="support_features",
    description="Customer support interaction and satisfaction features",
    entities=[customer],
    ttl=timedelta(days=90),
    schema=[
        Field(name="ticket_count_7d", dtype=Int64,
              description="Number of support tickets in last 7 days"),
        Field(name="ticket_count_30d", dtype=Int64,
              description="Number of support tickets in last 30 days"),
        Field(name="ticket_count_90d", dtype=Int64,
              description="Number of support tickets in last 90 days"),
        Field(name="critical_ticket_count_30d", dtype=Int64,
              description="Number of critical priority tickets (last 30 days)"),
        Field(name="high_priority_ticket_count_30d", dtype=Int64,
              description="Number of high priority tickets (last 30 days)"),
        Field(name="avg_resolution_time_hours_90d", dtype=Float64,
              description="Average ticket resolution time in hours (last 90 days)"),
        Field(name="open_ticket_count", dtype=Int64,
              description="Current count of open tickets"),
        Field(name="avg_satisfaction_score_90d", dtype=Float64,
              description="Average customer satisfaction score (last 90 days)"),
        Field(name="escalation_rate_90d", dtype=Float64,
              description="Ticket escalation rate (last 90 days)"),
    ],
    source=snowflake_source,
    online=True,
    tags={
        "team": "support",
        "use_case": "churn_prediction",
        "pii": "false",
    },
)


# ---------------------------------------------------------------------------
# Customer Profile Features
# ---------------------------------------------------------------------------

customer_profile_view = FeatureView(
    name="customer_profile",
    description="Customer demographic and account features",
    entities=[customer],
    ttl=timedelta(days=365),  # Profile features change less frequently
    schema=[
        Field(name="customer_tier", dtype=String,
              description="Customer tier (free, pro, enterprise)"),
        Field(name="industry", dtype=String,
              description="Customer industry vertical"),
        Field(name="company_size", dtype=String,
              description="Company size category"),
        Field(name="country", dtype=String,
              description="Customer country"),
        Field(name="region", dtype=String,
              description="Customer region"),
        Field(name="account_age_days", dtype=Int64,
              description="Days since account creation"),
    ],
    source=snowflake_source,
    online=True,
    tags={
        "team": "customer-success",
        "use_case": "churn_prediction",
        "pii": "false",
    },
)


# ============================================================================
# Feature Services (Groups of features for specific use cases)
# ============================================================================

from feast import FeatureService

# Feature service for churn prediction model
churn_prediction_service = FeatureService(
    name="churn_prediction_v1",
    description="Features for customer churn prediction model",
    features=[
        billing_features_view,
        usage_features_view,
        support_features_view,
        customer_profile_view,
    ],
    tags={
        "model": "churn_prediction",
        "version": "v1",
        "owner": "ml-engineering",
    },
)


# Feature service for customer health score
customer_health_service = FeatureService(
    name="customer_health_score",
    description="Features for real-time customer health scoring",
    features=[
        usage_features_view[
            ["session_count_7d", "active_days_7d", "avg_engagement_score_7d"]
        ],
        support_features_view[
            ["ticket_count_7d", "open_ticket_count", "avg_satisfaction_score_90d"]
        ],
        billing_features_view[
            ["spend_30d", "spend_trend_30d", "late_payment_count_90d"]
        ],
    ],
    tags={
        "use_case": "customer_health",
        "owner": "customer-success",
    },
)


# ============================================================================
# On-Demand Feature Views (Computed at request time)
# ============================================================================

from feast import OnDemandFeatureView
from feast.on_demand_feature_view import on_demand_feature_view


# Define request data schema
input_request = RequestSource(
    name="request_data",
    schema=[
        Field(name="current_date", dtype=String),
    ],
)


@on_demand_feature_view(
    sources=[
        billing_features_view,
        usage_features_view,
    ],
    schema=[
        Field(name="spend_per_session_30d", dtype=Float64),
        Field(name="engagement_billing_ratio", dtype=Float64),
        Field(name="activity_intensity_30d", dtype=Float64),
    ],
    description="Computed features combining billing and usage metrics",
)
def computed_features(features_df):
    """
    Compute derived features at request time.

    These features are calculated on-the-fly when serving features,
    allowing for real-time feature engineering without pre-computation.
    """
    import pandas as pd

    df = pd.DataFrame()

    # Spend per session (efficiency metric)
    df["spend_per_session_30d"] = (
        features_df["spend_30d"] / features_df["session_count_30d"].replace(0, 1)
    )

    # Engagement to billing ratio
    df["engagement_billing_ratio"] = (
        features_df["avg_engagement_score_7d"] / features_df["spend_trend_30d"].replace(0, 1)
    )

    # Activity intensity (sessions per active day)
    df["activity_intensity_30d"] = (
        features_df["session_count_30d"] / features_df["active_days_30d"].replace(0, 1)
    )

    return df


# ============================================================================
# Stream Feature Views (for real-time streaming features)
# ============================================================================

# Example: Real-time event stream processing
# Uncomment if you have streaming infrastructure (Kafka, Kinesis, etc.)

"""
from feast import KafkaSource, StreamFeatureView

realtime_events_source = KafkaSource(
    name="realtime_customer_events",
    kafka_bootstrap_servers="localhost:9092",
    topic="customer-events",
    timestamp_field="event_timestamp",
    batch_source=snowflake_source,  # Fallback for historical data
)

realtime_activity_view = StreamFeatureView(
    name="realtime_activity",
    description="Real-time customer activity metrics",
    entities=[customer],
    ttl=timedelta(hours=1),  # Short TTL for real-time features
    schema=[
        Field(name="events_last_hour", dtype=Int64),
        Field(name="last_action_timestamp", dtype=UnixTimestamp),
        Field(name="current_session_duration", dtype=Float32),
    ],
    source=realtime_events_source,
    online=True,
    tags={
        "latency": "real-time",
        "use_case": "live_monitoring",
    },
)
"""


# ============================================================================
# Feature Validation Rules (Data Quality)
# ============================================================================

# Define expectations for feature values
# This ensures data quality in both offline and online stores

from great_expectations.core import ExpectationSuite, ExpectationConfiguration

# Example validation rules (integrate with Great Expectations)
feature_validation_suite = ExpectationSuite(
    expectation_suite_name="feast_features_validation",
    expectations=[
        # Billing features
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_between",
            kwargs={
                "column": "spend_30d",
                "min_value": 0,
                "max_value": 1000000,
            },
        ),
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_not_be_null",
            kwargs={
                "column": "customer_id",
            },
        ),
        # Usage features
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_between",
            kwargs={
                "column": "active_days_30d",
                "min_value": 0,
                "max_value": 30,
            },
        ),
        # Support features
        ExpectationConfiguration(
            expectation_type="expect_column_values_to_be_between",
            kwargs={
                "column": "avg_satisfaction_score_90d",
                "min_value": 0,
                "max_value": 10,
            },
        ),
    ],
)


# ============================================================================
# Feature Metadata and Lineage
# ============================================================================

# Document feature lineage for data governance
FEATURE_LINEAGE = {
    "billing_features": {
        "source_tables": [
            "analytics.billing_transactions",
        ],
        "transformations": [
            "temporal_aggregation",
            "null_handling",
            "trend_calculation",
        ],
        "upstream_dependencies": [
            "data_ingestion_pipeline",
            "billing_etl_dag",
        ],
    },
    "usage_features": {
        "source_tables": [
            "analytics.usage_sessions",
        ],
        "transformations": [
            "temporal_aggregation",
            "session_metrics_calculation",
        ],
        "upstream_dependencies": [
            "event_tracking_pipeline",
            "usage_etl_dag",
        ],
    },
    "support_features": {
        "source_tables": [
            "analytics.support_tickets",
        ],
        "transformations": [
            "temporal_aggregation",
            "satisfaction_score_calculation",
            "escalation_rate_calculation",
        ],
        "upstream_dependencies": [
            "zendesk_integration",
            "support_etl_dag",
        ],
    },
}


# ============================================================================
# Utility Functions
# ============================================================================

def get_feature_list(feature_view_name: str) -> list:
    """Get list of feature names for a specific feature view."""
    feature_views = {
        "billing_features": billing_features_view,
        "usage_features": usage_features_view,
        "support_features": support_features_view,
        "customer_profile": customer_profile_view,
    }

    if feature_view_name not in feature_views:
        raise ValueError(f"Unknown feature view: {feature_view_name}")

    return [field.name for field in feature_views[feature_view_name].schema]


def get_all_features() -> list:
    """Get list of all feature names across all views."""
    all_features = []
    for view in [billing_features_view, usage_features_view,
                 support_features_view, customer_profile_view]:
        all_features.extend([field.name for field in view.schema])
    return all_features


if __name__ == "__main__":
    # Print feature summary
    print("=" * 80)
    print("Feast Feature Store Summary")
    print("=" * 80)
    print(f"\nEntity: {customer.name} ({customer.value_type})")
    print(f"\nFeature Views: 4")
    print(f"  - {billing_features_view.name}: {len(billing_features_view.schema)} features")
    print(f"  - {usage_features_view.name}: {len(usage_features_view.schema)} features")
    print(f"  - {support_features_view.name}: {len(support_features_view.schema)} features")
    print(f"  - {customer_profile_view.name}: {len(customer_profile_view.schema)} features")
    print(f"\nTotal Features: {len(get_all_features())}")
    print(f"\nFeature Services: 2")
    print(f"  - {churn_prediction_service.name}")
    print(f"  - {customer_health_service.name}")
    print("\n" + "=" * 80)
