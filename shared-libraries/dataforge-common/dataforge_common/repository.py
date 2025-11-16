"""Repository pattern for database operations."""

from datetime import datetime
from typing import Generic, List, Optional, Type, TypeVar, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.orm import Session
from contextlib import contextmanager

from .models import Base, UserModel, RoleModel, AuditEventModel, SessionModel, APIKeyModel
from .database import DatabaseManager, get_database_manager
from .logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T', bound=Base)


class BaseRepository(Generic[T]):
    """Base repository for CRUD operations."""

    def __init__(self, model: Type[T], db_manager: Optional[DatabaseManager] = None):
        """Initialize repository.

        Args:
            model: SQLAlchemy model class
            db_manager: Database manager instance
        """
        self.model = model
        self.db_manager = db_manager or get_database_manager()

    @contextmanager
    def _session(self):
        """Get database session context."""
        with self.db_manager.session() as session:
            yield session

    def create(self, **kwargs) -> T:
        """Create a new record.

        Args:
            **kwargs: Model attributes

        Returns:
            Created model instance
        """
        with self._session() as session:
            instance = self.model(**kwargs)
            session.add(instance)
            session.flush()
            session.refresh(instance)
            return instance

    def get_by_id(self, id_value: Any) -> Optional[T]:
        """Get record by primary key.

        Args:
            id_value: Primary key value

        Returns:
            Model instance or None
        """
        with self._session() as session:
            return session.get(self.model, id_value)

    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """Get all records.

        Args:
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            List of model instances
        """
        with self._session() as session:
            stmt = select(self.model).offset(offset)
            if limit:
                stmt = stmt.limit(limit)
            return list(session.scalars(stmt).all())

    def filter_by(self, **kwargs) -> List[T]:
        """Filter records by attributes.

        Args:
            **kwargs: Filter criteria

        Returns:
            List of matching model instances
        """
        with self._session() as session:
            stmt = select(self.model).filter_by(**kwargs)
            return list(session.scalars(stmt).all())

    def update(self, id_value: Any, **kwargs) -> Optional[T]:
        """Update a record.

        Args:
            id_value: Primary key value
            **kwargs: Attributes to update

        Returns:
            Updated model instance or None
        """
        with self._session() as session:
            instance = session.get(self.model, id_value)
            if instance:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
                session.flush()
                session.refresh(instance)
            return instance

    def delete(self, id_value: Any) -> bool:
        """Delete a record.

        Args:
            id_value: Primary key value

        Returns:
            True if deleted, False if not found
        """
        with self._session() as session:
            instance = session.get(self.model, id_value)
            if instance:
                session.delete(instance)
                return True
            return False

    def count(self, **kwargs) -> int:
        """Count records.

        Args:
            **kwargs: Optional filter criteria

        Returns:
            Number of matching records
        """
        with self._session() as session:
            stmt = select(self.model)
            if kwargs:
                stmt = stmt.filter_by(**kwargs)
            return session.query(self.model).count()

    def exists(self, **kwargs) -> bool:
        """Check if record exists.

        Args:
            **kwargs: Filter criteria

        Returns:
            True if exists
        """
        return self.count(**kwargs) > 0


class UserRepository(BaseRepository[UserModel]):
    """Repository for user operations."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        super().__init__(UserModel, db_manager)

    def get_by_username(self, username: str) -> Optional[UserModel]:
        """Get user by username.

        Args:
            username: Username

        Returns:
            User model or None
        """
        results = self.filter_by(username=username)
        return results[0] if results else None

    def get_by_email(self, email: str) -> Optional[UserModel]:
        """Get user by email.

        Args:
            email: Email address

        Returns:
            User model or None
        """
        results = self.filter_by(email=email)
        return results[0] if results else None

    def update_last_login(self, user_id: str) -> None:
        """Update user's last login time.

        Args:
            user_id: User ID
        """
        self.update(user_id, last_login=datetime.utcnow())

    def get_active_users(self) -> List[UserModel]:
        """Get all active users.

        Returns:
            List of active users
        """
        return self.filter_by(is_active=True)

    def add_role(self, user_id: str, role: RoleModel) -> None:
        """Add role to user.

        Args:
            user_id: User ID
            role: Role model
        """
        with self._session() as session:
            user = session.get(UserModel, user_id)
            if user and role not in user.roles:
                user.roles.append(role)
                session.flush()

    def remove_role(self, user_id: str, role: RoleModel) -> None:
        """Remove role from user.

        Args:
            user_id: User ID
            role: Role model
        """
        with self._session() as session:
            user = session.get(UserModel, user_id)
            if user and role in user.roles:
                user.roles.remove(role)
                session.flush()


class RoleRepository(BaseRepository[RoleModel]):
    """Repository for role operations."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        super().__init__(RoleModel, db_manager)

    def get_by_name(self, name: str) -> Optional[RoleModel]:
        """Get role by name.

        Args:
            name: Role name

        Returns:
            Role model or None
        """
        results = self.filter_by(name=name)
        return results[0] if results else None

    def ensure_default_roles(self) -> None:
        """Ensure default roles exist."""
        default_roles = [
            ("user", "Standard user role"),
            ("admin", "Administrator role"),
            ("analyst", "Data analyst role"),
            ("developer", "Developer role"),
        ]

        for role_name, description in default_roles:
            if not self.get_by_name(role_name):
                self.create(
                    role_id=f"role_{role_name}",
                    name=role_name,
                    description=description,
                )
                logger.info(f"Created default role: {role_name}")


class AuditEventRepository(BaseRepository[AuditEventModel]):
    """Repository for audit event operations."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        super().__init__(AuditEventModel, db_manager)

    def get_by_user(self, user_id: str, limit: int = 100) -> List[AuditEventModel]:
        """Get audit events for user.

        Args:
            user_id: User ID
            limit: Maximum events to return

        Returns:
            List of audit events
        """
        with self._session() as session:
            stmt = (
                select(AuditEventModel)
                .filter_by(user_id=user_id)
                .order_by(AuditEventModel.timestamp.desc())
                .limit(limit)
            )
            return list(session.scalars(stmt).all())

    def get_by_resource(self, resource_type: str, resource_id: str, limit: int = 100) -> List[AuditEventModel]:
        """Get audit events for resource.

        Args:
            resource_type: Resource type
            resource_id: Resource ID
            limit: Maximum events to return

        Returns:
            List of audit events
        """
        with self._session() as session:
            stmt = (
                select(AuditEventModel)
                .filter_by(resource_type=resource_type, resource_id=resource_id)
                .order_by(AuditEventModel.timestamp.desc())
                .limit(limit)
            )
            return list(session.scalars(stmt).all())

    def get_recent(self, limit: int = 100) -> List[AuditEventModel]:
        """Get recent audit events.

        Args:
            limit: Maximum events to return

        Returns:
            List of audit events
        """
        with self._session() as session:
            stmt = (
                select(AuditEventModel)
                .order_by(AuditEventModel.timestamp.desc())
                .limit(limit)
            )
            return list(session.scalars(stmt).all())


class SessionRepository(BaseRepository[SessionModel]):
    """Repository for session operations."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        super().__init__(SessionModel, db_manager)

    def get_by_refresh_token(self, refresh_token: str) -> Optional[SessionModel]:
        """Get session by refresh token.

        Args:
            refresh_token: Refresh token

        Returns:
            Session model or None
        """
        results = self.filter_by(refresh_token=refresh_token, is_active=True)
        return results[0] if results else None

    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session.

        Args:
            session_id: Session ID

        Returns:
            True if invalidated
        """
        return bool(self.update(session_id, is_active=False))

    def invalidate_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for user.

        Args:
            user_id: User ID

        Returns:
            Number of sessions invalidated
        """
        with self._session() as session:
            stmt = (
                update(SessionModel)
                .where(SessionModel.user_id == user_id, SessionModel.is_active == True)
                .values(is_active=False)
            )
            result = session.execute(stmt)
            return result.rowcount

    def cleanup_expired_sessions(self) -> int:
        """Delete expired sessions.

        Returns:
            Number of sessions deleted
        """
        with self._session() as session:
            stmt = delete(SessionModel).where(SessionModel.expires_at < datetime.utcnow())
            result = session.execute(stmt)
            return result.rowcount
