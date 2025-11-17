"""Repository for Deployment data access operations."""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from src.models.deployment import Deployment


class DeploymentRepository:
    """Repository for managing deployment data access."""

    def __init__(self, db: Session):
        """Initialize repository with database session.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def create(self, deployment: Deployment) -> Deployment:
        """Create a new deployment.

        Args:
            deployment: Deployment instance to create

        Returns:
            Created Deployment instance
        """
        self.db.add(deployment)
        self.db.commit()
        self.db.refresh(deployment)
        return deployment

    def get_by_id(self, deployment_id: str) -> Optional[Deployment]:
        """Get deployment by ID.

        Args:
            deployment_id: Deployment identifier

        Returns:
            Deployment instance or None if not found
        """
        return self.db.query(Deployment).filter(
            Deployment.deployment_id == deployment_id
        ).first()

    def get_by_name(self, deployment_name: str) -> Optional[Deployment]:
        """Get deployment by name.

        Args:
            deployment_name: Deployment name

        Returns:
            Deployment instance or None if not found
        """
        return self.db.query(Deployment).filter(
            Deployment.deployment_name == deployment_name
        ).first()

    def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        environment: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Deployment]:
        """List all deployments with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            environment: Filter by environment (optional)
            status: Filter by status (optional)

        Returns:
            List of Deployment instances
        """
        query = self.db.query(Deployment)

        if environment:
            query = query.filter(Deployment.environment == environment)
        if status:
            query = query.filter(Deployment.status == status)

        return query.order_by(desc(Deployment.created_at)).offset(skip).limit(limit).all()

    def get_by_model(self, model_id: str) -> List[Deployment]:
        """Get all deployments for a specific model.

        Args:
            model_id: Model identifier

        Returns:
            List of Deployment instances
        """
        return self.db.query(Deployment).filter(
            Deployment.model_id == model_id
        ).order_by(desc(Deployment.created_at)).all()

    def get_active_deployments(
        self,
        environment: Optional[str] = None
    ) -> List[Deployment]:
        """Get all active/running deployments.

        Args:
            environment: Filter by environment (optional)

        Returns:
            List of active Deployment instances
        """
        query = self.db.query(Deployment).filter(
            Deployment.status.in_(['running', 'healthy'])
        )

        if environment:
            query = query.filter(Deployment.environment == environment)

        return query.order_by(desc(Deployment.deployed_at)).all()

    def get_by_environment(self, environment: str) -> List[Deployment]:
        """Get all deployments in a specific environment.

        Args:
            environment: Environment name (dev, staging, production)

        Returns:
            List of Deployment instances
        """
        return self.db.query(Deployment).filter(
            Deployment.environment == environment
        ).order_by(desc(Deployment.created_at)).all()

    def get_production_deployments(self) -> List[Deployment]:
        """Get all production deployments.

        Returns:
            List of production Deployment instances
        """
        return self.get_by_environment('production')

    def get_by_strategy(self, strategy: str) -> List[Deployment]:
        """Get deployments by deployment strategy.

        Args:
            strategy: Deployment strategy (blue_green, canary, rolling, shadow)

        Returns:
            List of Deployment instances
        """
        return self.db.query(Deployment).filter(
            Deployment.strategy == strategy
        ).order_by(desc(Deployment.created_at)).all()

    def get_unhealthy_deployments(self) -> List[Deployment]:
        """Get all deployments with unhealthy status.

        Returns:
            List of unhealthy Deployment instances
        """
        return self.db.query(Deployment).filter(
            Deployment.health_status.in_(['unhealthy', 'degraded', 'unknown'])
        ).order_by(desc(Deployment.last_health_check)).all()

    def get_canary_deployments(self, model_id: Optional[str] = None) -> List[Deployment]:
        """Get all canary deployments.

        Args:
            model_id: Filter by model ID (optional)

        Returns:
            List of canary Deployment instances
        """
        query = self.db.query(Deployment).filter(
            and_(
                Deployment.strategy == 'canary',
                Deployment.traffic_percentage < 100,
                Deployment.status == 'running'
            )
        )

        if model_id:
            query = query.filter(Deployment.model_id == model_id)

        return query.order_by(desc(Deployment.deployed_at)).all()

    def update(self, deployment_id: str, updates: Dict[str, Any]) -> Optional[Deployment]:
        """Update deployment attributes.

        Args:
            deployment_id: Deployment identifier
            updates: Dictionary of attributes to update

        Returns:
            Updated Deployment instance or None if not found
        """
        deployment = self.get_by_id(deployment_id)
        if not deployment:
            return None

        for key, value in updates.items():
            if hasattr(deployment, key):
                setattr(deployment, key, value)

        deployment.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(deployment)
        return deployment

    def update_status(self, deployment_id: str, status: str) -> Optional[Deployment]:
        """Update deployment status.

        Args:
            deployment_id: Deployment identifier
            status: New status

        Returns:
            Updated Deployment instance or None if not found
        """
        return self.update(deployment_id, {"status": status})

    def update_health_status(
        self,
        deployment_id: str,
        health_status: str
    ) -> Optional[Deployment]:
        """Update deployment health status.

        Args:
            deployment_id: Deployment identifier
            health_status: New health status

        Returns:
            Updated Deployment instance or None if not found
        """
        return self.update(deployment_id, {
            "health_status": health_status,
            "last_health_check": datetime.utcnow()
        })

    def update_traffic_percentage(
        self,
        deployment_id: str,
        traffic_percentage: int
    ) -> Optional[Deployment]:
        """Update traffic percentage for canary deployment.

        Args:
            deployment_id: Deployment identifier
            traffic_percentage: Traffic percentage (0-100)

        Returns:
            Updated Deployment instance or None if not found
        """
        if not 0 <= traffic_percentage <= 100:
            raise ValueError("Traffic percentage must be between 0 and 100")

        return self.update(deployment_id, {"traffic_percentage": traffic_percentage})

    def increment_request_count(
        self,
        deployment_id: str,
        count: int = 1
    ) -> Optional[Deployment]:
        """Increment request count for a deployment.

        Args:
            deployment_id: Deployment identifier
            count: Number to increment by

        Returns:
            Updated Deployment instance or None if not found
        """
        deployment = self.get_by_id(deployment_id)
        if not deployment:
            return None

        deployment.request_count = (deployment.request_count or 0) + count
        deployment.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(deployment)
        return deployment

    def increment_error_count(
        self,
        deployment_id: str,
        count: int = 1
    ) -> Optional[Deployment]:
        """Increment error count for a deployment.

        Args:
            deployment_id: Deployment identifier
            count: Number to increment by

        Returns:
            Updated Deployment instance or None if not found
        """
        deployment = self.get_by_id(deployment_id)
        if not deployment:
            return None

        deployment.error_count = (deployment.error_count or 0) + count
        deployment.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(deployment)
        return deployment

    def update_metrics(
        self,
        deployment_id: str,
        request_count: Optional[int] = None,
        error_count: Optional[int] = None,
        avg_latency_ms: Optional[int] = None
    ) -> Optional[Deployment]:
        """Update deployment metrics.

        Args:
            deployment_id: Deployment identifier
            request_count: Total request count (optional)
            error_count: Total error count (optional)
            avg_latency_ms: Average latency in milliseconds (optional)

        Returns:
            Updated Deployment instance or None if not found
        """
        updates = {}
        if request_count is not None:
            updates["request_count"] = request_count
        if error_count is not None:
            updates["error_count"] = error_count
        if avg_latency_ms is not None:
            updates["avg_latency_ms"] = avg_latency_ms

        return self.update(deployment_id, updates)

    def delete(self, deployment_id: str) -> bool:
        """Delete a deployment.

        Args:
            deployment_id: Deployment identifier

        Returns:
            True if deleted, False if not found
        """
        deployment = self.get_by_id(deployment_id)
        if not deployment:
            return False

        self.db.delete(deployment)
        self.db.commit()
        return True

    def count_by_environment(self) -> Dict[str, int]:
        """Get count of deployments grouped by environment.

        Returns:
            Dictionary mapping environment to count
        """
        results = self.db.query(
            Deployment.environment,
            func.count(Deployment.deployment_id).label('count')
        ).group_by(Deployment.environment).all()

        return {environment: count for environment, count in results}

    def count_by_status(self) -> Dict[str, int]:
        """Get count of deployments grouped by status.

        Returns:
            Dictionary mapping status to count
        """
        results = self.db.query(
            Deployment.status,
            func.count(Deployment.deployment_id).label('count')
        ).group_by(Deployment.status).all()

        return {status: count for status, count in results}

    def get_deployment_stats(self, deployment_id: str) -> Optional[Dict[str, Any]]:
        """Get deployment statistics.

        Args:
            deployment_id: Deployment identifier

        Returns:
            Dictionary with deployment stats or None if not found
        """
        deployment = self.get_by_id(deployment_id)
        if not deployment:
            return None

        error_rate = 0.0
        if deployment.request_count and deployment.request_count > 0:
            error_rate = (deployment.error_count or 0) / deployment.request_count * 100

        return {
            "deployment_id": deployment.deployment_id,
            "deployment_name": deployment.deployment_name,
            "status": deployment.status,
            "health_status": deployment.health_status,
            "request_count": deployment.request_count or 0,
            "error_count": deployment.error_count or 0,
            "error_rate_percentage": round(error_rate, 2),
            "avg_latency_ms": deployment.avg_latency_ms,
            "traffic_percentage": deployment.traffic_percentage,
            "replicas": deployment.replicas,
            "uptime_hours": self._calculate_uptime(deployment),
        }

    def _calculate_uptime(self, deployment: Deployment) -> Optional[float]:
        """Calculate deployment uptime in hours.

        Args:
            deployment: Deployment instance

        Returns:
            Uptime in hours or None if not deployed
        """
        if not deployment.deployed_at:
            return None

        uptime = datetime.utcnow() - deployment.deployed_at
        return round(uptime.total_seconds() / 3600, 2)

    def get_deployments_needing_health_check(
        self,
        minutes_since_last_check: int = 5
    ) -> List[Deployment]:
        """Get deployments that need a health check.

        Args:
            minutes_since_last_check: Minutes since last health check

        Returns:
            List of Deployment instances needing health check
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes_since_last_check)

        return self.db.query(Deployment).filter(
            and_(
                Deployment.status == 'running',
                or_(
                    Deployment.last_health_check.is_(None),
                    Deployment.last_health_check < cutoff_time
                )
            )
        ).all()
