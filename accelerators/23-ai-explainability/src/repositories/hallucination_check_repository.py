"""Repository for HallucinationCheck model."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
import hashlib

from src.models.hallucination_check import HallucinationCheck


class HallucinationCheckRepository:
    """Repository for managing hallucination checks."""

    def __init__(self, db: Session):
        """Initialize repository with database session."""
        self.db = db

    @staticmethod
    def generate_prompt_hash(prompt: str) -> str:
        """Generate hash for prompt deduplication."""
        return hashlib.sha256(prompt.encode()).hexdigest()

    def create(self, check_data: Dict[str, Any]) -> HallucinationCheck:
        """Create a new hallucination check."""
        # Generate prompt hash if not provided
        if 'prompt_hash' not in check_data and 'prompt' in check_data:
            check_data['prompt_hash'] = self.generate_prompt_hash(check_data['prompt'])

        check = HallucinationCheck(**check_data)
        self.db.add(check)
        self.db.commit()
        self.db.refresh(check)
        return check

    def get_by_id(self, check_id: str) -> Optional[HallucinationCheck]:
        """Get hallucination check by ID."""
        return self.db.query(HallucinationCheck).filter(
            HallucinationCheck.check_id == check_id
        ).first()

    def get_by_model(
        self,
        model_name: str,
        model_version: Optional[str] = None,
        limit: int = 100
    ) -> List[HallucinationCheck]:
        """Get hallucination checks for a model."""
        query = self.db.query(HallucinationCheck).filter(
            HallucinationCheck.model_name == model_name
        )

        if model_version:
            query = query.filter(HallucinationCheck.model_version == model_version)

        return query.order_by(desc(HallucinationCheck.created_at)).limit(limit).all()

    def get_by_prompt_hash(self, prompt_hash: str) -> List[HallucinationCheck]:
        """Get checks for the same prompt (by hash)."""
        return (
            self.db.query(HallucinationCheck)
            .filter(HallucinationCheck.prompt_hash == prompt_hash)
            .order_by(desc(HallucinationCheck.created_at))
            .all()
        )

    def find_similar_prompt(self, prompt: str) -> Optional[HallucinationCheck]:
        """
        Find if a similar prompt has been checked before.

        Returns most recent check with same prompt hash.
        """
        prompt_hash = self.generate_prompt_hash(prompt)
        return (
            self.db.query(HallucinationCheck)
            .filter(HallucinationCheck.prompt_hash == prompt_hash)
            .order_by(desc(HallucinationCheck.created_at))
            .first()
        )

    def get_hallucinated_outputs(
        self,
        model_name: Optional[str] = None,
        severity: Optional[str] = None,
        hours: Optional[int] = None,
        limit: int = 100
    ) -> List[HallucinationCheck]:
        """
        Get outputs flagged as hallucinated.

        Args:
            model_name: Optional model filter
            severity: Optional severity filter
            hours: Optional time range
            limit: Maximum results

        Returns:
            List of hallucinated checks
        """
        query = self.db.query(HallucinationCheck).filter(
            HallucinationCheck.hallucinated == True
        )

        if model_name:
            query = query.filter(HallucinationCheck.model_name == model_name)
        if severity:
            query = query.filter(HallucinationCheck.severity == severity)
        if hours:
            since = datetime.utcnow() - timedelta(hours=hours)
            query = query.filter(HallucinationCheck.created_at >= since)

        return query.order_by(desc(HallucinationCheck.created_at)).limit(limit).all()

    def get_by_risk_level(
        self,
        risk_level: str,
        model_name: Optional[str] = None,
        limit: int = 100
    ) -> List[HallucinationCheck]:
        """Get checks by hallucination risk level."""
        query = self.db.query(HallucinationCheck).filter(
            HallucinationCheck.hallucination_risk == risk_level
        )

        if model_name:
            query = query.filter(HallucinationCheck.model_name == model_name)

        return query.order_by(desc(HallucinationCheck.created_at)).limit(limit).all()

    def get_high_risk_checks(
        self,
        hours: int = 24,
        model_name: Optional[str] = None
    ) -> List[HallucinationCheck]:
        """Get high and critical risk checks from last N hours."""
        since = datetime.utcnow() - timedelta(hours=hours)
        query = self.db.query(HallucinationCheck).filter(
            HallucinationCheck.created_at >= since,
            HallucinationCheck.hallucination_risk.in_(['high', 'critical'])
        )

        if model_name:
            query = query.filter(HallucinationCheck.model_name == model_name)

        return query.order_by(desc(HallucinationCheck.hallucination_score)).all()

    def get_by_use_case(
        self,
        use_case: str,
        limit: int = 100
    ) -> List[HallucinationCheck]:
        """Get checks for a specific use case."""
        return (
            self.db.query(HallucinationCheck)
            .filter(HallucinationCheck.use_case == use_case)
            .order_by(desc(HallucinationCheck.created_at))
            .limit(limit)
            .all()
        )

    def get_by_domain(
        self,
        domain: str,
        limit: int = 100
    ) -> List[HallucinationCheck]:
        """Get checks for a specific domain/topic."""
        return (
            self.db.query(HallucinationCheck)
            .filter(HallucinationCheck.domain == domain)
            .order_by(desc(HallucinationCheck.created_at))
            .limit(limit)
            .all()
        )

    def get_check_stats(
        self,
        model_name: Optional[str] = None,
        hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about hallucination checks.

        Args:
            model_name: Optional model filter
            hours: Optional time range

        Returns:
            Dictionary with statistics
        """
        query = self.db.query(HallucinationCheck)

        if model_name:
            query = query.filter(HallucinationCheck.model_name == model_name)
        if hours:
            since = datetime.utcnow() - timedelta(hours=hours)
            query = query.filter(HallucinationCheck.created_at >= since)

        total_count = query.count()
        hallucinated_count = query.filter(HallucinationCheck.hallucinated == True).count()

        # Average scores
        avg_confidence = query.with_entities(
            func.avg(HallucinationCheck.confidence_score)
        ).scalar() or 0

        avg_hallucination = query.with_entities(
            func.avg(HallucinationCheck.hallucination_score)
        ).scalar() or 0

        avg_grounding = query.with_entities(
            func.avg(HallucinationCheck.grounding_quality)
        ).scalar() or 0

        # Count by risk level
        risk_counts = (
            query.with_entities(
                HallucinationCheck.hallucination_risk,
                func.count(HallucinationCheck.check_id).label('count')
            )
            .group_by(HallucinationCheck.hallucination_risk)
            .all()
        )

        # Count by severity
        severity_counts = (
            query.with_entities(
                HallucinationCheck.severity,
                func.count(HallucinationCheck.check_id).label('count')
            )
            .group_by(HallucinationCheck.severity)
            .all()
        )

        # Hallucination rate
        hallucination_rate = (hallucinated_count / total_count * 100) if total_count > 0 else 0

        return {
            'total_checks': total_count,
            'hallucinated_count': hallucinated_count,
            'hallucination_rate': round(hallucination_rate, 2),
            'avg_confidence_score': round(float(avg_confidence), 3),
            'avg_hallucination_score': round(float(avg_hallucination), 3),
            'avg_grounding_quality': round(float(avg_grounding), 3) if avg_grounding else None,
            'by_risk_level': {risk: count for risk, count in risk_counts},
            'by_severity': {sev: count for sev, count in severity_counts},
            'unique_models': query.with_entities(
                func.count(func.distinct(HallucinationCheck.model_name))
            ).scalar()
        }

    def get_model_reliability(
        self,
        model_name: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get reliability metrics for a model over time.

        Args:
            model_name: Model name
            days: Time period in days

        Returns:
            Dictionary with reliability metrics
        """
        since = datetime.utcnow() - timedelta(days=days)
        checks = (
            self.db.query(HallucinationCheck)
            .filter(HallucinationCheck.model_name == model_name)
            .filter(HallucinationCheck.created_at >= since)
            .all()
        )

        if not checks:
            return {
                'model_name': model_name,
                'period_days': days,
                'total_checks': 0,
                'reliability_score': 0
            }

        total = len(checks)
        hallucinated = sum(1 for c in checks if c.hallucinated)
        avg_confidence = sum(c.confidence_score for c in checks) / total
        avg_hallucination = sum(c.hallucination_score for c in checks) / total

        # Calculate reliability score (inverse of hallucination rate, weighted by confidence)
        reliability_score = (1 - (hallucinated / total)) * avg_confidence

        return {
            'model_name': model_name,
            'period_days': days,
            'total_checks': total,
            'hallucinated_count': hallucinated,
            'hallucination_rate': round((hallucinated / total) * 100, 2),
            'avg_confidence': round(avg_confidence, 3),
            'avg_hallucination_score': round(avg_hallucination, 3),
            'reliability_score': round(reliability_score, 3)
        }

    def get_trending_issues(
        self,
        hours: int = 168,  # 1 week
        top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """Get most common hallucination issues."""
        since = datetime.utcnow() - timedelta(hours=hours)
        checks = (
            self.db.query(HallucinationCheck)
            .filter(HallucinationCheck.created_at >= since)
            .filter(HallucinationCheck.issues_detected.isnot(None))
            .all()
        )

        # Aggregate issues
        issue_counts: Dict[str, int] = {}
        for check in checks:
            if check.issues_detected:
                for issue in check.issues_detected:
                    issue_counts[issue] = issue_counts.get(issue, 0) + 1

        # Sort and return top N
        sorted_issues = sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {'issue': issue, 'count': count}
            for issue, count in sorted_issues[:top_n]
        ]

    def update(self, check_id: str, updates: Dict[str, Any]) -> Optional[HallucinationCheck]:
        """Update a hallucination check."""
        check = self.get_by_id(check_id)
        if check:
            for key, value in updates.items():
                if hasattr(check, key):
                    setattr(check, key, value)
            self.db.commit()
            self.db.refresh(check)
        return check

    def delete(self, check_id: str) -> bool:
        """Delete a hallucination check."""
        check = self.get_by_id(check_id)
        if check:
            self.db.delete(check)
            self.db.commit()
            return True
        return False

    def delete_old_checks(self, days_to_keep: int = 90) -> int:
        """Delete checks older than specified days."""
        cutoff = datetime.utcnow() - timedelta(days=days_to_keep)
        count = (
            self.db.query(HallucinationCheck)
            .filter(HallucinationCheck.created_at < cutoff)
            .delete()
        )
        self.db.commit()
        return count

    def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: str = 'created_at'
    ) -> List[HallucinationCheck]:
        """List all checks with pagination."""
        query = self.db.query(HallucinationCheck)

        if order_by == 'created_at':
            query = query.order_by(desc(HallucinationCheck.created_at))
        elif order_by == 'risk':
            query = query.order_by(desc(HallucinationCheck.hallucination_score))

        return query.offset(skip).limit(limit).all()
