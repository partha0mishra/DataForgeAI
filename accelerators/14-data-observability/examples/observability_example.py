"""Example: Data observability."""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from monitoring.quality_monitor import QualityMonitor


def main():
    """Run observability example."""
    print("=" * 80)
    print(" DataForge Data Observability - Example")
    print("=" * 80)

    monitor = QualityMonitor()

    # Create sample data with quality issues
    df = pd.DataFrame({
        "col1": [1, 2, None, 4, 5],
        "col2": ["a", "b", "c", None, "e"],
        "col3": [10, 20, 30, 40, 50],
    })

    print("\n1. Freshness Monitoring...")
    
    # Check fresh data
    fresh_metric = monitor.check_freshness(
        table="orders",
        last_update=datetime.utcnow() - timedelta(hours=2),
        max_age_hours=24,
    )
    print(f"   Orders table: {fresh_metric.value:.1f}h old - {'✓ PASS' if fresh_metric.passed else '✗ FAIL'}")

    # Check stale data
    stale_metric = monitor.check_freshness(
        table="legacy_data",
        last_update=datetime.utcnow() - timedelta(hours=48),
        max_age_hours=24,
    )
    print(f"   Legacy table: {stale_metric.value:.1f}h old - {'✓ PASS' if stale_metric.passed else '✗ FAIL'}")

    print("\n2. Completeness Monitoring...")

    completeness_metric = monitor.check_completeness(
        table="customer_data",
        df=df,
        min_completeness=0.95,
    )
    print(f"   Customer data: {completeness_metric.value:.1%} complete - {'✓ PASS' if completeness_metric.passed else '✗ FAIL'}")

    print("\n3. Metrics Summary:")
    all_metrics = monitor.get_metrics()
    print(f"   Total checks: {len(all_metrics)}")
    passed = sum(1 for m in all_metrics if m.passed)
    print(f"   Passed: {passed}/{len(all_metrics)}")

    print("\n" + "=" * 80)
    print(" Observability Example Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
