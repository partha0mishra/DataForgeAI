"""Service for detecting hallucinations in GenAI outputs."""

from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from datetime import datetime
import time
import logging
import os
import hashlib

from sqlalchemy.orm import Session

from src.repositories.hallucination_check_repository import HallucinationCheckRepository
from src.models.hallucination_check import HallucinationCheck

# Try to import GenAI libraries
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger(__name__)


class HallucinationDetectionService:
    """Service for detecting hallucinations in GenAI model outputs."""

    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.hallucination_repo = HallucinationCheckRepository(db)

        # Initialize API clients if available
        if OPENAI_AVAILABLE and os.getenv('OPENAI_API_KEY'):
            self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        else:
            self.openai_client = None

        if ANTHROPIC_AVAILABLE and os.getenv('ANTHROPIC_API_KEY'):
            self.anthropic_client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        else:
            self.anthropic_client = None

    def check_hallucination(
        self,
        prompt: str,
        output: str,
        model_name: str,
        model_version: Optional[str] = None,
        domain: Optional[str] = None,
        use_case: Optional[str] = None,
        detection_methods: Optional[List[str]] = None,
        checked_by: Optional[str] = None
    ) -> HallucinationCheck:
        """
        Check GenAI output for hallucinations.

        Args:
            prompt: The input prompt
            output: The generated output
            model_name: Name of the GenAI model
            model_version: Version of the model
            domain: Domain/topic of the query
            use_case: Use case (e.g., 'customer_support')
            detection_methods: Methods to use for detection
            checked_by: User who requested check

        Returns:
            HallucinationCheck object with detection results
        """
        start_time = time.time()

        try:
            if detection_methods is None:
                detection_methods = ['self_consistency', 'perplexity', 'confidence']

            # Perform hallucination detection
            hallucination_score = 0.0
            confidence_score = 0.0
            detection_details = {}

            # Self-consistency check
            if 'self_consistency' in detection_methods:
                consistency_score = self._check_self_consistency(prompt, output, model_name)
                detection_details['self_consistency'] = consistency_score
                hallucination_score += (1 - consistency_score) * 0.4

            # Confidence-based detection
            if 'confidence' in detection_methods:
                confidence = self._estimate_confidence(output)
                confidence_score = confidence
                detection_details['confidence'] = confidence
                hallucination_score += (1 - confidence) * 0.3

            # Perplexity check (if available)
            if 'perplexity' in detection_methods:
                perplexity = self._calculate_perplexity(output)
                detection_details['perplexity'] = perplexity
                if perplexity > 100:  # High perplexity indicates potential hallucination
                    hallucination_score += 0.2
            else:
                hallucination_score += 0.15  # Base assumption

            # Knowledge retrieval check (if external knowledge available)
            if 'knowledge_retrieval' in detection_methods:
                grounding_quality = self._check_grounding(output)
                detection_details['grounding_quality'] = grounding_quality
                hallucination_score += (1 - grounding_quality) * 0.1

            # Normalize hallucination score
            hallucination_score = min(max(hallucination_score, 0.0), 1.0)

            # Determine risk level
            hallucination_risk = self._determine_risk_level(hallucination_score)

            # Check if output is hallucinated
            hallucinated = hallucination_score > 0.6

            # Extract reasoning (if model supports it)
            reasoning = self._extract_reasoning(prompt, output, model_name)

            # Perform basic fact checking
            fact_checks = self._perform_fact_checks(output)

            # Calculate prompt attribution
            prompt_attribution = self._analyze_prompt_attribution(prompt, output)

            # Detect specific issues
            issues_detected = self._detect_hallucination_issues(
                output, hallucination_score, detection_details
            )

            # Determine severity
            severity = self._determine_severity(hallucination_risk, len(issues_detected))

            # Generate recommendations
            recommendations = self._generate_recommendations(
                issues_detected, hallucination_risk
            )

            # Generate alternative responses (if hallucinated)
            alternative_responses = None
            if hallucinated and self.openai_client:
                alternative_responses = self._generate_alternatives(prompt)

            # Generate explanation
            explanation_text = self._generate_hallucination_explanation(
                hallucination_risk, hallucination_score, issues_detected
            )

            check_duration = (time.time() - start_time) * 1000

            # Create hallucination check record
            check_data = {
                'model_name': model_name,
                'model_version': model_version,
                'prompt': prompt,
                'output': output,
                'hallucination_risk': hallucination_risk,
                'confidence_score': confidence_score,
                'hallucination_score': hallucination_score,
                'reasoning': reasoning,
                'prompt_attribution': prompt_attribution,
                'fact_checks': fact_checks,
                'grounding_quality': detection_details.get('grounding_quality'),
                'detection_methods': detection_methods,
                'detection_details': detection_details,
                'hallucinated': hallucinated,
                'issues_detected': issues_detected,
                'severity': severity,
                'recommendations': recommendations,
                'alternative_responses': alternative_responses,
                'domain': domain,
                'use_case': use_case,
                'check_duration_ms': check_duration,
                'explanation_text': explanation_text,
                'checked_by': checked_by
            }

            return self.hallucination_repo.create(check_data)

        except Exception as e:
            logger.error(f"Error in hallucination detection: {str(e)}")
            raise

    def _check_self_consistency(
        self,
        prompt: str,
        output: str,
        model_name: str
    ) -> float:
        """Check self-consistency by generating multiple responses."""
        # Simplified implementation
        # In production, would generate multiple responses and compare
        # For now, return a heuristic based on output characteristics

        # Check for hedging language that indicates uncertainty
        hedging_words = ['maybe', 'possibly', 'might', 'could', 'perhaps', 'probably']
        hedging_count = sum(1 for word in hedging_words if word in output.lower())

        # More hedging = less consistency
        consistency = max(0.5, 1.0 - (hedging_count * 0.1))

        return min(consistency, 1.0)

    def _estimate_confidence(self, output: str) -> float:
        """Estimate confidence in the output."""
        # Heuristic-based confidence estimation
        # In production, this would use model's actual confidence scores

        # Factors that reduce confidence:
        # - Presence of uncertainty phrases
        # - Very short or very long responses
        # - Lack of specific details

        uncertainty_phrases = [
            'i\'m not sure', 'i don\'t know', 'unclear', 'uncertain',
            'not confident', 'maybe', 'possibly'
        ]

        confidence = 0.8  # Base confidence

        # Reduce for uncertainty phrases
        for phrase in uncertainty_phrases:
            if phrase in output.lower():
                confidence -= 0.15

        # Reduce for extreme lengths
        word_count = len(output.split())
        if word_count < 10 or word_count > 500:
            confidence -= 0.1

        return max(min(confidence, 1.0), 0.0)

    def _calculate_perplexity(self, output: str) -> float:
        """Calculate perplexity of the output (simplified)."""
        # In production, would use actual language model to calculate perplexity
        # For now, return a reasonable estimate

        # Very simple heuristic: longer, more complex sentences = higher perplexity
        words = output.split()
        avg_word_length = sum(len(w) for w in words) / len(words) if words else 0

        # Estimate perplexity based on word length and sentence structure
        perplexity = 30 + (avg_word_length * 5)

        return perplexity

    def _check_grounding(self, output: str) -> float:
        """Check how well grounded the output is in verifiable facts."""
        # Simplified implementation
        # In production, would check against knowledge base

        # Look for specific facts (numbers, dates, names, etc.)
        import re

        # Count specific elements
        numbers = len(re.findall(r'\b\d+\b', output))
        dates = len(re.findall(r'\b\d{4}\b|\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', output))
        proper_nouns = len(re.findall(r'\b[A-Z][a-z]+\b', output))

        # More specific facts = better grounding
        specificity_score = min((numbers + dates + proper_nouns) / 10, 1.0)

        return max(specificity_score, 0.3)

    def _extract_reasoning(
        self,
        prompt: str,
        output: str,
        model_name: str
    ) -> Optional[str]:
        """Extract chain-of-thought reasoning if available."""
        # In production, would use model's reasoning capabilities
        # For now, return basic analysis

        if 'explain' in prompt.lower() or 'why' in prompt.lower():
            return f"Model was asked to provide reasoning. Output length: {len(output)} chars."

        return None

    def _perform_fact_checks(self, output: str) -> List[Dict[str, Any]]:
        """Perform basic fact checking on claims in output."""
        # Simplified implementation
        # In production, would check against external knowledge sources

        fact_checks = []

        # Extract potential factual claims (sentences with numbers, dates, etc.)
        import re
        sentences = output.split('.')

        for sentence in sentences[:3]:  # Check first 3 sentences
            if re.search(r'\b\d+\b', sentence):
                fact_checks.append({
                    'claim': sentence.strip(),
                    'verified': None,  # Would check against knowledge base
                    'confidence': 0.5,
                    'source': 'not_checked'
                })

        return fact_checks if fact_checks else []

    def _analyze_prompt_attribution(
        self,
        prompt: str,
        output: str
    ) -> Dict[str, float]:
        """Analyze which parts of prompt influenced the output."""
        # Simplified implementation
        # In production, would use attention mechanisms

        attribution = {}

        # Simple keyword overlap analysis
        prompt_words = set(prompt.lower().split())
        output_words = set(output.lower().split())

        overlap = prompt_words.intersection(output_words)

        # Create attribution weights
        for word in list(overlap)[:5]:  # Top 5 overlapping words
            attribution[word] = 0.5 + (len(word) / 20)  # Longer words get higher weight

        return attribution

    def _detect_hallucination_issues(
        self,
        output: str,
        hallucination_score: float,
        detection_details: Dict[str, Any]
    ) -> List[str]:
        """Detect specific hallucination issues."""
        issues = []

        if hallucination_score > 0.7:
            issues.append("High hallucination risk detected")

        if detection_details.get('self_consistency', 1.0) < 0.5:
            issues.append("Low self-consistency in responses")

        if detection_details.get('confidence', 1.0) < 0.5:
            issues.append("Low confidence in generated output")

        if detection_details.get('perplexity', 0) > 150:
            issues.append("Unusually high perplexity detected")

        if detection_details.get('grounding_quality', 1.0) < 0.4:
            issues.append("Poor grounding in verifiable facts")

        # Check for common hallucination patterns
        if 'i don\'t know' in output.lower() and len(output) > 100:
            issues.append("Model expressed uncertainty but continued generating")

        return issues

    def _determine_risk_level(self, score: float) -> str:
        """Determine hallucination risk level."""
        if score >= 0.8:
            return "critical"
        elif score >= 0.6:
            return "high"
        elif score >= 0.4:
            return "medium"
        elif score >= 0.2:
            return "low"
        else:
            return "none"

    def _determine_severity(self, risk_level: str, num_issues: int) -> str:
        """Determine severity of hallucination."""
        if risk_level in ['critical', 'high'] and num_issues >= 3:
            return "critical"
        elif risk_level == 'high' or num_issues >= 2:
            return "high"
        elif risk_level == 'medium':
            return "medium"
        else:
            return "low"

    def _generate_recommendations(
        self,
        issues: List[str],
        risk_level: str
    ) -> List[str]:
        """Generate recommendations for addressing hallucinations."""
        recommendations = []

        if not issues:
            recommendations.append("No significant hallucination detected")
            return recommendations

        if risk_level in ['high', 'critical']:
            recommendations.append("Do not use this output without verification")
            recommendations.append("Regenerate response with different prompt")

        if any('self-consistency' in issue for issue in issues):
            recommendations.append("Use ensemble voting across multiple responses")

        if any('confidence' in issue for issue in issues):
            recommendations.append("Request model to indicate uncertainty explicitly")

        if any('grounding' in issue for issue in issues):
            recommendations.append("Provide more context and specific sources in prompt")
            recommendations.append("Use retrieval-augmented generation (RAG)")

        return recommendations

    def _generate_alternatives(self, prompt: str) -> List[str]:
        """Generate alternative responses (placeholder)."""
        # In production, would call model API to generate alternatives
        return []

    def _generate_hallucination_explanation(
        self,
        risk_level: str,
        score: float,
        issues: List[str]
    ) -> str:
        """Generate explanation of hallucination check results."""
        explanation = f"""
Hallucination Check Results
===========================

Risk Level: {risk_level.upper()}
Hallucination Score: {score:.2f}/1.00
Issues Detected: {len(issues)}

"""

        if issues:
            explanation += "Detected Issues:\\n"
            for issue in issues:
                explanation += f"- {issue}\\n"
            explanation += "\\n"

        if risk_level in ['high', 'critical']:
            explanation += "⚠️  WARNING: This output has high hallucination risk. "
            explanation += "Verify all factual claims before use."
        elif risk_level == 'medium':
            explanation += "⚠️  CAUTION: This output may contain some inaccuracies. "
            explanation += "Review carefully before use."
        else:
            explanation += "✓ This output appears reliable, but always verify critical information."

        return explanation

    def get_check_by_id(self, check_id: str) -> Optional[HallucinationCheck]:
        """Get hallucination check by ID."""
        return self.hallucination_repo.get_by_id(check_id)

    def get_model_checks(
        self,
        model_name: str,
        model_version: Optional[str] = None,
        limit: int = 100
    ) -> List[HallucinationCheck]:
        """Get hallucination checks for a model."""
        return self.hallucination_repo.get_by_model(model_name, model_version, limit)

    def get_high_risk_checks(
        self,
        hours: int = 24,
        model_name: Optional[str] = None
    ) -> List[HallucinationCheck]:
        """Get high risk hallucination checks."""
        return self.hallucination_repo.get_high_risk_checks(hours, model_name)

    def get_check_stats(
        self,
        model_name: Optional[str] = None,
        hours: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get hallucination check statistics."""
        return self.hallucination_repo.get_check_stats(model_name, hours)

    def get_model_reliability(
        self,
        model_name: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get reliability metrics for a model."""
        return self.hallucination_repo.get_model_reliability(model_name, days)

    def delete_check(self, check_id: str) -> bool:
        """Delete a hallucination check."""
        return self.hallucination_repo.delete(check_id)
