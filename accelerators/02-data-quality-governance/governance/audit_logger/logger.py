"""Audit logger for data governance."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from dataforge_common.logging import get_logger
from dataforge_connectors.databases import PostgreSQLConnector

logger = get_logger(__name__)


class AuditLogger:
    """
    Audit logger for tracking data access and operations.

    Logs all data access, modifications, and governance events
    to ensure compliance and enable forensic analysis.

    Example:
        audit = AuditLogger(storage_type="postgres")

        audit.log_access(
            user="user@company.com",
            dataset="customers",
            action="read",
            records=1000
        )

        audit.log_quality_check(
            dataset="orders",
            status="passed",
            metrics={"completeness": 0.99}
        )
    """

    def __init__(
        self,
        storage_type: str = "file",
        storage_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize audit logger.

        Args:
            storage_type: Storage type ('file', 'postgres', 's3')
            storage_config: Configuration for storage backend
        """
        self.storage_type = storage_type
        self.storage_config = storage_config or {}
        self.logger = logger

        if storage_type == "file":
            self.log_dir = Path(self.storage_config.get("log_dir", "audit_logs"))
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_access(
        self,
        user: str,
        dataset: str,
        action: str,
        records: Optional[int] = None,
        columns: Optional[list] = None,
        filters: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Log data access event.

        Args:
            user: User identifier
            dataset: Dataset being accessed
            action: Action type (read, write, delete)
            records: Number of records accessed
            columns: Columns accessed
            filters: Filters applied
            metadata: Additional metadata

        Returns:
            str: Audit log entry ID
        """
        entry = {
            "event_id": self._generate_id(),
            "event_type": "data_access",
            "timestamp": datetime.utcnow().isoformat(),
            "user": user,
            "dataset": dataset,
            "action": action,
            "records": records,
            "columns": columns,
            "filters": filters,
            "metadata": metadata or {},
        }

        self._write_entry(entry)

        self.logger.info(
            "Data access logged",
            user=user,
            dataset=dataset,
            action=action,
            records=records,
        )

        return entry["event_id"]

    def log_quality_check(
        self,
        dataset: str,
        status: str,
        metrics: Dict[str, Any],
        suite: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Log quality check event.

        Args:
            dataset: Dataset checked
            status: Check status (passed, failed, warning)
            metrics: Quality metrics
            suite: Expectation suite name
            metadata: Additional metadata

        Returns:
            str: Audit log entry ID
        """
        entry = {
            "event_id": self._generate_id(),
            "event_type": "quality_check",
            "timestamp": datetime.utcnow().isoformat(),
            "dataset": dataset,
            "status": status,
            "metrics": metrics,
            "suite": suite,
            "metadata": metadata or {},
        }

        self._write_entry(entry)

        self.logger.info(
            "Quality check logged",
            dataset=dataset,
            status=status,
            suite=suite,
        )

        return entry["event_id"]

    def log_pii_detection(
        self,
        dataset: str,
        pii_found: Dict[str, Any],
        action_taken: str,
        metadata: Optional[Dict] = None,
    ) -> str:
        """
        Log PII detection event.

        Args:
            dataset: Dataset scanned
            pii_found: PII detection results
            action_taken: Action taken (masked, flagged, none)
            metadata: Additional metadata

        Returns:
            str: Audit log entry ID
        """
        entry = {
            "event_id": self._generate_id(),
            "event_type": "pii_detection",
            "timestamp": datetime.utcnow().isoformat(),
            "dataset": dataset,
            "pii_found": pii_found,
            "action_taken": action_taken,
            "metadata": metadata or {},
        }

        self._write_entry(entry)

        self.logger.info(
            "PII detection logged",
            dataset=dataset,
            action=action_taken,
        )

        return entry["event_id"]

    def log_policy_violation(
        self,
        user: str,
        dataset: str,
        policy: str,
        violation_type: str,
        details: Dict[str, Any],
    ) -> str:
        """
        Log policy violation event.

        Args:
            user: User who violated policy
            dataset: Dataset involved
            policy: Policy violated
            violation_type: Type of violation
            details: Violation details

        Returns:
            str: Audit log entry ID
        """
        entry = {
            "event_id": self._generate_id(),
            "event_type": "policy_violation",
            "timestamp": datetime.utcnow().isoformat(),
            "severity": "high",
            "user": user,
            "dataset": dataset,
            "policy": policy,
            "violation_type": violation_type,
            "details": details,
        }

        self._write_entry(entry)

        self.logger.warning(
            "Policy violation logged",
            user=user,
            dataset=dataset,
            policy=policy,
        )

        return entry["event_id"]

    def _write_entry(self, entry: Dict[str, Any]) -> None:
        """Write audit entry to storage."""
        if self.storage_type == "file":
            # Write to daily log file
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            log_file = self.log_dir / f"audit_{date_str}.jsonl"

            with open(log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")

        elif self.storage_type == "postgres":
            # Write to PostgreSQL (example)
            # In production, use proper database connection
            pass

    def _generate_id(self) -> str:
        """Generate unique audit entry ID."""
        from dataforge_common.utils import generate_id

        return generate_id(prefix="audit", length=12)

    def query_logs(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_type: Optional[str] = None,
        user: Optional[str] = None,
        dataset: Optional[str] = None,
    ) -> list:
        """
        Query audit logs.

        Args:
            start_date: Start date for query
            end_date: End date for query
            event_type: Filter by event type
            user: Filter by user
            dataset: Filter by dataset

        Returns:
            list: Matching audit log entries
        """
        # Example implementation for file storage
        if self.storage_type == "file":
            results = []

            # Read log files in date range
            for log_file in self.log_dir.glob("audit_*.jsonl"):
                with open(log_file) as f:
                    for line in f:
                        entry = json.loads(line)

                        # Apply filters
                        if event_type and entry.get("event_type") != event_type:
                            continue
                        if user and entry.get("user") != user:
                            continue
                        if dataset and entry.get("dataset") != dataset:
                            continue

                        results.append(entry)

            return results

        return []
