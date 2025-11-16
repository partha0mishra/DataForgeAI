"""Database utilities and connection management."""

from typing import Optional, Any, Dict
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from .logging import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Manage database connections and sessions."""

    def __init__(
        self,
        connection_string: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        echo: bool = False,
    ):
        """Initialize database manager.

        Args:
            connection_string: Database connection string
            pool_size: Connection pool size
            max_overflow: Maximum overflow connections
            pool_timeout: Pool timeout in seconds
            echo: Echo SQL statements
        """
        self.engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            echo=echo,
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

        logger.info(f"Database manager initialized with pool_size={pool_size}")

    @contextmanager
    def session(self):
        """Get database session context manager.

        Yields:
            Database session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()

    def get_session(self) -> Session:
        """Get new database session.

        Returns:
            Database session
        """
        return self.SessionLocal()

    def dispose(self):
        """Dispose of connection pool."""
        self.engine.dispose()
        logger.info("Database connection pool disposed")


# Global database manager
_db_manager: Optional[DatabaseManager] = None


def init_database(connection_string: str, **kwargs):
    """Initialize global database manager.

    Args:
        connection_string: Database connection string
        **kwargs: Additional arguments for DatabaseManager
    """
    global _db_manager
    _db_manager = DatabaseManager(connection_string, **kwargs)


def get_database() -> Optional[DatabaseManager]:
    """Get global database manager.

    Returns:
        Database manager instance or None
    """
    return _db_manager


@contextmanager
def get_db_session():
    """Get database session from global manager.

    Yields:
        Database session
    """
    if not _db_manager:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    with _db_manager.session() as session:
        yield session
