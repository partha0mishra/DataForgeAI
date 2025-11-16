"""Example: Complete process optimization workflow."""

import os
import sys
from pathlib import Path

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mining.process_miner import ProcessMiner
from analysis.bottleneck_analyzer import BottleneckAnalyzer
from optimization.optimizer import ProcessOptimizer


def print_section(title: str):
    """Print section header."""
    print()
    print("=" * 80)
    print(f" {title}")
    print("=" * 80)
    print()


def create_sample_process_log():
    """Create sample process event log."""
    print("Creating sample process event log...")

    np.random.seed(42)

    # Process: Order Fulfillment
    activities = [
        "Receive Order",
        "Validate Payment",
        "Check Inventory",
        "Pick Items",
        "Pack Order",
        "Quality Check",
        "Ship Order",
        "Confirm Delivery",
    ]

    resources = ["System", "Agent1", "Agent2", "Agent3", "Warehouse1", "Warehouse2", "QA Team", "Shipping"]

    events = []
    case_id = 1

    # Generate 200 cases
    for _ in range(200):
        # Random start time
        start_time = datetime(2024, 1, 1) + timedelta(days=np.random.randint(0, 90))

        # Normal path with some variations
        current_time = start_time

        # Receive Order
        events.append({
            "case_id": f"ORDER_{case_id:04d}",
            "activity": "Receive Order",
            "timestamp": current_time,
            "resource": "System",
        })
        current_time += timedelta(minutes=np.random.randint(1, 5))

        # Validate Payment
        events.append({
            "case_id": f"ORDER_{case_id:04d}",
            "activity": "Validate Payment",
            "timestamp": current_time,
            "resource": np.random.choice(["Agent1", "Agent2"]),
        })
        current_time += timedelta(minutes=np.random.randint(5, 30))

        # Check Inventory - sometimes delayed
        delay = np.random.choice([0, 0, 0, 1, 2, 24])  # Sometimes 24hr delay (bottleneck)
        current_time += timedelta(hours=delay)
        events.append({
            "case_id": f"ORDER_{case_id:04d}",
            "activity": "Check Inventory",
            "timestamp": current_time,
            "resource": np.random.choice(["Warehouse1", "Warehouse2"]),
        })
        current_time += timedelta(minutes=np.random.randint(10, 60))

        # Pick Items - sometimes repeated (bottleneck)
        pick_attempts = np.random.choice([1, 1, 1, 2, 3])  # Sometimes multiple picks
        for attempt in range(pick_attempts):
            events.append({
                "case_id": f"ORDER_{case_id:04d}",
                "activity": "Pick Items",
                "timestamp": current_time,
                "resource": np.random.choice(["Warehouse1", "Warehouse2"]),
            })
            current_time += timedelta(hours=np.random.randint(1, 4))

        # Pack Order
        events.append({
            "case_id": f"ORDER_{case_id:04d}",
            "activity": "Pack Order",
            "timestamp": current_time,
            "resource": np.random.choice(["Warehouse1", "Warehouse2"]),
        })
        current_time += timedelta(minutes=np.random.randint(15, 45))

        # Quality Check - sometimes long duration (bottleneck)
        qa_duration = np.random.choice([30, 30, 60, 120, 240])  # Sometimes 4hrs
        events.append({
            "case_id": f"ORDER_{case_id:04d}",
            "activity": "Quality Check",
            "timestamp": current_time,
            "resource": "QA Team",
        })
        current_time += timedelta(minutes=qa_duration)

        # Ship Order
        events.append({
            "case_id": f"ORDER_{case_id:04d}",
            "activity": "Ship Order",
            "timestamp": current_time,
            "resource": "Shipping",
        })
        current_time += timedelta(hours=np.random.randint(24, 72))

        # Confirm Delivery - sometimes fails (outcome)
        outcome = np.random.choice(["success", "success", "success", "failed"])
        events.append({
            "case_id": f"ORDER_{case_id:04d}",
            "activity": "Confirm Delivery",
            "timestamp": current_time,
            "resource": "System",
            "outcome": outcome,
        })

        case_id += 1

    df = pd.DataFrame(events)

    # Save to CSV
    output_path = Path(__file__).parent / "sample_process_log.csv"
    df.to_csv(output_path, index=False)

    print(f"✓ Created {len(df)} events for {case_id-1} cases")
    print(f"✓ Saved to: {output_path}")
    print(f"✓ Activities: {len(df['activity'].unique())}")
    print(f"✓ Resources: {len(df['resource'].unique())}")

    return df, output_path


def main():
    """Run complete process optimization example."""
    print("=" * 80)
    print(" DataForge Process Optimization - Complete Example")
    print("=" * 80)

    # Step 1: Create sample process log
    print_section("1. Create Sample Process Event Log")
    event_log, log_path = create_sample_process_log()

    # Step 2: Initialize components
    print_section("2. Initialize Process Optimization Components")

    process_miner = ProcessMiner()
    print("✓ Process miner initialized")

    bottleneck_analyzer = BottleneckAnalyzer(
        duration_threshold_percentile=0.75,
        frequency_threshold_std=2.0,
        waiting_time_threshold_hours=12.0,
    )
    print("✓ Bottleneck analyzer initialized")

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        process_optimizer = ProcessOptimizer(llm_api_key=api_key)
        print("✓ Process optimizer initialized (with LLM)")
    else:
        process_optimizer = ProcessOptimizer()
        print("✓ Process optimizer initialized (without LLM)")
        print("  Set OPENAI_API_KEY for AI-powered recommendations")

    # Step 3: Discover process
    print_section("3. Discover Process from Event Log")

    discovered = process_miner.discover_process(
        event_log=event_log,
        case_id_column="case_id",
        activity_column="activity",
        timestamp_column="timestamp",
        resource_column="resource",
        outcome_column="outcome",
    )

    print(f"Process: {discovered.process_name}")
    print(f"Total Cases: {discovered.total_cases}")
    print(f"Unique Activities: {discovered.unique_activities}")
    print(f"Start Activities: {', '.join(discovered.start_activities)}")
    print(f"End Activities: {', '.join(discovered.end_activities)}")
    print()
    print("Activity Statistics:")
    for activity, step in discovered.steps.items():
        print(f"  {activity}:")
        print(f"    Count: {step.count}")
        print(f"    Avg Duration: {step.avg_duration:.2f} hours")
        if step.resources:
            print(f"    Resources: {', '.join(step.resources)}")
    print()
    print(f"Top 5 Process Paths:")
    for i, path in enumerate(discovered.paths[:5], 1):
        print(f"  {i}. {' → '.join(path.steps)}")
        print(f"     Count: {path.count}, Avg Duration: {path.avg_total_duration:.2f}h, Success: {path.success_rate:.0%}")

    # Step 4: Analyze bottlenecks
    print_section("4. Analyze Process Bottlenecks")

    analysis = bottleneck_analyzer.analyze(
        discovered_process=discovered,
        event_log=event_log,
        case_id_column="case_id",
        activity_column="activity",
        timestamp_column="timestamp",
        resource_column="resource",
    )

    print(f"Overall Health Score: {analysis.overall_health_score:.1f}/100")
    print(f"Total Bottlenecks: {analysis.total_bottlenecks}")
    print(f"  High Severity: {analysis.high_severity_count}")
    print(f"  Medium Severity: {analysis.medium_severity_count}")
    print(f"  Low Severity: {analysis.low_severity_count}")
    print()
    print("Top Bottlenecks:")
    for i, bottleneck in enumerate(analysis.bottlenecks[:5], 1):
        print(f"\n{i}. {bottleneck.activity}")
        print(f"   Type: {bottleneck.bottleneck_type}")
        print(f"   Severity: {bottleneck.severity:.2f}")
        print(f"   Impact: {bottleneck.impact}")
        print(f"   Evidence:")
        for key, value in bottleneck.evidence.items():
            if isinstance(value, (int, float)):
                print(f"     {key}: {value:.2f}")
            else:
                print(f"     {key}: {value}")

    # Step 5: Generate optimization plan
    print_section("5. Generate Optimization Plan")

    optimization_plan = process_optimizer.optimize(
        discovered_process=discovered,
        bottleneck_analysis=analysis,
    )

    print(f"Current Health Score: {optimization_plan.current_health_score:.1f}/100")
    print(f"Projected Health Score: {optimization_plan.projected_health_score:.1f}/100")
    print(f"Improvement: +{optimization_plan.projected_health_score - optimization_plan.current_health_score:.1f} points")
    print()
    print(f"Total Recommendations: {len(optimization_plan.recommendations)}")
    print(f"Quick Wins: {len(optimization_plan.quick_wins)}")
    print(f"Strategic Initiatives: {len(optimization_plan.strategic_initiatives)}")
    print(f"Total Estimated Savings: {optimization_plan.total_estimated_savings_hours:.0f} hours")
    print()
    print("Quick Wins (High Priority, Low Effort):")
    for i, rec in enumerate(optimization_plan.quick_wins, 1):
        print(f"\n{i}. {rec.title}")
        print(f"   {rec.description}")
        print(f"   Category: {rec.category}")
        print(f"   Estimated Impact: {rec.estimated_impact}")
        if rec.estimated_savings_hours:
            print(f"   Estimated Savings: {rec.estimated_savings_hours:.0f} hours")
    print()
    print("All Recommendations:")
    for i, rec in enumerate(optimization_plan.recommendations, 1):
        print(f"\n{i}. {rec.title}")
        print(f"   Priority: {rec.priority.upper()}, Effort: {rec.implementation_effort}")
        print(f"   {rec.description}")

    # Step 6: Implementation roadmap
    print_section("6. Implementation Roadmap")

    for phase in optimization_plan.implementation_roadmap:
        print(f"\n{phase['phase']}")
        print(f"Recommendations: {len(phase['recommendations'])}")
        print(f"Estimated Savings: {phase['estimated_savings']:.0f} hours")
        print("Items:")
        for rec in phase['recommendations']:
            print(f"  • {rec}")

    # Step 7: Export BPMN
    print_section("7. Export Process Model")

    bpmn_xml = process_miner.export_bpmn(discovered)
    bpmn_path = Path(__file__).parent / "process_model.bpmn"
    bpmn_path.write_text(bpmn_xml)

    print(f"✓ BPMN model exported to: {bpmn_path}")
    print(f"  Open with BPMN modeling tools for visualization")

    # Final summary
    print_section("Example Complete!")

    print("Summary:")
    print(f"  ✓ Analyzed {discovered.total_cases} process cases")
    print(f"  ✓ Discovered {discovered.unique_activities} unique activities")
    print(f"  ✓ Identified {analysis.total_bottlenecks} bottlenecks")
    print(f"  ✓ Generated {len(optimization_plan.recommendations)} optimization recommendations")
    print(f"  ✓ Estimated savings: {optimization_plan.total_estimated_savings_hours:.0f} hours")
    print(f"  ✓ Health score improvement: {optimization_plan.current_health_score:.1f} → {optimization_plan.projected_health_score:.1f}")
    print()
    print("Next steps:")
    print("  1. Start API: uvicorn src.api.main:app --reload --port 8009")
    print("  2. Try API at http://localhost:8009/docs")
    print("  3. Upload your own process event logs")
    print("  4. Implement quick wins for immediate impact")
    print()


if __name__ == "__main__":
    main()
