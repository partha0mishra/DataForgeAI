"""Data Quality Checker using Great Expectations."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from great_expectations.core.batch import RuntimeBatchRequest
from great_expectations.data_context import DataContext

from dataforge_common.logging import get_logger
from dataforge_common.monitoring import increment_counter, track_duration
from dataforge_contracts import QualityCheck, QualityMetrics, QualityReport, QualityStatus

logger = get_logger(__name__)


class DataQualityChecker:
    """
    Data quality validation using Great Expectations.

    Example:
        checker = DataQualityChecker(
            context_root_dir="great_expectations",
            datasource_name="my_datasource"
        )

        result = checker.validate_dataframe(
            df=my_dataframe,
            expectation_suite_name="my_suite"
        )

        if result.overall_status == QualityStatus.PASSED:
            print("Data quality checks passed!")
    """

    def __init__(
        self,
        context_root_dir: str = "great_expectations",
        datasource_name: str = "pandas_datasource",
    ):
        """
        Initialize quality checker.

        Args:
            context_root_dir: Path to GE context directory
            datasource_name: Name of datasource to use
        """
        self.context_root_dir = context_root_dir
        self.datasource_name = datasource_name
        self.logger = logger

        # Initialize Great Expectations context
        self.context = self._get_or_create_context()

    def _get_or_create_context(self) -> DataContext:
        """Get or create Great Expectations context."""
        context_path = Path(self.context_root_dir)

        if context_path.exists():
            self.logger.info("Loading existing GE context", path=str(context_path))
            return DataContext(context_root_dir=self.context_root_dir)
        else:
            self.logger.info("Creating new GE context", path=str(context_path))
            # In production, this would be properly initialized
            # For now, return a basic context
            return DataContext(context_root_dir=self.context_root_dir)

    @track_duration("data_quality_validation_seconds")
    def validate_dataframe(
        self,
        df: pd.DataFrame,
        expectation_suite_name: str,
        batch_identifier: Optional[str] = None,
    ) -> QualityReport:
        """
        Validate DataFrame against expectation suite.

        Args:
            df: DataFrame to validate
            expectation_suite_name: Name of expectation suite
            batch_identifier: Optional batch identifier

        Returns:
            QualityReport: Validation results
        """
        self.logger.info(
            "Starting quality validation",
            suite=expectation_suite_name,
            rows=len(df),
            columns=len(df.columns),
        )

        # Generate batch identifier if not provided
        if batch_identifier is None:
            batch_identifier = f"batch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        # Run basic validation (example implementation)
        checks = self._run_basic_checks(df)

        # Calculate metrics
        total_checks = len(checks)
        passed_checks = sum(1 for c in checks if c.status == QualityStatus.PASSED)
        failed_checks = sum(1 for c in checks if c.status == QualityStatus.FAILED)
        warnings = sum(1 for c in checks if c.status == QualityStatus.WARNING)

        metrics = QualityMetrics(
            total_rows=len(df),
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warnings=warnings,
        )

        # Determine overall status
        if failed_checks > 0:
            overall_status = QualityStatus.FAILED
        elif warnings > 0:
            overall_status = QualityStatus.WARNING
        else:
            overall_status = QualityStatus.PASSED

        # Create report
        report = QualityReport(
            report_id=f"qr_{batch_identifier}",
            dataset=batch_identifier,
            timestamp=datetime.utcnow(),
            overall_status=overall_status,
            checks=checks,
            metrics=metrics,
        )

        # Track metrics
        increment_counter(
            "quality_checks_total",
            labels={"status": overall_status.value, "suite": expectation_suite_name},
        )

        self.logger.info(
            "Quality validation complete",
            overall_status=overall_status.value,
            passed=passed_checks,
            failed=failed_checks,
            warnings=warnings,
        )

        return report

    def _run_basic_checks(self, df: pd.DataFrame) -> List[QualityCheck]:
        """
        Run basic quality checks on DataFrame.

        This is an example implementation. In production, this would
        use Great Expectations expectations.
        """
        checks = []

        # Check 1: No null values in key columns (example)
        for col in df.columns:
            null_count = df[col].isnull().sum()
            null_pct = (null_count / len(df)) * 100

            if null_pct == 0:
                status = QualityStatus.PASSED
                message = f"Column '{col}' has no null values"
            elif null_pct < 5:
                status = QualityStatus.WARNING
                message = f"Column '{col}' has {null_pct:.2f}% null values"
            else:
                status = QualityStatus.FAILED
                message = f"Column '{col}' has {null_pct:.2f}% null values (exceeds 5% threshold)"

            checks.append(
                QualityCheck(
                    check_name=f"null_check_{col}",
                    check_type="completeness",
                    status=status,
                    expectation=f"expect_column_values_to_not_be_null: {col}",
                    actual=f"{null_count} nulls ({null_pct:.2f}%)",
                    message=message,
                )
            )

        # Check 2: Row count is reasonable
        if len(df) == 0:
            checks.append(
                QualityCheck(
                    check_name="row_count_check",
                    check_type="volume",
                    status=QualityStatus.FAILED,
                    expectation="expect_table_row_count_to_be_between: min=1",
                    actual=f"{len(df)} rows",
                    message="Table is empty",
                )
            )
        elif len(df) < 10:
            checks.append(
                QualityCheck(
                    check_name="row_count_check",
                    check_type="volume",
                    status=QualityStatus.WARNING,
                    expectation="expect_table_row_count_to_be_between: min=10",
                    actual=f"{len(df)} rows",
                    message="Table has fewer than 10 rows",
                )
            )
        else:
            checks.append(
                QualityCheck(
                    check_name="row_count_check",
                    check_type="volume",
                    status=QualityStatus.PASSED,
                    expectation="expect_table_row_count_to_be_between: min=1",
                    actual=f"{len(df)} rows",
                    message="Table row count is acceptable",
                )
            )

        # Check 3: Column count matches expected (example: at least 2 columns)
        if len(df.columns) < 2:
            checks.append(
                QualityCheck(
                    check_name="column_count_check",
                    check_type="schema",
                    status=QualityStatus.FAILED,
                    expectation="expect_table_column_count_to_be_between: min=2",
                    actual=f"{len(df.columns)} columns",
                    message="Table has fewer than 2 columns",
                )
            )
        else:
            checks.append(
                QualityCheck(
                    check_name="column_count_check",
                    check_type="schema",
                    status=QualityStatus.PASSED,
                    expectation="expect_table_column_count_to_be_between: min=2",
                    actual=f"{len(df.columns)} columns",
                    message="Table column count is acceptable",
                )
            )

        return checks

    def save_report(self, report: QualityReport, output_path: str) -> None:
        """
        Save quality report to file.

        Args:
            report: Quality report to save
            output_path: Path to save report
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            f.write(report.model_dump_json(indent=2))

        self.logger.info("Quality report saved", path=output_path)
