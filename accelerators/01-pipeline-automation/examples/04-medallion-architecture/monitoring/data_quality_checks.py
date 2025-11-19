#!/usr/bin/env python3
"""
Data Quality Monitoring for Medallion Architecture
===================================================

Comprehensive data quality checks for bronze, silver, and gold layers.
Monitors row counts, null percentages, value ranges, freshness, and more.

Features:
    - Layer-specific quality metrics
    - Threshold-based alerts
    - Trend analysis
    - HTML and JSON report generation
    - Integration with logging/alerting systems

Usage:
    # Run all checks
    python data_quality_checks.py --delta-path /path/to/delta-lake

    # Check specific layer
    python data_quality_checks.py --layer silver

    # Generate report
    python data_quality_checks.py --report-format html --output report.html

Author: DataForgeAI Team
Version: 1.0.0
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import (
    col, count, sum as spark_sum, avg, max as spark_max,
    min as spark_min, stddev, current_timestamp, expr,
    countDistinct, when, isnan, isnull, percentile_approx
)

# ============================================================================
# CONFIGURATION
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Quality thresholds
QUALITY_THRESHOLDS = {
    "max_null_percentage": 5.0,  # Maximum acceptable null percentage
    "min_row_count": 100,  # Minimum expected rows
    "max_duplicate_percentage": 1.0,  # Maximum acceptable duplicates
    "max_data_age_hours": 24,  # Maximum data age in hours
    "temperature_range": (-50, 150),  # Valid temperature range
    "humidity_range": (0, 100),  # Valid humidity range
    "battery_range": (0, 100)  # Valid battery level range
}


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class QualityCheck:
    """Individual quality check result."""
    check_name: str
    layer: str
    table: str
    status: str  # PASS, WARN, FAIL
    value: Any
    threshold: Optional[Any]
    message: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class QualityReport:
    """Complete quality report."""
    report_id: str
    timestamp: str
    layers_checked: List[str]
    total_checks: int
    passed_checks: int
    warning_checks: int
    failed_checks: int
    checks: List[QualityCheck]
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp,
            "layers_checked": self.layers_checked,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "warning_checks": self.warning_checks,
            "failed_checks": self.failed_checks,
            "checks": [c.to_dict() for c in self.checks],
            "summary": self.summary
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def to_html(self) -> str:
        """Generate HTML report."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Data Quality Report - {self.report_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .metric {{ display: inline-block; margin: 10px 20px; }}
        .pass {{ color: green; font-weight: bold; }}
        .warn {{ color: orange; font-weight: bold; }}
        .fail {{ color: red; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .status-pass {{ background-color: #d4edda; }}
        .status-warn {{ background-color: #fff3cd; }}
        .status-fail {{ background-color: #f8d7da; }}
    </style>
</head>
<body>
    <h1>Data Quality Report</h1>
    <div class="summary">
        <h2>Summary</h2>
        <div class="metric">Report ID: <strong>{self.report_id}</strong></div>
        <div class="metric">Timestamp: <strong>{self.timestamp}</strong></div>
        <div class="metric">Layers: <strong>{', '.join(self.layers_checked)}</strong></div>
        <br>
        <div class="metric">Total Checks: <strong>{self.total_checks}</strong></div>
        <div class="metric pass">Passed: {self.passed_checks}</div>
        <div class="metric warn">Warnings: {self.warning_checks}</div>
        <div class="metric fail">Failed: {self.failed_checks}</div>
    </div>

    <h2>Detailed Checks</h2>
    <table>
        <tr>
            <th>Status</th>
            <th>Layer</th>
            <th>Table</th>
            <th>Check</th>
            <th>Value</th>
            <th>Threshold</th>
            <th>Message</th>
        </tr>
"""

        for check in self.checks:
            status_class = f"status-{check.status.lower()}"
            html += f"""
        <tr class="{status_class}">
            <td class="{check.status.lower()}">{check.status}</td>
            <td>{check.layer}</td>
            <td>{check.table}</td>
            <td>{check.check_name}</td>
            <td>{check.value}</td>
            <td>{check.threshold if check.threshold else 'N/A'}</td>
            <td>{check.message}</td>
        </tr>
"""

        html += """
    </table>
</body>
</html>
"""
        return html


# ============================================================================
# QUALITY CHECKER
# ============================================================================

class DataQualityChecker:
    """Data quality checker for Delta tables."""

    def __init__(self, spark: SparkSession, delta_base_path: str):
        """
        Initialize quality checker.

        Args:
            spark: SparkSession
            delta_base_path: Base path to Delta Lake tables
        """
        self.spark = spark
        self.delta_base_path = delta_base_path
        self.checks: List[QualityCheck] = []

    def _add_check(
        self,
        check_name: str,
        layer: str,
        table: str,
        status: str,
        value: Any,
        threshold: Optional[Any],
        message: str
    ) -> None:
        """Add a quality check result."""
        check = QualityCheck(
            check_name=check_name,
            layer=layer,
            table=table,
            status=status,
            value=value,
            threshold=threshold,
            message=message,
            timestamp=datetime.now().isoformat()
        )
        self.checks.append(check)
        logger.info(f"[{status}] {layer}.{table} - {check_name}: {message}")

    def check_row_count(self, df: DataFrame, layer: str, table: str, min_rows: int = None) -> None:
        """Check row count against threshold."""
        min_rows = min_rows or QUALITY_THRESHOLDS["min_row_count"]
        row_count = df.count()

        if row_count >= min_rows:
            status = "PASS"
            message = f"Row count {row_count} meets minimum threshold"
        elif row_count > 0:
            status = "WARN"
            message = f"Row count {row_count} below threshold {min_rows}"
        else:
            status = "FAIL"
            message = "Table is empty"

        self._add_check(
            "row_count",
            layer,
            table,
            status,
            row_count,
            min_rows,
            message
        )

    def check_null_percentage(
        self,
        df: DataFrame,
        layer: str,
        table: str,
        columns: List[str],
        max_null_pct: float = None
    ) -> None:
        """Check null percentage for specified columns."""
        max_null_pct = max_null_pct or QUALITY_THRESHOLDS["max_null_percentage"]
        total_rows = df.count()

        if total_rows == 0:
            return

        for column in columns:
            if column not in df.columns:
                continue

            null_count = df.filter(col(column).isNull()).count()
            null_percentage = (null_count / total_rows) * 100

            if null_percentage == 0:
                status = "PASS"
                message = f"No nulls found in {column}"
            elif null_percentage <= max_null_pct:
                status = "PASS"
                message = f"Null percentage {null_percentage:.2f}% within threshold"
            else:
                status = "FAIL"
                message = f"Null percentage {null_percentage:.2f}% exceeds threshold"

            self._add_check(
                f"null_check_{column}",
                layer,
                table,
                status,
                f"{null_percentage:.2f}%",
                f"{max_null_pct}%",
                message
            )

    def check_value_range(
        self,
        df: DataFrame,
        layer: str,
        table: str,
        column: str,
        valid_range: Tuple[float, float]
    ) -> None:
        """Check if values are within expected range."""
        if column not in df.columns:
            return

        total_rows = df.count()
        if total_rows == 0:
            return

        min_val, max_val = valid_range
        out_of_range = df.filter(
            (col(column) < min_val) | (col(column) > max_val)
        ).count()

        out_of_range_pct = (out_of_range / total_rows) * 100

        if out_of_range == 0:
            status = "PASS"
            message = f"All {column} values within range [{min_val}, {max_val}]"
        elif out_of_range_pct <= 1.0:
            status = "WARN"
            message = f"{out_of_range_pct:.2f}% of {column} values out of range"
        else:
            status = "FAIL"
            message = f"{out_of_range_pct:.2f}% of {column} values out of range"

        self._add_check(
            f"range_check_{column}",
            layer,
            table,
            status,
            f"{out_of_range} rows ({out_of_range_pct:.2f}%)",
            f"[{min_val}, {max_val}]",
            message
        )

    def check_data_freshness(
        self,
        df: DataFrame,
        layer: str,
        table: str,
        timestamp_column: str,
        max_age_hours: int = None
    ) -> None:
        """Check data freshness based on timestamp column."""
        max_age_hours = max_age_hours or QUALITY_THRESHOLDS["max_data_age_hours"]

        if timestamp_column not in df.columns:
            return

        # Get latest timestamp
        latest_timestamp = df.agg(spark_max(timestamp_column)).collect()[0][0]

        if latest_timestamp is None:
            self._add_check(
                "freshness_check",
                layer,
                table,
                "FAIL",
                "No timestamp",
                f"{max_age_hours}h",
                "No timestamp found in data"
            )
            return

        # Calculate age
        age_hours = (datetime.now() - latest_timestamp).total_seconds() / 3600

        if age_hours <= max_age_hours:
            status = "PASS"
            message = f"Data is fresh ({age_hours:.1f}h old)"
        elif age_hours <= max_age_hours * 2:
            status = "WARN"
            message = f"Data is stale ({age_hours:.1f}h old)"
        else:
            status = "FAIL"
            message = f"Data is very stale ({age_hours:.1f}h old)"

        self._add_check(
            "freshness_check",
            layer,
            table,
            status,
            f"{age_hours:.1f}h",
            f"{max_age_hours}h",
            message
        )

    def check_duplicates(
        self,
        df: DataFrame,
        layer: str,
        table: str,
        key_columns: List[str],
        max_duplicate_pct: float = None
    ) -> None:
        """Check for duplicate records based on key columns."""
        max_duplicate_pct = max_duplicate_pct or QUALITY_THRESHOLDS["max_duplicate_percentage"]

        total_rows = df.count()
        if total_rows == 0:
            return

        distinct_rows = df.select(key_columns).distinct().count()
        duplicate_rows = total_rows - distinct_rows
        duplicate_pct = (duplicate_rows / total_rows) * 100

        if duplicate_pct == 0:
            status = "PASS"
            message = "No duplicates found"
        elif duplicate_pct <= max_duplicate_pct:
            status = "PASS"
            message = f"Duplicate rate {duplicate_pct:.2f}% within threshold"
        else:
            status = "FAIL"
            message = f"Duplicate rate {duplicate_pct:.2f}% exceeds threshold"

        self._add_check(
            "duplicate_check",
            layer,
            table,
            status,
            f"{duplicate_rows} rows ({duplicate_pct:.2f}%)",
            f"{max_duplicate_pct}%",
            message
        )

    def check_statistics(self, df: DataFrame, layer: str, table: str, column: str) -> None:
        """Calculate and log basic statistics for a column."""
        if column not in df.columns:
            return

        stats = df.select(
            avg(column).alias("avg"),
            spark_min(column).alias("min"),
            spark_max(column).alias("max"),
            stddev(column).alias("stddev")
        ).collect()[0]

        message = f"avg={stats['avg']:.2f}, min={stats['min']:.2f}, max={stats['max']:.2f}, stddev={stats['stddev']:.2f}"

        self._add_check(
            f"statistics_{column}",
            layer,
            table,
            "PASS",
            message,
            None,
            f"Statistics computed for {column}"
        )

    def check_bronze_iot_events(self) -> None:
        """Run quality checks on bronze IoT events table."""
        logger.info("Checking bronze IoT events...")

        table_path = f"{self.delta_base_path}/bronze/iot_events"
        try:
            df = self.spark.read.format("delta").load(table_path)

            self.check_row_count(df, "bronze", "iot_events")
            self.check_null_percentage(
                df, "bronze", "iot_events",
                ["raw_value", "kafka_topic", "kafka_offset"]
            )
            self.check_data_freshness(df, "bronze", "iot_events", "kafka_timestamp")

        except Exception as e:
            logger.error(f"Error checking bronze IoT events: {e}")
            self._add_check(
                "table_access",
                "bronze",
                "iot_events",
                "FAIL",
                str(e),
                None,
                f"Failed to access table: {e}"
            )

    def check_silver_iot_events(self) -> None:
        """Run quality checks on silver IoT events table."""
        logger.info("Checking silver IoT events...")

        table_path = f"{self.delta_base_path}/silver/iot_events"
        try:
            df = self.spark.read.format("delta").load(table_path)

            self.check_row_count(df, "silver", "iot_events")
            self.check_null_percentage(
                df, "silver", "iot_events",
                ["device_id", "event_timestamp", "temperature"]
            )
            self.check_data_freshness(df, "silver", "iot_events", "event_timestamp")
            self.check_duplicates(df, "silver", "iot_events", ["event_id"])
            self.check_value_range(
                df, "silver", "iot_events",
                "temperature", QUALITY_THRESHOLDS["temperature_range"]
            )
            self.check_value_range(
                df, "silver", "iot_events",
                "humidity", QUALITY_THRESHOLDS["humidity_range"]
            )
            self.check_value_range(
                df, "silver", "iot_events",
                "battery_level", QUALITY_THRESHOLDS["battery_range"]
            )
            self.check_statistics(df, "silver", "iot_events", "temperature")
            self.check_statistics(df, "silver", "iot_events", "battery_level")

        except Exception as e:
            logger.error(f"Error checking silver IoT events: {e}")
            self._add_check(
                "table_access",
                "silver",
                "iot_events",
                "FAIL",
                str(e),
                None,
                f"Failed to access table: {e}"
            )

    def check_gold_hourly_metrics(self) -> None:
        """Run quality checks on gold hourly metrics table."""
        logger.info("Checking gold hourly metrics...")

        table_path = f"{self.delta_base_path}/gold/hourly_metrics"
        try:
            df = self.spark.read.format("delta").load(table_path)

            self.check_row_count(df, "gold", "hourly_metrics")
            self.check_null_percentage(
                df, "gold", "hourly_metrics",
                ["window_start", "device_id", "event_count"]
            )
            self.check_data_freshness(df, "gold", "hourly_metrics", "window_start", max_age_hours=2)

        except Exception as e:
            logger.error(f"Error checking gold hourly metrics: {e}")
            self._add_check(
                "table_access",
                "gold",
                "hourly_metrics",
                "FAIL",
                str(e),
                None,
                f"Failed to access table: {e}"
            )

    def generate_report(self) -> QualityReport:
        """Generate quality report from collected checks."""
        passed = sum(1 for c in self.checks if c.status == "PASS")
        warnings = sum(1 for c in self.checks if c.status == "WARN")
        failed = sum(1 for c in self.checks if c.status == "FAIL")

        layers = list(set(c.layer for c in self.checks))

        report = QualityReport(
            report_id=f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            layers_checked=layers,
            total_checks=len(self.checks),
            passed_checks=passed,
            warning_checks=warnings,
            failed_checks=failed,
            checks=self.checks,
            summary={
                "overall_status": "PASS" if failed == 0 else ("WARN" if warnings > 0 else "FAIL"),
                "pass_rate": f"{(passed / len(self.checks) * 100):.1f}%" if self.checks else "0%"
            }
        )

        return report


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run data quality checks on medallion architecture"
    )

    parser.add_argument(
        "--delta-path",
        type=str,
        default="/tmp/delta-lake",
        help="Base path to Delta Lake tables"
    )

    parser.add_argument(
        "--layer",
        type=str,
        choices=["bronze", "silver", "gold", "all"],
        default="all",
        help="Layer to check (default: all)"
    )

    parser.add_argument(
        "--report-format",
        type=str,
        choices=["json", "html", "both"],
        default="json",
        help="Report output format (default: json)"
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (prints to stdout if not specified)"
    )

    args = parser.parse_args()

    # Initialize Spark
    spark = (
        SparkSession.builder
        .appName("Data Quality Checks")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .getOrCreate()
    )

    # Initialize checker
    checker = DataQualityChecker(spark, args.delta_path)

    # Run checks based on layer
    if args.layer in ["bronze", "all"]:
        checker.check_bronze_iot_events()

    if args.layer in ["silver", "all"]:
        checker.check_silver_iot_events()

    if args.layer in ["gold", "all"]:
        checker.check_gold_hourly_metrics()

    # Generate report
    report = checker.generate_report()

    # Output report
    if args.report_format in ["json", "both"]:
        json_output = report.to_json()
        if args.output:
            output_path = args.output if args.output.endswith('.json') else f"{args.output}.json"
            with open(output_path, 'w') as f:
                f.write(json_output)
            logger.info(f"JSON report saved to: {output_path}")
        else:
            print(json_output)

    if args.report_format in ["html", "both"]:
        html_output = report.to_html()
        if args.output:
            output_path = args.output if args.output.endswith('.html') else f"{args.output}.html"
            with open(output_path, 'w') as f:
                f.write(html_output)
            logger.info(f"HTML report saved to: {output_path}")
        else:
            print(html_output)

    # Exit with appropriate code
    sys.exit(0 if report.failed_checks == 0 else 1)


if __name__ == "__main__":
    main()
