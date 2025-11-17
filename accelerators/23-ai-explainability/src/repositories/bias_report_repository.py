"""Repository for BiasReport model."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from src.models.bias_report import BiasReport


class BiasReportRepository:
    """Repository for managing bias reports."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    def create(self, report_data: Dict[str, Any]) -> BiasReport:
        """Create a new bias report."""
        report = BiasReport(**report_data)
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_by_id(self, report_id: str) -> Optional[BiasReport]:
        """Get bias report by ID."""
        return self.db.query(BiasReport).filter(BiasReport.report_id == report_id).first()

    def get_by_model_id(
        self,
        model_id: str,
        limit: int = 50
    ) -> List[BiasReport]:
        """Get all bias reports for a model."""
        return (
            self.db.query(BiasReport)
            .filter(BiasReport.model_id == model_id)
            .order_by(desc(BiasReport.created_at))
            .limit(limit)
            .all()
        )

    def get_latest_by_model(self, model_id: str) -> Optional[BiasReport]:
        """Get the most recent bias report for a model."""
        return (
            self.db.query(BiasReport)
            .filter(BiasReport.model_id == model_id)
            .order_by(desc(BiasReport.created_at))
            .first()
        )

    def get_non_compliant_reports(
        self,
        severity: Optional[str] = None,
        hours: Optional[int] = None
    ) -> List[BiasReport]:
        """
        Get non-compliant bias reports.

        Args:
            severity: Optional filter by severity level
            hours: Optional time range in hours

        Returns:
            List of non-compliant reports
        """
        query = self.db.query(BiasReport).filter(BiasReport.compliant == False)

        if severity:
            query = query.filter(BiasReport.severity == severity)
        if hours:
            since = datetime.utcnow() - timedelta(hours=hours)
            query = query.filter(BiasReport.created_at >= since)

        return query.order_by(desc(BiasReport.created_at)).all()

    def get_by_fairness_threshold(
        self,
        threshold: float,
        below: bool = True
    ) -> List[BiasReport]:
        """
        Get reports based on fairness score threshold.

        Args:
            threshold: Fairness score threshold (0-1)
            below: If True, get scores below threshold; if False, above

        Returns:
            List of bias reports
        """
        if below:
            query = self.db.query(BiasReport).filter(
                BiasReport.overall_fairness_score < threshold
            )
        else:
            query = self.db.query(BiasReport).filter(
                BiasReport.overall_fairness_score >= threshold
            )

        return query.order_by(BiasReport.overall_fairness_score).all()

    def get_reports_by_attribute(
        self,
        protected_attribute: str,
        limit: int = 50
    ) -> List[BiasReport]:
        """Get reports that analyzed a specific protected attribute."""
        # Use JSON contains for PostgreSQL or filter in Python for SQLite
        return (
            self.db.query(BiasReport)
            .filter(BiasReport.protected_attributes.contains([protected_attribute]))
            .order_by(desc(BiasReport.created_at))
            .limit(limit)
            .all()
        )

    def get_critical_severity_reports(
        self,
        hours: int = 24
    ) -> List[BiasReport]:
        """Get critical severity reports from last N hours."""
        since = datetime.utcnow() - timedelta(hours=hours)
        return (
            self.db.query(BiasReport)
            .filter(BiasReport.severity == 'critical')
            .filter(BiasReport.created_at >= since)
            .order_by(desc(BiasReport.created_at))
            .all()
        )

    def get_report_stats(
        self,
        model_id: Optional[str] = None,
        hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about bias reports.

        Args:
            model_id: Optional model filter
            hours: Optional time range

        Returns:
            Dictionary with statistics
        """
        query = self.db.query(BiasReport)

        if model_id:
            query = query.filter(BiasReport.model_id == model_id)
        if hours:
            since = datetime.utcnow() - timedelta(hours=hours)
            query = query.filter(BiasReport.created_at >= since)

        total_count = query.count()
        compliant_count = query.filter(BiasReport.compliant == True).count()

        # Average fairness score
        avg_fairness = query.with_entities(
            func.avg(BiasReport.overall_fairness_score)
        ).scalar() or 0

        # Count by severity
        severity_counts = (
            query.with_entities(
                BiasReport.severity,
                func.count(BiasReport.report_id).label('count')
            )
            .group_by(BiasReport.severity)
            .all()
        )

        # Compliance rate
        compliance_rate = (compliant_count / total_count * 100) if total_count > 0 else 0

        return {
            'total_reports': total_count,
            'compliant_count': compliant_count,
            'non_compliant_count': total_count - compliant_count,
            'compliance_rate': round(compliance_rate, 2),
            'avg_fairness_score': round(float(avg_fairness), 3),
            'by_severity': {s: c for s, c in severity_counts},
            'unique_models': query.with_entities(
                func.count(func.distinct(BiasReport.model_id))
            ).scalar()
        }

    def get_trending_issues(
        self,
        hours: int = 168,  # 1 week
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get most common bias issues detected.

        Args:
            hours: Time range in hours
            top_n: Number of top issues to return

        Returns:
            List of issues with counts
        """
        since = datetime.utcnow() - timedelta(hours=hours)
        reports = (
            self.db.query(BiasReport)
            .filter(BiasReport.created_at >= since)
            .filter(BiasReport.issues_detected.isnot(None))
            .all()
        )

        # Aggregate issues
        issue_counts: Dict[str, int] = {}
        for report in reports:
            if report.issues_detected:
                for issue in report.issues_detected:
                    issue_counts[issue] = issue_counts.get(issue, 0) + 1

        # Sort and return top N
        sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {'issue': issue, 'count': count}
            for issue, count in sorted_issues[:top_n]
        ]

    def update(self, report_id: str, updates: Dict[str, Any]) -> Optional[BiasReport]:
        """Update a bias report."""
        report = self.get_by_id(report_id)
        if report:
            for key, value in updates.items():
                if hasattr(report, key):
                    setattr(report, key, value)
            self.db.commit()
            self.db.refresh(report)
        return report

    def delete(self, report_id: str) -> bool:
        """Delete a bias report."""
        report = self.get_by_id(report_id)
        if report:
            self.db.delete(report)
            self.db.commit()
            return True
        return False

    def delete_old_reports(self, days_to_keep: int = 365) -> int:
        """
        Delete reports older than specified days.

        Args:
            days_to_keep: Number of days to retain

        Returns:
            Number of deleted reports
        """
        cutoff = datetime.utcnow() - timedelta(days=days_to_keep)
        count = (
            self.db.query(BiasReport)
            .filter(BiasReport.created_at < cutoff)
            .delete()
        )
        self.db.commit()
        return count

    def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: str = 'created_at'
    ) -> List[BiasReport]:
        """List all reports with pagination."""
        query = self.db.query(BiasReport)

        if order_by == 'created_at':
            query = query.order_by(desc(BiasReport.created_at))
        elif order_by == 'fairness_score':
            query = query.order_by(BiasReport.overall_fairness_score)

        return query.offset(skip).limit(limit).all()
