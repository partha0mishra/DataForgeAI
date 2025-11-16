"""Data classification and sensitivity tagging."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List
import pandas as pd
from dataforge_common.logging import get_logger

logger = get_logger(__name__)


class DataClassification(Enum):
    """Data classification levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


@dataclass
class ClassificationRule:
    """Rule for classifying data."""
    name: str
    classification: DataClassification
    column_patterns: List[str] = field(default_factory=list)
    content_patterns: List[str] = field(default_factory=list)


class DataClassifier:
    """Classify data by sensitivity level."""

    def __init__(self):
        """Initialize classifier."""
        self.rules = self._build_default_rules()

    def _build_default_rules(self) -> List[ClassificationRule]:
        """Build default classification rules."""
        return [
            ClassificationRule(
                name="PII Data",
                classification=DataClassification.RESTRICTED,
                column_patterns=["ssn", "social_security", "credit_card", "password"],
                content_patterns=["\\d{3}-\\d{2}-\\d{4}"],
            ),
            ClassificationRule(
                name="Contact Information",
                classification=DataClassification.CONFIDENTIAL,
                column_patterns=["email", "phone", "address"],
            ),
            ClassificationRule(
                name="Financial Data",
                classification=DataClassification.CONFIDENTIAL,
                column_patterns=["salary", "revenue", "payment", "invoice"],
            ),
            ClassificationRule(
                name="Public Data",
                classification=DataClassification.PUBLIC,
                column_patterns=["id", "name", "title", "department"],
            ),
        ]

    def classify_dataframe(
        self,
        df: pd.DataFrame,
    ) -> Dict[str, DataClassification]:
        """Classify DataFrame columns.

        Args:
            df: DataFrame to classify

        Returns:
            Dictionary mapping column names to classifications
        """
        classifications = {}

        for column in df.columns:
            classification = self._classify_column(column, df[column])
            classifications[column] = classification

        logger.info(f"Classified {len(df.columns)} columns")

        return classifications

    def _classify_column(
        self,
        column_name: str,
        column_data: pd.Series,
    ) -> DataClassification:
        """Classify a single column."""
        column_lower = column_name.lower()

        # Check rules in priority order
        for rule in self.rules:
            # Check column name patterns
            for pattern in rule.column_patterns:
                if pattern.lower() in column_lower:
                    return rule.classification

        # Default to internal
        return DataClassification.INTERNAL
