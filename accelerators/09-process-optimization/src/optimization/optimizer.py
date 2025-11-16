"""Process optimization recommendations."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from dataforge_ai_core.llm import LLMClient
from dataforge_common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class OptimizationRecommendation:
    """A process optimization recommendation."""

    title: str
    description: str
    category: str  # automation, redesign, resource, technology
    priority: str  # high, medium, low
    estimated_impact: str
    implementation_effort: str  # low, medium, high
    affected_activities: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    estimated_savings_hours: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationPlan:
    """Complete process optimization plan."""

    process_name: str
    current_health_score: float
    projected_health_score: float
    recommendations: List[OptimizationRecommendation]
    quick_wins: List[OptimizationRecommendation]
    strategic_initiatives: List[OptimizationRecommendation]
    total_estimated_savings_hours: float
    implementation_roadmap: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProcessOptimizer:
    """Generate process optimization recommendations."""

    def __init__(
        self,
        llm_api_key: Optional[str] = None,
        llm_model: str = "gpt-4",
    ):
        """Initialize process optimizer.

        Args:
            llm_api_key: Optional API key for LLM-powered recommendations
            llm_model: LLM model name
        """
        self.llm_client = None
        if llm_api_key:
            self.llm_client = LLMClient(api_key=llm_api_key, model=llm_model)

    def optimize(
        self,
        discovered_process,
        bottleneck_analysis,
    ) -> OptimizationPlan:
        """Generate optimization plan.

        Args:
            discovered_process: Discovered process from ProcessMiner
            bottleneck_analysis: Bottleneck analysis results

        Returns:
            Optimization plan with recommendations
        """
        logger.info("Generating optimization plan")

        recommendations = []

        # Generate recommendations for each bottleneck
        for bottleneck in bottleneck_analysis.bottlenecks:
            recs = self._generate_bottleneck_recommendations(
                bottleneck,
                discovered_process,
            )
            recommendations.extend(recs)

        # Generate general improvement recommendations
        general_recs = self._generate_general_recommendations(
            discovered_process,
            bottleneck_analysis,
        )
        recommendations.extend(general_recs)

        # Use LLM for enhanced recommendations if available
        if self.llm_client:
            llm_recs = self._generate_llm_recommendations(
                discovered_process,
                bottleneck_analysis,
            )
            recommendations.extend(llm_recs)

        # Categorize recommendations
        quick_wins = [
            r for r in recommendations
            if r.priority == "high" and r.implementation_effort == "low"
        ]

        strategic = [
            r for r in recommendations
            if r.implementation_effort == "high"
        ]

        # Calculate total savings
        total_savings = sum(
            r.estimated_savings_hours or 0 for r in recommendations
        )

        # Project health score improvement
        projected_score = min(
            bottleneck_analysis.overall_health_score + (len(recommendations) * 5),
            100.0,
        )

        # Create implementation roadmap
        roadmap = self._create_roadmap(recommendations)

        plan = OptimizationPlan(
            process_name=discovered_process.process_name,
            current_health_score=bottleneck_analysis.overall_health_score,
            projected_health_score=projected_score,
            recommendations=recommendations,
            quick_wins=quick_wins,
            strategic_initiatives=strategic,
            total_estimated_savings_hours=total_savings,
            implementation_roadmap=roadmap,
        )

        logger.info(
            f"Generated {len(recommendations)} recommendations "
            f"({len(quick_wins)} quick wins, {len(strategic)} strategic)"
        )

        return plan

    def _generate_bottleneck_recommendations(
        self,
        bottleneck,
        discovered_process,
    ) -> List[OptimizationRecommendation]:
        """Generate recommendations for a specific bottleneck."""
        recommendations = []

        if bottleneck.bottleneck_type == "duration":
            # Duration-specific recommendations
            rec = OptimizationRecommendation(
                title=f"Reduce Duration of {bottleneck.activity}",
                description=f"Optimize the '{bottleneck.activity}' activity which currently takes {bottleneck.evidence.get('avg_duration_hours', 0):.2f} hours on average.",
                category="automation",
                priority="high" if bottleneck.severity > 0.7 else "medium",
                estimated_impact=f"Reduce processing time by {bottleneck.evidence.get('excess_percentage', 0):.0f}%",
                implementation_effort="medium",
                affected_activities=[bottleneck.activity],
                prerequisites=[
                    "Analyze current implementation",
                    "Identify automation opportunities",
                ],
                risks=["Temporary process disruption during implementation"],
                estimated_savings_hours=bottleneck.evidence.get("avg_duration_hours", 0) * 0.3,  # 30% reduction
            )
            recommendations.append(rec)

        elif bottleneck.bottleneck_type == "waiting":
            # Waiting time recommendations
            activities = bottleneck.activity.split(" → ")

            rec = OptimizationRecommendation(
                title=f"Eliminate Waiting Time Between Activities",
                description=f"Reduce {bottleneck.evidence.get('avg_waiting_hours', 0):.2f} hour average waiting time between '{activities[0]}' and '{activities[1]}'.",
                category="redesign",
                priority="high" if bottleneck.severity > 0.7 else "medium",
                estimated_impact="Reduce cycle time by up to 40%",
                implementation_effort="low",
                affected_activities=activities,
                prerequisites=["Implement automatic handoff", "Add notifications"],
                risks=["Requires coordination between teams"],
                estimated_savings_hours=bottleneck.evidence.get("avg_waiting_hours", 0) * 0.5,
            )
            recommendations.append(rec)

        elif bottleneck.bottleneck_type == "frequency":
            # Frequency-specific recommendations
            rec = OptimizationRecommendation(
                title=f"Reduce Frequency of {bottleneck.activity}",
                description=f"Activity occurs {bottleneck.evidence.get('count', 0)} times, investigate and reduce rework.",
                category="redesign",
                priority="medium",
                estimated_impact="Eliminate 30-50% of repetitions",
                implementation_effort="medium",
                affected_activities=[bottleneck.activity],
                prerequisites=["Root cause analysis", "Quality improvements upstream"],
                risks=["May require process redesign"],
                estimated_savings_hours=bottleneck.evidence.get("count", 0) * 0.3,
            )
            recommendations.append(rec)

        elif bottleneck.bottleneck_type == "resource":
            # Resource-specific recommendations
            rec = OptimizationRecommendation(
                title=f"Balance Resource Workload",
                description=f"Resource is overloaded with {bottleneck.evidence.get('workload', 0)} events.",
                category="resource",
                priority="high",
                estimated_impact="Improve throughput by 25-40%",
                implementation_effort="low",
                affected_activities=[],
                prerequisites=["Workload analysis", "Resource availability assessment"],
                risks=["Training required for additional resources"],
                estimated_savings_hours=bottleneck.evidence.get("workload", 0) * 0.2,
            )
            recommendations.append(rec)

        elif bottleneck.bottleneck_type == "path":
            # Path-specific recommendations
            rec = OptimizationRecommendation(
                title=f"Improve Process Path Success Rate",
                description=f"Path has only {bottleneck.evidence.get('success_rate', 0):.0%} success rate, needs redesign.",
                category="redesign",
                priority="high" if bottleneck.severity > 0.7 else "medium",
                estimated_impact=f"Improve success rate to >90%",
                implementation_effort="high",
                affected_activities=bottleneck.evidence.get("path_steps", []),
                prerequisites=["Failure analysis", "Process redesign"],
                risks=["Significant process changes required"],
                estimated_savings_hours=bottleneck.evidence.get("avg_duration_hours", 0) * bottleneck.evidence.get("count", 0) * (1 - bottleneck.evidence.get("success_rate", 1)),
            )
            recommendations.append(rec)

        return recommendations

    def _generate_general_recommendations(
        self,
        discovered_process,
        bottleneck_analysis,
    ) -> List[OptimizationRecommendation]:
        """Generate general process improvement recommendations."""
        recommendations = []

        # Automation opportunities
        if discovered_process.unique_activities > 10:
            rec = OptimizationRecommendation(
                title="Implement Process Automation",
                description="Automate repetitive manual activities to reduce human error and processing time.",
                category="automation",
                priority="medium",
                estimated_impact="20-30% reduction in manual effort",
                implementation_effort="high",
                affected_activities=[],
                prerequisites=["Technology assessment", "ROI analysis"],
                risks=["Initial investment required", "Change management"],
                estimated_savings_hours=discovered_process.statistics.get("avg_case_duration_hours", 0) * discovered_process.total_cases * 0.2,
            )
            recommendations.append(rec)

        # Parallel processing
        if len(discovered_process.paths) > 5:
            rec = OptimizationRecommendation(
                title="Enable Parallel Processing",
                description="Identify activities that can be executed in parallel to reduce overall cycle time.",
                category="redesign",
                priority="medium",
                estimated_impact="15-25% cycle time reduction",
                implementation_effort="medium",
                affected_activities=[],
                prerequisites=["Dependency analysis", "System capabilities"],
                risks=["Complexity increase"],
                estimated_savings_hours=discovered_process.statistics.get("avg_case_duration_hours", 0) * discovered_process.total_cases * 0.15,
            )
            recommendations.append(rec)

        # Standardization
        if len(discovered_process.paths) > 10:
            rec = OptimizationRecommendation(
                title="Standardize Process Variations",
                description=f"Reduce {len(discovered_process.paths)} process variations to improve consistency.",
                category="redesign",
                priority="low",
                estimated_impact="Improved quality and predictability",
                implementation_effort="medium",
                affected_activities=[],
                prerequisites=["Variation analysis", "Best practice identification"],
                risks=["May reduce flexibility"],
            )
            recommendations.append(rec)

        return recommendations

    def _generate_llm_recommendations(
        self,
        discovered_process,
        bottleneck_analysis,
    ) -> List[OptimizationRecommendation]:
        """Generate AI-powered recommendations using LLM."""
        if not self.llm_client:
            return []

        try:
            # Build context
            context = f"""
Process: {discovered_process.process_name}
Total Cases: {discovered_process.total_cases}
Unique Activities: {discovered_process.unique_activities}
Average Case Duration: {discovered_process.statistics.get('avg_case_duration_hours', 0):.2f} hours
Health Score: {bottleneck_analysis.overall_health_score:.1f}/100

Top Bottlenecks:
"""
            for i, bottleneck in enumerate(bottleneck_analysis.bottlenecks[:3], 1):
                context += f"{i}. {bottleneck.activity} ({bottleneck.bottleneck_type}, severity: {bottleneck.severity:.2f})\n"

            prompt = f"""{context}

Based on this process analysis, provide 2-3 strategic optimization recommendations.
Focus on high-impact improvements that address the root causes.

Format each recommendation as:
TITLE: <title>
CATEGORY: <automation|redesign|resource|technology>
DESCRIPTION: <description>
IMPACT: <estimated impact>
EFFORT: <low|medium|high>
"""

            response = self.llm_client.generate_chat(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business process optimization expert.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.7,
            )

            # Parse response (simplified)
            recommendations = []
            rec_texts = response.split("\n\n")

            for rec_text in rec_texts:
                if "TITLE:" in rec_text:
                    lines = rec_text.split("\n")
                    title = ""
                    category = "technology"
                    description = ""
                    impact = ""
                    effort = "medium"

                    for line in lines:
                        if line.startswith("TITLE:"):
                            title = line.replace("TITLE:", "").strip()
                        elif line.startswith("CATEGORY:"):
                            category = line.replace("CATEGORY:", "").strip().lower()
                        elif line.startswith("DESCRIPTION:"):
                            description = line.replace("DESCRIPTION:", "").strip()
                        elif line.startswith("IMPACT:"):
                            impact = line.replace("IMPACT:", "").strip()
                        elif line.startswith("EFFORT:"):
                            effort = line.replace("EFFORT:", "").strip().lower()

                    if title and description:
                        rec = OptimizationRecommendation(
                            title=title,
                            description=description,
                            category=category,
                            priority="medium",
                            estimated_impact=impact,
                            implementation_effort=effort,
                            affected_activities=[],
                            metadata={"source": "llm"},
                        )
                        recommendations.append(rec)

            return recommendations

        except Exception as e:
            logger.warning(f"Failed to generate LLM recommendations: {str(e)}")
            return []

    def _create_roadmap(
        self,
        recommendations: List[OptimizationRecommendation],
    ) -> List[Dict[str, Any]]:
        """Create implementation roadmap."""
        # Phase 1: Quick wins (high priority, low effort)
        phase1 = [
            r for r in recommendations
            if r.priority == "high" and r.implementation_effort == "low"
        ]

        # Phase 2: Medium effort improvements
        phase2 = [
            r for r in recommendations
            if r.implementation_effort == "medium" and r.priority in ["high", "medium"]
        ]

        # Phase 3: Strategic initiatives (high effort)
        phase3 = [
            r for r in recommendations
            if r.implementation_effort == "high"
        ]

        roadmap = []

        if phase1:
            roadmap.append({
                "phase": "Phase 1: Quick Wins (0-3 months)",
                "recommendations": [r.title for r in phase1],
                "estimated_savings": sum(r.estimated_savings_hours or 0 for r in phase1),
            })

        if phase2:
            roadmap.append({
                "phase": "Phase 2: Tactical Improvements (3-6 months)",
                "recommendations": [r.title for r in phase2],
                "estimated_savings": sum(r.estimated_savings_hours or 0 for r in phase2),
            })

        if phase3:
            roadmap.append({
                "phase": "Phase 3: Strategic Initiatives (6-12 months)",
                "recommendations": [r.title for r in phase3],
                "estimated_savings": sum(r.estimated_savings_hours or 0 for r in phase3),
            })

        return roadmap
