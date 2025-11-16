"""PII (Personally Identifiable Information) Detection."""

import re
from typing import Dict, List, Optional, Set

import pandas as pd

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


class PIIDetector:
    """
    Detect and mask Personally Identifiable Information (PII).

    Supports detection of:
    - Email addresses
    - Phone numbers
    - Social Security Numbers (SSN)
    - Credit card numbers
    - IP addresses
    - Custom patterns

    Example:
        detector = PIIDetector()

        # Detect PII in DataFrame
        pii_found = detector.detect_in_dataframe(df)

        # Mask PII
        masked_df = detector.mask_pii(df)

        # Get PII report
        report = detector.generate_report(df)
    """

    # Regex patterns for common PII types
    PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        "ip_address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "zip_code": r"\b\d{5}(?:-\d{4})?\b",
    }

    def __init__(self, custom_patterns: Optional[Dict[str, str]] = None):
        """
        Initialize PII detector.

        Args:
            custom_patterns: Additional patterns to detect (name -> regex)
        """
        self.patterns = self.PATTERNS.copy()

        if custom_patterns:
            self.patterns.update(custom_patterns)

        self.logger = logger
        self.logger.info("PII detector initialized", pattern_count=len(self.patterns))

    def detect_in_text(self, text: str) -> Dict[str, List[str]]:
        """
        Detect PII in text string.

        Args:
            text: Text to scan for PII

        Returns:
            dict: PII type -> list of matches
        """
        if not isinstance(text, str):
            return {}

        results = {}

        for pii_type, pattern in self.patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                results[pii_type] = matches

        return results

    def detect_in_dataframe(self, df: pd.DataFrame) -> Dict[str, Dict[str, int]]:
        """
        Detect PII in DataFrame.

        Args:
            df: DataFrame to scan

        Returns:
            dict: Column -> {PII type -> count}
        """
        self.logger.info("Scanning DataFrame for PII", rows=len(df), columns=len(df.columns))

        results = {}

        for column in df.columns:
            # Only scan string columns
            if df[column].dtype == "object":
                column_results = {}

                for pii_type, pattern in self.patterns.items():
                    # Count matches in column
                    matches = df[column].astype(str).str.contains(pattern, regex=True, na=False)
                    count = matches.sum()

                    if count > 0:
                        column_results[pii_type] = int(count)

                if column_results:
                    results[column] = column_results

        total_pii = sum(sum(v.values()) for v in results.values())

        self.logger.info(
            "PII detection complete",
            columns_with_pii=len(results),
            total_matches=total_pii,
        )

        return results

    def mask_pii(
        self,
        df: pd.DataFrame,
        mask_char: str = "*",
        preserve_format: bool = True,
    ) -> pd.DataFrame:
        """
        Mask PII in DataFrame.

        Args:
            df: DataFrame to mask
            mask_char: Character to use for masking
            preserve_format: Preserve format of original data

        Returns:
            DataFrame with PII masked
        """
        self.logger.info("Masking PII in DataFrame")

        masked_df = df.copy()

        for column in masked_df.columns:
            if masked_df[column].dtype == "object":
                for pii_type, pattern in self.patterns.items():
                    if preserve_format:
                        # Preserve format (e.g., email -> ****@***.com)
                        masked_df[column] = masked_df[column].astype(str).str.replace(
                            pattern,
                            self._get_mask_replacement(pii_type, mask_char),
                            regex=True,
                        )
                    else:
                        # Simple masking
                        masked_df[column] = masked_df[column].astype(str).str.replace(
                            pattern, mask_char * 10, regex=True
                        )

        return masked_df

    def _get_mask_replacement(self, pii_type: str, mask_char: str) -> str:
        """Get appropriate mask replacement for PII type."""
        masks = {
            "email": f"{mask_char * 4}@{mask_char * 3}.com",
            "phone": f"{mask_char * 3}-{mask_char * 3}-{mask_char * 4}",
            "ssn": f"{mask_char * 3}-{mask_char * 2}-{mask_char * 4}",
            "credit_card": f"{mask_char * 4} {mask_char * 4} {mask_char * 4} {mask_char * 4}",
            "ip_address": f"{mask_char * 3}.{mask_char * 3}.{mask_char * 3}.{mask_char * 3}",
        }

        return masks.get(pii_type, mask_char * 10)

    def generate_report(self, df: pd.DataFrame) -> Dict[str, any]:
        """
        Generate PII detection report.

        Args:
            df: DataFrame to analyze

        Returns:
            dict: Detailed PII report
        """
        pii_detected = self.detect_in_dataframe(df)

        report = {
            "dataset_info": {
                "total_rows": len(df),
                "total_columns": len(df.columns),
            },
            "pii_summary": {
                "columns_with_pii": len(pii_detected),
                "total_pii_instances": sum(sum(v.values()) for v in pii_detected.values()),
            },
            "pii_by_column": pii_detected,
            "recommendations": self._generate_recommendations(pii_detected),
        }

        return report

    def _generate_recommendations(
        self, pii_detected: Dict[str, Dict[str, int]]
    ) -> List[str]:
        """Generate recommendations based on PII found."""
        recommendations = []

        if pii_detected:
            recommendations.append("PII detected - consider data masking or anonymization")
            recommendations.append("Implement access controls for columns with PII")
            recommendations.append("Enable audit logging for PII access")
            recommendations.append("Review data retention policies")

            # Specific recommendations by PII type
            all_pii_types = set()
            for column_pii in pii_detected.values():
                all_pii_types.update(column_pii.keys())

            if "ssn" in all_pii_types or "credit_card" in all_pii_types:
                recommendations.append("High-risk PII found - encryption at rest required")

            if "email" in all_pii_types:
                recommendations.append("Consider email hashing for analytics use cases")

        return recommendations
