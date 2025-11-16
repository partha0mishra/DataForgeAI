"""Example: Comprehensive data catalog demonstration."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "backend/src"))

from metadata.catalog import (
    ColumnMetadata,
    DataCatalog,
    DatasetType,
)
from lineage.lineage_tracker import LineageTracker
from schema.schema_registry import SchemaRegistry, SchemaType, CompatibilityMode
from search.semantic_search import SemanticSearchEngine


def print_section(title: str):
    """Print section header."""
    print()
    print("=" * 80)
    print(f" {title}")
    print("=" * 80)
    print()


def main():
    """Run comprehensive catalog example."""
    print("=" * 80)
    print(" DataForge Data Catalog - Comprehensive Example")
    print("=" * 80)

    # Initialize components
    print_section("1. Initialize Catalog Components")

    catalog = DataCatalog()
    schema_registry = SchemaRegistry()
    lineage_tracker = LineageTracker()
    search_engine = SemanticSearchEngine()

    print("✓ Data catalog initialized")
    print("✓ Schema registry initialized")
    print("✓ Lineage tracker initialized")
    print("✓ Semantic search engine initialized")

    # Register schemas
    print_section("2. Register Data Schemas")

    # Customer schema
    customer_schema = {
        "type": "object",
        "properties": {
            "customer_id": {"type": "integer"},
            "first_name": {"type": "string"},
            "last_name": {"type": "string"},
            "email": {"type": "string", "format": "email"},
            "phone": {"type": "string"},
            "created_at": {"type": "string", "format": "date-time"},
        },
        "required": ["customer_id", "email"],
    }

    customer_schema_id = schema_registry.register_schema(
        name="customer_profile",
        namespace="com.dataforge.crm",
        schema=customer_schema,
        schema_type=SchemaType.JSON_SCHEMA,
        description="Customer profile schema",
        compatibility_mode=CompatibilityMode.BACKWARD,
        owner="data_team",
        tags=["customer", "pii"],
    )

    print(f"✓ Registered schema: {customer_schema_id}")

    # Order schema
    order_schema = {
        "type": "object",
        "properties": {
            "order_id": {"type": "integer"},
            "customer_id": {"type": "integer"},
            "order_date": {"type": "string", "format": "date"},
            "total_amount": {"type": "number"},
            "status": {"type": "string", "enum": ["pending", "completed", "cancelled"]},
        },
        "required": ["order_id", "customer_id", "order_date"],
    }

    order_schema_id = schema_registry.register_schema(
        name="order",
        namespace="com.dataforge.sales",
        schema=order_schema,
        schema_type=SchemaType.JSON_SCHEMA,
        description="Order transaction schema",
        owner="sales_team",
        tags=["order", "transaction"],
    )

    print(f"✓ Registered schema: {order_schema_id}")

    # Register datasets
    print_section("3. Register Datasets in Catalog")

    # Raw customer data
    raw_customers_id = catalog.register_dataset(
        name="raw_customers",
        description="Raw customer data from CRM system",
        dataset_type=DatasetType.TABLE,
        source="postgres://crm-prod/raw/customers",
        owner="data_team",
        database="crm",
        schema="raw",
        table="customers",
        columns=[
            ColumnMetadata(
                name="customer_id",
                data_type="integer",
                description="Unique customer identifier",
                primary_key=True,
            ),
            ColumnMetadata(
                name="email",
                data_type="string",
                description="Customer email address",
                tags=["pii"],
            ),
            ColumnMetadata(
                name="phone",
                data_type="string",
                description="Customer phone number",
                tags=["pii"],
            ),
        ],
        tags=["raw", "customer", "pii", "crm"],
    )

    print(f"✓ Registered dataset: {raw_customers_id}")

    # Raw orders
    raw_orders_id = catalog.register_dataset(
        name="raw_orders",
        description="Raw order transactions from e-commerce platform",
        dataset_type=DatasetType.TABLE,
        source="postgres://sales-prod/raw/orders",
        owner="sales_team",
        database="sales",
        schema="raw",
        table="orders",
        tags=["raw", "order", "transaction"],
    )

    print(f"✓ Registered dataset: {raw_orders_id}")

    # Staging customer data
    stg_customers_id = catalog.register_dataset(
        name="stg_customers",
        description="Staged and cleaned customer data",
        dataset_type=DatasetType.VIEW,
        source="postgres://analytics/staging/customers",
        owner="data_team",
        database="analytics",
        schema="staging",
        table="stg_customers",
        tags=["staging", "customer", "cleaned"],
    )

    print(f"✓ Registered dataset: {stg_customers_id}")

    # Analytics customer orders
    analytics_customer_orders_id = catalog.register_dataset(
        name="customer_orders",
        description="Customer orders mart combining customer and order data",
        dataset_type=DatasetType.TABLE,
        source="postgres://analytics/marts/customer_orders",
        owner="analytics_team",
        database="analytics",
        schema="marts",
        table="customer_orders",
        tags=["mart", "customer", "order", "analytics"],
    )

    print(f"✓ Registered dataset: {analytics_customer_orders_id}")

    # Index datasets for search
    print_section("4. Index Datasets for Semantic Search")

    for dataset_id in [
        raw_customers_id,
        raw_orders_id,
        stg_customers_id,
        analytics_customer_orders_id,
    ]:
        metadata = catalog.get_dataset(dataset_id)

        search_engine.index_dataset(
            dataset_id=dataset_id,
            name=metadata.name,
            description=metadata.description,
            metadata={
                "tags": metadata.tags,
                "owner": metadata.owner,
                "dataset_type": metadata.dataset_type.value,
            },
            columns=[c.name for c in metadata.columns],
        )

        print(f"✓ Indexed: {metadata.name}")

    # Track lineage
    print_section("5. Track Data Lineage")

    # raw -> staging lineage
    lineage_tracker.track_transformation(
        source_datasets=[raw_customers_id],
        target_dataset=stg_customers_id,
        transformation="SELECT * FROM raw.customers WHERE deleted_at IS NULL",
        metadata={
            "pipeline": "daily_staging",
            "transformation_type": "filter",
        },
    )

    print(f"✓ Tracked lineage: {raw_customers_id} → {stg_customers_id}")

    # staging -> analytics lineage
    lineage_tracker.track_transformation(
        source_datasets=[stg_customers_id, raw_orders_id],
        target_dataset=analytics_customer_orders_id,
        transformation="""
        SELECT
            c.customer_id,
            c.email,
            COUNT(o.order_id) as total_orders,
            SUM(o.total_amount) as lifetime_value
        FROM staging.stg_customers c
        LEFT JOIN raw.orders o ON c.customer_id = o.customer_id
        GROUP BY c.customer_id, c.email
        """,
        metadata={
            "pipeline": "customer_analytics_mart",
            "transformation_type": "join_aggregate",
        },
    )

    print(f"✓ Tracked lineage: [{stg_customers_id}, {raw_orders_id}] → {analytics_customer_orders_id}")

    # Perform semantic search
    print_section("6. Semantic Search Demonstration")

    search_queries = [
        "customer contact information",
        "order transactions",
        "analytics mart",
        "cleaned data",
    ]

    for query in search_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 80)

        results = search_engine.search(query, top_k=3)

        for i, result in enumerate(results, 1):
            print(f"{i}. {result.name} (score: {result.score:.3f})")
            print(f"   Description: {result.description}")
            print(f"   Matched fields: {', '.join(result.matched_fields)}")
            print(f"   Tags: {', '.join(result.metadata.get('tags', []))}")
            print()

    # Query upstream lineage
    print_section("7. Upstream Lineage Analysis")

    print(f"Getting upstream lineage for: {analytics_customer_orders_id}")
    print()

    upstream = lineage_tracker.get_upstream_lineage(analytics_customer_orders_id)

    print(f"Found {len(upstream.nodes)} nodes and {len(upstream.edges)} edges")
    print()
    print("Lineage chain:")
    for edge in upstream.edges:
        print(f"  {edge.source_id} → {edge.target_id}")
        print(f"    Type: {edge.relationship_type.value}")
        transformation = edge.metadata.get("transformation", "")
        if transformation:
            print(f"    Transformation: {transformation[:100]}...")
        print()

    # Query downstream lineage
    print_section("8. Downstream Lineage Analysis")

    print(f"Getting downstream lineage for: {raw_customers_id}")
    print()

    downstream = lineage_tracker.get_downstream_lineage(raw_customers_id)

    print(f"Found {len(downstream.nodes)} nodes and {len(downstream.edges)} edges")
    print()
    print("Impact chain:")
    for edge in downstream.edges:
        print(f"  {edge.source_id} → {edge.target_id}")
        print(f"    Type: {edge.relationship_type.value}")
        print()

    # Impact analysis
    print_section("9. Impact Analysis")

    print(f"Analyzing impact of changes to: {raw_customers_id}")
    print()

    impact = lineage_tracker.analyze_impact(raw_customers_id)

    print(f"Total affected datasets: {impact['total_affected']}")
    print(f"Maximum depth: {impact['max_depth']}")
    print()
    print("Affected datasets by depth:")
    for depth, datasets in impact['by_depth'].items():
        print(f"  Depth {depth}: {len(datasets)} dataset(s)")
        for dataset in datasets:
            print(f"    - {dataset}")
    print()

    # Get catalog statistics
    print_section("10. Catalog Statistics")

    stats = catalog.get_statistics()

    print(f"Total datasets: {stats['total_datasets']}")
    print()
    print("Datasets by type:")
    for dtype, count in stats['datasets_by_type'].items():
        print(f"  {dtype}: {count}")
    print()
    print("Datasets by owner:")
    for owner, count in stats['datasets_by_owner'].items():
        print(f"  {owner}: {count}")
    print()

    # Search statistics
    search_stats = search_engine.get_statistics()
    print(f"Indexed datasets: {search_stats['total_indexed']}")
    print(f"Embedding model: {search_stats['embedding_model']}")
    print(f"Embedding dimension: {search_stats['embedding_dimension']}")

    # Schema validation
    print_section("11. Schema Compatibility Validation")

    # Try to register new version with additional optional field (backward compatible)
    customer_schema_v2 = customer_schema.copy()
    customer_schema_v2["properties"]["loyalty_tier"] = {"type": "string"}

    print("Testing schema evolution (adding optional field)...")
    is_compatible = schema_registry.validate_compatibility(
        customer_schema_id, customer_schema_v2
    )

    if is_compatible:
        print("✓ Schema v2 is backward compatible")

        schema_registry.register_schema(
            name="customer_profile",
            namespace="com.dataforge.crm",
            schema=customer_schema_v2,
            schema_type=SchemaType.JSON_SCHEMA,
            description="Customer profile schema v2",
            owner="data_team",
        )

        metadata = schema_registry.get_schema_metadata(customer_schema_id)
        print(f"✓ New version registered: v{metadata.latest_version}")
    else:
        print("✗ Schema v2 is not backward compatible")

    # Dataset discovery
    print_section("12. Dataset Discovery by Tags")

    tag_searches = ["customer", "pii", "analytics"]

    for tag in tag_searches:
        datasets = catalog.list_datasets(tags=[tag])
        print(f"\nDatasets tagged with '{tag}': {len(datasets)}")
        for dataset in datasets:
            print(f"  - {dataset.name} ({dataset.dataset_type.value})")

    # Final summary
    print_section("Example Complete!")

    print("Summary:")
    print(f"  ✓ Registered {len(catalog.datasets)} datasets")
    print(f"  ✓ Registered {len(schema_registry.schemas)} schemas")
    print(f"  ✓ Tracked {len(lineage_tracker.edges)} lineage relationships")
    print(f"  ✓ Indexed {search_stats['total_indexed']} datasets for search")
    print()
    print("Next steps:")
    print("  1. Start the API: uvicorn backend.src.api.main:app --reload --port 8003")
    print("  2. Try the API endpoints at http://localhost:8003/docs")
    print("  3. Integrate with your data pipelines for automatic tracking")
    print()


if __name__ == "__main__":
    main()
