"""Example: Complete BI Dashboard creation and visualization."""

from pathlib import Path
import sys

import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dashboard.dashboard_manager import DashboardManager, VisualizationType
from visualization.chart_builder import ChartBuilder
from data.query_engine import QueryEngine


def print_section(title: str):
    """Print section header."""
    print()
    print("=" * 80)
    print(f" {title}")
    print("=" * 80)
    print()


def create_sample_data():
    """Create sample sales data."""
    print("Creating sample sales data...")

    # Generate dates
    dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")

    # Generate sales data
    np.random.seed(42)

    data = {
        "date": dates,
        "revenue": np.random.randint(1000, 10000, size=len(dates))
        + np.sin(np.arange(len(dates)) * 2 * np.pi / 365) * 2000,
        "orders": np.random.randint(50, 200, size=len(dates)),
        "customers": np.random.randint(30, 150, size=len(dates)),
        "product_category": np.random.choice(
            ["Electronics", "Clothing", "Home", "Books"], size=len(dates)
        ),
        "region": np.random.choice(
            ["North", "South", "East", "West"], size=len(dates)
        ),
    }

    df = pd.DataFrame(data)

    # Save to CSV
    output_path = Path(__file__).parent / "sample_sales_data.csv"
    df.to_csv(output_path, index=False)

    print(f"✓ Created {len(df)} rows of sample data")
    print(f"✓ Saved to: {output_path}")

    return output_path


def main():
    """Run BI Dashboard example."""
    print("=" * 80)
    print(" DataForge BI Dashboarding - Complete Example")
    print("=" * 80)

    # Step 1: Create sample data
    print_section("1. Create Sample Sales Data")

    data_file = create_sample_data()

    # Step 2: Initialize components
    print_section("2. Initialize Dashboard Components")

    dashboard_manager = DashboardManager()
    chart_builder = ChartBuilder(theme="plotly_white")
    query_engine = QueryEngine()

    print("✓ Dashboard manager initialized")
    print("✓ Chart builder initialized")
    print("✓ Query engine initialized")

    # Step 3: Create dashboard
    print_section("3. Create Sales Dashboard")

    dashboard = dashboard_manager.create_dashboard(
        name="Sales Performance Dashboard",
        description="Monthly sales metrics and trends",
        owner="analytics_team",
        tags=["sales", "performance", "executive"],
    )

    print(f"✓ Dashboard created: {dashboard.dashboard_id}")
    print(f"  Name: {dashboard.name}")
    print(f"  Owner: {dashboard.owner}")
    print(f"  Status: {dashboard.status.value}")

    # Step 4: Add data source
    print_section("4. Add Data Source")

    dashboard_manager.add_data_source(
        dashboard_id=dashboard.dashboard_id,
        source_id="sales_data",
        name="Sales CSV Data",
        type="file",
        file_path=str(data_file),
    )

    print("✓ Data source added: sales_data")
    print(f"  Type: file")
    print(f"  Path: {data_file}")

    # Step 5: Query and preview data
    print_section("5. Query and Preview Data")

    df = query_engine.execute_query(
        source_type="file",
        file_path=str(data_file),
    )

    print(f"✓ Data loaded: {len(df)} rows, {len(df.columns)} columns")
    print()
    print("First 5 rows:")
    print(df.head())
    print()
    print("Data summary:")
    print(df.describe())

    # Step 6: Create visualizations
    print_section("6. Create Visualizations")

    # 6.1 Revenue trend line chart
    print("Creating Revenue Trend chart...")

    revenue_by_date = df.groupby("date")["revenue"].sum().reset_index()

    revenue_chart = chart_builder.create_line_chart(
        data=revenue_by_date,
        x="date",
        y="revenue",
        title="Daily Revenue Trend",
        markers=True,
    )

    dashboard_manager.add_visualization(
        dashboard_id=dashboard.dashboard_id,
        viz_id="revenue_trend",
        name="Revenue Trend",
        type=VisualizationType.LINE_CHART,
        data_source_id="sales_data",
        config={
            "x_axis": "date",
            "y_axis": "revenue",
            "title": "Daily Revenue Trend",
            "markers": True,
        },
        position={"x": 0, "y": 0, "width": 12, "height": 4},
    )

    print("✓ Revenue Trend chart created")

    # 6.2 Sales by category pie chart
    print("Creating Sales by Category chart...")

    sales_by_category = df.groupby("product_category")["revenue"].sum().reset_index()

    category_chart = chart_builder.create_pie_chart(
        data=sales_by_category,
        values="revenue",
        names="product_category",
        title="Sales by Product Category",
    )

    dashboard_manager.add_visualization(
        dashboard_id=dashboard.dashboard_id,
        viz_id="sales_by_category",
        name="Sales by Category",
        type=VisualizationType.PIE_CHART,
        data_source_id="sales_data",
        config={
            "values": "revenue",
            "names": "product_category",
            "title": "Sales by Product Category",
        },
        position={"x": 0, "y": 4, "width": 6, "height": 4},
    )

    print("✓ Sales by Category chart created")

    # 6.3 Sales by region bar chart
    print("Creating Sales by Region chart...")

    sales_by_region = df.groupby("region")["revenue"].sum().reset_index()

    region_chart = chart_builder.create_bar_chart(
        data=sales_by_region,
        x="region",
        y="revenue",
        title="Sales by Region",
        color="region",
    )

    dashboard_manager.add_visualization(
        dashboard_id=dashboard.dashboard_id,
        viz_id="sales_by_region",
        name="Sales by Region",
        type=VisualizationType.BAR_CHART,
        data_source_id="sales_data",
        config={
            "x_axis": "region",
            "y_axis": "revenue",
            "title": "Sales by Region",
        },
        position={"x": 6, "y": 4, "width": 6, "height": 4},
    )

    print("✓ Sales by Region chart created")

    # 6.4 Total revenue metric
    print("Creating Total Revenue metric...")

    total_revenue = df["revenue"].sum()

    revenue_metric = chart_builder.create_metric(
        value=total_revenue,
        title="Total Revenue",
        format="$,.0f",
    )

    dashboard_manager.add_visualization(
        dashboard_id=dashboard.dashboard_id,
        viz_id="total_revenue",
        name="Total Revenue",
        type=VisualizationType.METRIC,
        data_source_id="sales_data",
        config={
            "value": total_revenue,
            "title": "Total Revenue",
            "format": "$,.0f",
        },
        position={"x": 0, "y": 8, "width": 3, "height": 2},
    )

    print(f"✓ Total Revenue metric created: ${total_revenue:,.0f}")

    # 6.5 Total orders metric
    print("Creating Total Orders metric...")

    total_orders = df["orders"].sum()

    orders_metric = chart_builder.create_metric(
        value=total_orders,
        title="Total Orders",
        format=",.0f",
    )

    dashboard_manager.add_visualization(
        dashboard_id=dashboard.dashboard_id,
        viz_id="total_orders",
        name="Total Orders",
        type=VisualizationType.METRIC,
        data_source_id="sales_data",
        config={
            "value": total_orders,
            "title": "Total Orders",
            "format": ",.0f",
        },
        position={"x": 3, "y": 8, "width": 3, "height": 2},
    )

    print(f"✓ Total Orders metric created: {total_orders:,}")

    # Step 7: Dashboard summary
    print_section("7. Dashboard Summary")

    updated_dashboard = dashboard_manager.get_dashboard(dashboard.dashboard_id)

    print(f"Dashboard: {updated_dashboard.name}")
    print(f"ID: {updated_dashboard.dashboard_id}")
    print(f"Status: {updated_dashboard.status.value}")
    print(f"Owner: {updated_dashboard.owner}")
    print()
    print(f"Data Sources: {len(updated_dashboard.data_sources)}")
    for ds in updated_dashboard.data_sources:
        print(f"  - {ds.name} ({ds.type})")
    print()
    print(f"Visualizations: {len(updated_dashboard.visualizations)}")
    for viz in updated_dashboard.visualizations:
        print(f"  - {viz.name} ({viz.type.value})")
        print(f"    Position: x={viz.position['x']}, y={viz.position['y']}, " +
              f"w={viz.position['width']}, h={viz.position['height']}")

    # Step 8: Publish dashboard
    print_section("8. Publish Dashboard")

    dashboard_manager.publish_dashboard(dashboard.dashboard_id)

    print(f"✓ Dashboard published")
    print(f"  Status: {dashboard_manager.get_dashboard(dashboard.dashboard_id).status.value}")

    # Step 9: Share dashboard
    print_section("9. Share Dashboard")

    dashboard_manager.share_dashboard(
        dashboard_id=dashboard.dashboard_id,
        users=["user1@company.com", "user2@company.com"],
        permission="viewer",
    )

    print("✓ Dashboard shared with 2 users")
    print("  Permission: viewer")

    # Step 10: Export dashboard
    print_section("10. Export Dashboard")

    export = dashboard_manager.export_dashboard(dashboard.dashboard_id)

    print("✓ Dashboard exported to JSON")
    print()
    print("Export preview:")
    print(f"  Name: {export['name']}")
    print(f"  Visualizations: {len(export['visualizations'])}")
    print(f"  Data Sources: {len(export['data_sources'])}")

    # Step 11: Clone dashboard
    print_section("11. Clone Dashboard")

    cloned = dashboard_manager.clone_dashboard(
        dashboard_id=dashboard.dashboard_id,
        new_name="Sales Performance Dashboard (Copy)",
        owner="marketing_team",
    )

    print(f"✓ Dashboard cloned")
    print(f"  Original: {dashboard.dashboard_id}")
    print(f"  Clone: {cloned.dashboard_id}")
    print(f"  New Owner: {cloned.owner}")

    # Final summary
    print_section("Example Complete!")

    all_dashboards = dashboard_manager.list_dashboards()

    print("Summary:")
    print(f"  ✓ Created 1 dashboard with 5 visualizations")
    print(f"  ✓ Loaded {len(df)} rows of sample data")
    print(f"  ✓ Published dashboard")
    print(f"  ✓ Shared with 2 users")
    print(f"  ✓ Cloned dashboard")
    print(f"  ✓ Total dashboards: {len(all_dashboards)}")
    print()
    print("Visualizations created:")
    print("  1. Revenue Trend (line chart)")
    print("  2. Sales by Category (pie chart)")
    print("  3. Sales by Region (bar chart)")
    print("  4. Total Revenue (metric)")
    print("  5. Total Orders (metric)")
    print()
    print("Next steps:")
    print("  1. Start API: uvicorn src.api.main:app --reload --port 8005")
    print("  2. Try API at http://localhost:8005/docs")
    print("  3. View dashboards and create new visualizations")
    print()


if __name__ == "__main__":
    main()
