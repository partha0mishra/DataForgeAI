"""PII detection and masking."""

import pandas as pd
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from dataforge_common.logging import get_logger

logger = get_logger(__name__)


class PIIType(Enum):
    """Types of PII data."""
    EMAIL = "email"
    PHONE = "phone"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    NAME = "name"
    ADDRESS = "address"
    DATE_OF_BIRTH = "date_of_birth"


@dataclass
class PIIMatch:
    """A detected PII match."""
    pii_type: PIIType
    column: str
    value: str
    row_index: int
    confidence: float = 1.0


@dataclass
class PIIReport:
    """PII detection report."""
    total_rows: int
    total_columns: int
    pii_columns: List[str] = field(default_factory=list)
    matches: List[PIIMatch] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)


class PIIDetector:
    """Detect PII in datasets."""

    def __init__(self):
        """Initialize PII detector."""
        self.patterns = self._build_patterns()

    def _build_patterns(self) -> Dict[PIIType, str]:
        """Build regex patterns for PII detection."""
        return {
            PIIType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            PIIType.PHONE: r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            PIIType.SSN: r'\b\d{3}-\d{2}-\d{4}\b',
            PIIType.CREDIT_CARD: r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            PIIType.IP_ADDRESS: r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        }

    def scan_dataframe(
        self,
        df: pd.DataFrame,
        sample_size: int = 1000,
    ) -> PIIReport:
        """Scan DataFrame for PII.

        Args:
            df: DataFrame to scan
            sample_size: Number of rows to sample

        Returns:
            PIIReport with findings
        """
        logger.info(f"Scanning DataFrame with {len(df)} rows, {len(df.columns)} columns")

        # Sample if dataset is large
        if len(df) > sample_size:
            sample_df = df.sample(n=sample_size)
        else:
            sample_df = df

        matches = []
        pii_columns = set()

        # Scan each column
        for column in sample_df.columns:
            column_matches = self._scan_column(sample_df, column)
            matches.extend(column_matches)
            if column_matches:
                pii_columns.add(column)

        # Create summary
        summary = {}
        for match in matches:
            pii_type = match.pii_type.value
            summary[pii_type] = summary.get(pii_type, 0) + 1

        report = PIIReport(
            total_rows=len(df),
            total_columns=len(df.columns),
            pii_columns=list(pii_columns),
            matches=matches[:100],  # Limit to first 100
            summary=summary,
        )

        logger.info(f"Found PII in {len(pii_columns)} columns: {pii_columns}")

        return report

    def _scan_column(
        self,
        df: pd.DataFrame,
        column: str,
    ) -> List[PIIMatch]:
        """Scan a single column for PII."""
        matches = []

        # Convert column to string
        column_data = df[column].astype(str)

        for pii_type, pattern in self.patterns.items():
            for idx, value in enumerate(column_data):
                if pd.isna(value) or value == 'nan':
                    continue

                if re.search(pattern, value):
                    matches.append(PIIMatch(
                        pii_type=pii_type,
                        column=column,
                        value=value,
                        row_index=idx,
                        confidence=0.9,
                    ))
                    break  # Found PII, no need to check other types

        return matches

    def mask_dataframe(
        self,
        df: pd.DataFrame,
        strategy: str = "redact",
    ) -> pd.DataFrame:
        """Mask PII in DataFrame.

        Args:
            df: DataFrame to mask
            strategy: Masking strategy (redact, hash, tokenize)

        Returns:
            Masked DataFrame
        """
        logger.info(f"Masking DataFrame with strategy: {strategy}")

        masked_df = df.copy()

        # Scan for PII
        report = self.scan_dataframe(df)

        # Mask PII columns
        for column in report.pii_columns:
            if strategy == "redact":
                masked_df[column] = "[REDACTED]"
            elif strategy == "hash":
                masked_df[column] = masked_df[column].apply(
                    lambda x: f"HASH_{hash(str(x)) % 10000:04d}"
                )
            elif strategy == "tokenize":
                masked_df[column] = masked_df[column].apply(
                    lambda x: f"TOKEN_{masked_df.index.get_loc(masked_df[masked_df[column] == x].index[0]) if x in masked_df[column].values else 0:04d}"
                )

        logger.info(f"Masked {len(report.pii_columns)} columns")

        return masked_df
