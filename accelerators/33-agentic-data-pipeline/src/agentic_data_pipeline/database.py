"""
Database models and operations for storing pipeline generations.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models import PipelineOutput, SavedGeneration

logger = logging.getLogger(__name__)

Base = declarative_base()


class GenerationRecord(Base):
    """Database model for saved pipeline generations."""

    __tablename__ = "generations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt = Column(Text, nullable=False)
    pipeline_output = Column(Text, nullable=False)  # JSON
    config = Column(Text, nullable=False)  # JSON
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    user_rating = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    generation_time_seconds = Column(Float, nullable=False)

    def to_saved_generation(self) -> SavedGeneration:
        """Convert to SavedGeneration model."""
        return SavedGeneration(
            id=self.id,
            prompt=self.prompt,
            pipeline_output=json.loads(self.pipeline_output),
            config=json.loads(self.config),
            created_at=self.created_at,
            user_rating=self.user_rating,
            feedback=self.feedback,
            tokens_used=self.tokens_used,
            generation_time_seconds=self.generation_time_seconds,
        )


class DatabaseManager:
    """Manage database operations for pipeline generations."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.database_url

        # Ensure data directory exists for SQLite
        if self.database_url.startswith("sqlite"):
            db_path = self.database_url.replace("sqlite:///", "")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

        # Create tables
        Base.metadata.create_all(bind=self.engine)
        logger.info(f"Database initialized at {self.database_url}")

    def get_session(self) -> Session:
        """Get a database session."""
        return self.SessionLocal()

    def save_generation(
        self,
        prompt: str,
        pipeline_output: PipelineOutput,
        config: dict,
        generation_time_seconds: float,
        tokens_used: Optional[int] = None,
    ) -> int:
        """Save a pipeline generation to the database.

        Args:
            prompt: The user's input prompt
            pipeline_output: The generated pipeline output
            config: The configuration used for generation
            generation_time_seconds: Time taken to generate
            tokens_used: Number of tokens used (if available)

        Returns:
            The ID of the saved generation
        """
        session = self.get_session()
        try:
            record = GenerationRecord(
                prompt=prompt,
                pipeline_output=pipeline_output.model_dump_json(),
                config=json.dumps(config),
                generation_time_seconds=generation_time_seconds,
                tokens_used=tokens_used,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            logger.info(f"Saved generation with ID {record.id}")
            return record.id
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save generation: {e}")
            raise
        finally:
            session.close()

    def update_rating(self, generation_id: int, rating: int, feedback: Optional[str] = None) -> None:
        """Update the user rating for a generation.

        Args:
            generation_id: The ID of the generation to update
            rating: Rating from 0-5
            feedback: Optional text feedback
        """
        session = self.get_session()
        try:
            record = session.query(GenerationRecord).filter_by(id=generation_id).first()
            if record:
                record.user_rating = rating
                if feedback:
                    record.feedback = feedback
                session.commit()
                logger.info(f"Updated rating for generation {generation_id}: {rating}/5")
            else:
                logger.warning(f"Generation {generation_id} not found")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update rating: {e}")
            raise
        finally:
            session.close()

    def get_generation(self, generation_id: int) -> Optional[SavedGeneration]:
        """Get a generation by ID.

        Args:
            generation_id: The ID of the generation

        Returns:
            The saved generation or None if not found
        """
        session = self.get_session()
        try:
            record = session.query(GenerationRecord).filter_by(id=generation_id).first()
            if record:
                return record.to_saved_generation()
            return None
        finally:
            session.close()

    def get_recent_generations(self, limit: int = 10) -> List[SavedGeneration]:
        """Get recent generations.

        Args:
            limit: Maximum number of generations to return

        Returns:
            List of saved generations
        """
        session = self.get_session()
        try:
            records = (
                session.query(GenerationRecord)
                .order_by(GenerationRecord.created_at.desc())
                .limit(limit)
                .all()
            )
            return [record.to_saved_generation() for record in records]
        finally:
            session.close()

    def get_highly_rated_generations(self, min_rating: int = 4, limit: int = 10) -> List[SavedGeneration]:
        """Get highly rated generations for RAG.

        Args:
            min_rating: Minimum rating (inclusive)
            limit: Maximum number to return

        Returns:
            List of highly rated generations
        """
        session = self.get_session()
        try:
            records = (
                session.query(GenerationRecord)
                .filter(GenerationRecord.user_rating >= min_rating)
                .order_by(GenerationRecord.user_rating.desc(), GenerationRecord.created_at.desc())
                .limit(limit)
                .all()
            )
            return [record.to_saved_generation() for record in records]
        finally:
            session.close()

    def search_generations(self, search_term: str, limit: int = 10) -> List[SavedGeneration]:
        """Search generations by prompt text.

        Args:
            search_term: Text to search for in prompts
            limit: Maximum number to return

        Returns:
            List of matching generations
        """
        session = self.get_session()
        try:
            records = (
                session.query(GenerationRecord)
                .filter(GenerationRecord.prompt.like(f"%{search_term}%"))
                .order_by(GenerationRecord.created_at.desc())
                .limit(limit)
                .all()
            )
            return [record.to_saved_generation() for record in records]
        finally:
            session.close()

    def get_stats(self) -> dict:
        """Get database statistics.

        Returns:
            Dictionary with stats
        """
        session = self.get_session()
        try:
            total = session.query(GenerationRecord).count()
            rated = session.query(GenerationRecord).filter(GenerationRecord.user_rating.isnot(None)).count()
            avg_rating = (
                session.query(GenerationRecord)
                .filter(GenerationRecord.user_rating.isnot(None))
                .with_entities(GenerationRecord.user_rating)
                .all()
            )

            avg_rating_value = None
            if avg_rating:
                avg_rating_value = sum(r[0] for r in avg_rating) / len(avg_rating)

            return {
                "total_generations": total,
                "rated_generations": rated,
                "average_rating": avg_rating_value,
            }
        finally:
            session.close()


# Global database manager instance
db_manager = DatabaseManager()
