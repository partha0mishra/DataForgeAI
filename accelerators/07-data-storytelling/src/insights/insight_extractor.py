"""Insight extraction from data using statistical analysis."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from dataforge_common.logging import get_logger

logger = get_logger(__name__)


class InsightType(str, Enum):
    """Types of insights."""

    TREND = "trend"  # Increasing/decreasing trend
    SPIKE = "spike"  # Sudden increase
    DROP = "drop"  # Sudden decrease
    CORRELATION = "correlation"  # Correlation between variables
    OUTLIER = "outlier"  # Outlier detection
    DISTRIBUTION = "distribution"  # Distribution analysis
    COMPARISON = "comparison"  # Comparison between categories
    SEASONALITY = "seasonality"  # Seasonal patterns


@dataclass
class Insight:
    """Data insight."""

    type: InsightType
    title: str
    description: str
    confidence: float  # 0-1
    metrics: Dict[str, Any]
    affected_columns: List[str]
    visualization_suggestion: str


class InsightExtractor:
    """
    Extract insights from data using statistical analysis.

    Provides:
    - Trend detection
    - Spike and drop detection
    - Correlation analysis
    - Outlier detection
    - Distribution analysis
    - Comparative insights

    Example:
        extractor = InsightExtractor()

        insights = extractor.extract_insights(df)

        for insight in insights:
            print(f"{insight.title}")
            print(f"  {insight.description}")
            print(f"  Confidence: {insight.confidence:.0%}")
    """

    def __init__(self, confidence_threshold: float = 0.6):
        """
        Initialize insight extractor.

        Args:
            confidence_threshold: Minimum confidence for insights
        """
        self.confidence_threshold = confidence_threshold
        self.logger = logger

        self.logger.info("Insight extractor initialized")

    def extract_insights(
        self,
        df: pd.DataFrame,
        max_insights: int = 10,
    ) -> List[Insight]:
        """
        Extract insights from DataFrame.

        Args:
            df: DataFrame to analyze
            max_insights: Maximum number of insights to return

        Returns:
            List of insights sorted by confidence
        """
        insights = []

        # Detect trends
        insights.extend(self._detect_trends(df))

        # Detect spikes and drops
        insights.extend(self._detect_spikes_drops(df))

        # Detect correlations
        insights.extend(self._detect_correlations(df))

        # Detect outliers
        insights.extend(self._detect_outliers(df))

        # Analyze distributions
        insights.extend(self._analyze_distributions(df))

        # Compare categories
        insights.extend(self._compare_categories(df))

        # Filter by confidence threshold
        insights = [i for i in insights if i.confidence >= self.confidence_threshold]

        # Sort by confidence
        insights.sort(key=lambda x: x.confidence, reverse=True)

        self.logger.info(
            "Insights extracted",
            total=len(insights),
            returned=min(len(insights), max_insights),
        )

        return insights[:max_insights]

    def _detect_trends(self, df: pd.DataFrame) -> List[Insight]:
        """Detect trends in numeric columns."""
        insights = []

        for column in df.select_dtypes(include=[np.number]).columns:
            try:
                # Calculate linear regression
                x = np.arange(len(df))
                y = df[column].values

                # Remove NaN values
                mask = ~np.isnan(y)
                if mask.sum() < 3:
                    continue

                x_clean = x[mask]
                y_clean = y[mask]

                # Linear regression
                coeffs = np.polyfit(x_clean, y_clean, 1)
                slope = coeffs[0]

                # Calculate r-squared
                y_pred = np.polyval(coeffs, x_clean)
                ss_res = np.sum((y_clean - y_pred) ** 2)
                ss_tot = np.sum((y_clean - np.mean(y_clean)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

                # Determine if trend is significant
                if abs(r_squared) > 0.5:  # Strong trend
                    direction = "increasing" if slope > 0 else "decreasing"
                    percent_change = (slope * len(df) / np.mean(y_clean)) * 100

                    insight = Insight(
                        type=InsightType.TREND,
                        title=f"{column.replace('_', ' ').title()} is {direction}",
                        description=f"{column} shows a {direction} trend with {abs(percent_change):.1f}% change over the period.",
                        confidence=min(abs(r_squared), 0.95),
                        metrics={
                            "slope": slope,
                            "r_squared": r_squared,
                            "percent_change": percent_change,
                        },
                        affected_columns=[column],
                        visualization_suggestion="line_chart",
                    )

                    insights.append(insight)

            except Exception as e:
                self.logger.debug(f"Trend detection failed for {column}: {e}")

        return insights

    def _detect_spikes_drops(self, df: pd.DataFrame) -> List[Insight]:
        """Detect sudden spikes or drops."""
        insights = []

        for column in df.select_dtypes(include=[np.number]).columns:
            try:
                values = df[column].values
                if len(values) < 5:
                    continue

                # Calculate moving average and standard deviation
                window = min(7, len(values) // 3)
                rolling_mean = pd.Series(values).rolling(window=window).mean()
                rolling_std = pd.Series(values).rolling(window=window).std()

                # Find anomalies (> 2 std deviations from moving average)
                for i in range(window, len(values)):
                    if pd.isna(rolling_mean[i]) or pd.isna(rolling_std[i]):
                        continue

                    z_score = abs((values[i] - rolling_mean[i]) / rolling_std[i]) if rolling_std[i] > 0 else 0

                    if z_score > 2:
                        is_spike = values[i] > rolling_mean[i]
                        percent_change = ((values[i] - rolling_mean[i]) / rolling_mean[i]) * 100

                        insight = Insight(
                            type=InsightType.SPIKE if is_spike else InsightType.DROP,
                            title=f"{'Spike' if is_spike else 'Drop'} detected in {column.replace('_', ' ').title()}",
                            description=f"{column} shows a {'spike' if is_spike else 'drop'} of {abs(percent_change):.1f}% at position {i}.",
                            confidence=min(z_score / 3, 0.9),
                            metrics={
                                "position": i,
                                "value": values[i],
                                "expected": rolling_mean[i],
                                "z_score": z_score,
                                "percent_change": percent_change,
                            },
                            affected_columns=[column],
                            visualization_suggestion="line_chart_with_annotation",
                        )

                        insights.append(insight)
                        break  # Only report first anomaly per column

            except Exception as e:
                self.logger.debug(f"Spike/drop detection failed for {column}: {e}")

        return insights

    def _detect_correlations(self, df: pd.DataFrame) -> List[Insight]:
        """Detect correlations between numeric columns."""
        insights = []

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) < 2:
            return insights

        # Calculate correlation matrix
        corr_matrix = df[numeric_cols].corr()

        # Find strong correlations
        for i in range(len(numeric_cols)):
            for j in range(i + 1, len(numeric_cols)):
                corr = corr_matrix.iloc[i, j]

                if abs(corr) > 0.7:  # Strong correlation
                    col1 = numeric_cols[i]
                    col2 = numeric_cols[j]

                    relationship = "positively" if corr > 0 else "negatively"

                    insight = Insight(
                        type=InsightType.CORRELATION,
                        title=f"{col1.replace('_', ' ').title()} and {col2.replace('_', ' ').title()} are {relationship} correlated",
                        description=f"{col1} and {col2} show a {relationship} correlated relationship (correlation: {corr:.2f}).",
                        confidence=min(abs(corr), 0.95),
                        metrics={"correlation": corr},
                        affected_columns=[col1, col2],
                        visualization_suggestion="scatter_plot",
                    )

                    insights.append(insight)

        return insights

    def _detect_outliers(self, df: pd.DataFrame) -> List[Insight]:
        """Detect outliers in numeric columns."""
        insights = []

        for column in df.select_dtypes(include=[np.number]).columns:
            try:
                values = df[column].dropna()
                if len(values) < 10:
                    continue

                # IQR method
                q1 = values.quantile(0.25)
                q3 = values.quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr

                outliers = values[(values < lower_bound) | (values > upper_bound)]

                if len(outliers) > 0 and len(outliers) < len(values) * 0.1:  # < 10% outliers
                    outlier_percent = (len(outliers) / len(values)) * 100

                    insight = Insight(
                        type=InsightType.OUTLIER,
                        title=f"Outliers detected in {column.replace('_', ' ').title()}",
                        description=f"{len(outliers)} outliers ({outlier_percent:.1f}%) detected in {column}.",
                        confidence=0.8,
                        metrics={
                            "count": len(outliers),
                            "percent": outlier_percent,
                            "lower_bound": lower_bound,
                            "upper_bound": upper_bound,
                        },
                        affected_columns=[column],
                        visualization_suggestion="box_plot",
                    )

                    insights.append(insight)

            except Exception as e:
                self.logger.debug(f"Outlier detection failed for {column}: {e}")

        return insights

    def _analyze_distributions(self, df: pd.DataFrame) -> List[Insight]:
        """Analyze distributions of numeric columns."""
        insights = []

        for column in df.select_dtypes(include=[np.number]).columns:
            try:
                values = df[column].dropna()
                if len(values) < 10:
                    continue

                # Calculate skewness
                skewness = values.skew()

                if abs(skewness) > 1:  # Significant skew
                    direction = "right" if skewness > 0 else "left"

                    insight = Insight(
                        type=InsightType.DISTRIBUTION,
                        title=f"{column.replace('_', ' ').title()} distribution is {direction}-skewed",
                        description=f"{column} shows a {direction}-skewed distribution (skewness: {skewness:.2f}).",
                        confidence=min(abs(skewness) / 2, 0.85),
                        metrics={"skewness": skewness},
                        affected_columns=[column],
                        visualization_suggestion="histogram",
                    )

                    insights.append(insight)

            except Exception as e:
                self.logger.debug(f"Distribution analysis failed for {column}: {e}")

        return insights

    def _compare_categories(self, df: pd.DataFrame) -> List[Insight]:
        """Compare values across categorical columns."""
        insights = []

        categorical_cols = df.select_dtypes(include=["object", "category"]).columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for cat_col in categorical_cols:
            for num_col in numeric_cols:
                try:
                    if df[cat_col].nunique() > 10:  # Too many categories
                        continue

                    grouped = df.groupby(cat_col)[num_col].mean()
                    if len(grouped) < 2:
                        continue

                    # Find max and min categories
                    max_cat = grouped.idxmax()
                    min_cat = grouped.idxmin()
                    max_val = grouped.max()
                    min_val = grouped.min()

                    difference = max_val - min_val
                    percent_diff = (difference / min_val) * 100 if min_val > 0 else 0

                    if percent_diff > 20:  # Significant difference
                        insight = Insight(
                            type=InsightType.COMPARISON,
                            title=f"{max_cat} has {percent_diff:.0f}% higher {num_col.replace('_', ' ')} than {min_cat}",
                            description=f"Among {cat_col} categories, {max_cat} has the highest average {num_col} ({max_val:.1f}), which is {percent_diff:.0f}% higher than {min_cat} ({min_val:.1f}).",
                            confidence=0.75,
                            metrics={
                                "max_category": max_cat,
                                "min_category": min_cat,
                                "max_value": max_val,
                                "min_value": min_val,
                                "percent_difference": percent_diff,
                            },
                            affected_columns=[cat_col, num_col],
                            visualization_suggestion="bar_chart",
                        )

                        insights.append(insight)

                except Exception as e:
                    self.logger.debug(f"Comparison failed for {cat_col}/{num_col}: {e}")

        return insights
