"""Example usage of agent card validation tests.

This file demonstrates how to use the validation tests programmatically
or customize them for specific use cases.
"""

import asyncio
import os
from typing import Any

import pytest

# Example: Custom agent configs
CUSTOM_AGENT_CONFIGS = [
    {"name": "agent1", "env_var": "AGENT1_URL"},
    {"name": "agent2", "env_var": "AGENT2_URL"},
]


# Example 1: Basic Description Quality Test
@pytest.mark.asyncio
@pytest.mark.skip(reason="Example only - not a real test")
async def example_description_quality_basic():
    """Example: Basic description quality validation."""
    from tests.integration.agent_card.test_agent_description_quality import (
        DescriptionQualityAnalyzer,
    )

    # Initialize with custom configs
    analyzer = DescriptionQualityAnalyzer(CUSTOM_AGENT_CONFIGS)

    try:
        # Fetch agent cards
        agent_cards = await analyzer.fetch_all_agent_cards()

        # Analyze descriptions
        analysis = await analyzer.analyze_all_descriptions(agent_cards)

        # Check results
        print(f"Total evaluated: {analysis['total_evaluated']}")
        print(f"Critical: {analysis['critical_count']}")
        print(f"Warnings: {analysis['warning_count']}")
        print(f"Good: {analysis['good_count']}")
        print(f"Summary: {analysis['summary']}")

        # Access individual evaluations
        for evaluation in analysis["evaluations"]:
            print(f"{evaluation['agent_name']}: {evaluation['overall_score']:.1f}/10")

    finally:
        await analyzer.close()


# Example 2: Generate Description Quality Report Programmatically
@pytest.mark.skip(reason="Example only - not a real test")
def example_description_quality_report():
    """Example: Generate HTML report programmatically."""
    from tests.integration.agent_card.test_agent_description_quality import QualityReporter

    # Mock analysis data
    analysis = {
        "total_evaluated": 2,
        "critical_count": 1,
        "warning_count": 1,
        "good_count": 0,
        "summary": "🔴 CRITICAL: 1 agent(s) with poor descriptions",
        "critical_issues": [
            {
                "agent_name": "example_agent",
                "overall_score": 4.5,
                "clarity_score": 5.0,
                "actionability_score": 4.0,
                "specificity_score": 4.5,
                "severity": "critical",
                "description": "This agent does stuff",
                "weaknesses": ["Too vague", "No clear use cases"],
                "improvement_suggestions": ["Add specific capabilities", "Define when to use"],
                "recommended_description": "Handles data processing for X, Y, Z use cases",
            }
        ],
        "warning_issues": [],
        "good_descriptions": [],
        "average_scores": {
            "clarity": 5.5,
            "actionability": 5.0,
            "specificity": 5.5,
            "overall": 5.3,
        },
    }

    # Generate and save report
    report = QualityReporter.generate_report(analysis)
    QualityReporter.save_report(report, "example_report.html")
    print("Report saved to example_report.html")


# Example 3: Basic Portfolio Coherence Test
@pytest.mark.asyncio
@pytest.mark.skip(reason="Example only - not a real test")
async def example_coherence_basic():
    """Example: Basic portfolio coherence validation."""
    from tests.integration.agent_card.test_coherence_validation import PortfolioCoherenceAnalyzer

    # Initialize with custom configs
    analyzer = PortfolioCoherenceAnalyzer(CUSTOM_AGENT_CONFIGS)

    try:
        # Fetch agent cards
        agent_cards = await analyzer.fetch_all_agent_cards()

        # Analyze portfolio
        analysis = await analyzer.analyze_portfolio(agent_cards)

        # Check results
        print(f"Total comparisons: {analysis['total_comparisons']}")
        print(f"High severity: {analysis['high_severity_count']}")
        print(f"Medium severity: {analysis['medium_severity_count']}")
        print(f"Low severity: {analysis['low_severity_count']}")
        print(f"Summary: {analysis['summary']}")

        # Access individual comparisons
        for issue in analysis["high_severity_issues"]:
            print(f"{issue['agent1']} ↔️ {issue['agent2']}: {issue['similarity_score']:.2f}")

    finally:
        await analyzer.close()


# Example 4: Custom Threshold for Description Quality
@pytest.mark.asyncio
@pytest.mark.skip(reason="Example only - not a real test")
async def example_custom_threshold():
    """Example: Using custom threshold for description quality."""
    from tests.integration.agent_card.test_agent_description_quality import (
        MIN_ACCEPTABLE_SCORE,
        DescriptionQualityAnalyzer,
    )

    analyzer = DescriptionQualityAnalyzer(CUSTOM_AGENT_CONFIGS)

    try:
        agent_cards = await analyzer.fetch_all_agent_cards()
        analysis = await analyzer.analyze_all_descriptions(agent_cards)

        # Custom threshold (stricter than default 5.0)
        custom_threshold = 7.0

        # Check against custom threshold
        failing_agents = [
            e for e in analysis["evaluations"] if e["overall_score"] < custom_threshold
        ]

        if failing_agents:
            print(f"❌ {len(failing_agents)} agents below {custom_threshold}/10 threshold")
            for agent in failing_agents:
                print(f"  - {agent['agent_name']}: {agent['overall_score']:.1f}/10")
        else:
            print(f"✅ All agents meet {custom_threshold}/10 threshold")

    finally:
        await analyzer.close()


# Example 5: Compare Specific Agent Pair
@pytest.mark.asyncio
@pytest.mark.skip(reason="Example only - not a real test")
async def example_compare_specific_pair():
    """Example: Compare two specific agents for overlap."""
    from tests.integration.agent_card.test_coherence_validation import PortfolioCoherenceAnalyzer

    analyzer = PortfolioCoherenceAnalyzer(CUSTOM_AGENT_CONFIGS)

    try:
        agent_cards = await analyzer.fetch_all_agent_cards()

        # Compare specific pair
        agent1_name = "agent1"
        agent2_name = "agent2"

        if agent1_name in agent_cards and agent2_name in agent_cards:
            comparison = await analyzer.compare_agents_with_llm(
                agent1_name, agent_cards[agent1_name], agent2_name, agent_cards[agent2_name]
            )

            print(f"Similarity: {comparison['similarity_score']:.2f}")
            print(f"Severity: {comparison['severity']}")
            print(f"Overlapping capabilities: {comparison['overlapping_capabilities']}")
            print(f"Suggestion: {comparison['consolidation_suggestion']}")

    finally:
        await analyzer.close()


# Example 6: Evaluate Single Description
@pytest.mark.asyncio
@pytest.mark.skip(reason="Example only - not a real test")
async def example_evaluate_single_description():
    """Example: Evaluate a single agent description."""
    from tests.integration.agent_card.test_agent_description_quality import (
        DescriptionQualityAnalyzer,
    )

    analyzer = DescriptionQualityAnalyzer([])

    try:
        # Evaluate a custom description
        description = "This agent helps with data analysis and reporting tasks."
        evaluation = await analyzer.evaluate_description("custom_agent", description)

        print(f"Agent: {evaluation['agent_name']}")
        print(f"Overall Score: {evaluation['overall_score']:.1f}/10")
        print(f"Clarity: {evaluation['clarity_score']:.1f}/10")
        print(f"Actionability: {evaluation['actionability_score']:.1f}/10")
        print(f"Specificity: {evaluation['specificity_score']:.1f}/10")
        print(f"Severity: {evaluation['severity']}")
        print(f"\nStrengths: {evaluation['strengths']}")
        print(f"Weaknesses: {evaluation['weaknesses']}")
        print(f"Suggestions: {evaluation['improvement_suggestions']}")

    finally:
        await analyzer.close()


# Example 7: Batch Process Multiple Descriptions
@pytest.mark.asyncio
@pytest.mark.skip(reason="Example only - not a real test")
async def example_batch_evaluate():
    """Example: Batch evaluate multiple descriptions."""
    from tests.integration.agent_card.test_agent_description_quality import (
        DescriptionQualityAnalyzer,
    )

    analyzer = DescriptionQualityAnalyzer([])

    descriptions = {
        "agent_a": "Provides comprehensive data visualization capabilities",
        "agent_b": "Handles data processing tasks",
        "agent_c": "Specialized agent for real-time analytics and reporting",
    }

    try:
        evaluations = []
        for name, desc in descriptions.items():
            evaluation = await analyzer.evaluate_description(name, desc)
            evaluations.append(evaluation)

        # Sort by score
        evaluations.sort(key=lambda x: x["overall_score"])

        print("📊 Batch Evaluation Results (lowest to highest):")
        for eval in evaluations:
            print(f"  {eval['agent_name']}: {eval['overall_score']:.1f}/10 ({eval['severity']})")

    finally:
        await analyzer.close()


# Example 8: Integration with Existing Tests
@pytest.mark.asyncio
@pytest.mark.skip(reason="Example only - not a real test")
async def example_integration_test(agent_configs):
    """Example: Integrate validation into existing test suite."""
    from tests.integration.agent_card.test_agent_description_quality import (
        DescriptionQualityAnalyzer,
    )

    # Use the same agent_configs fixture from conftest.py
    analyzer = DescriptionQualityAnalyzer(agent_configs)

    try:
        # Step 1: Fetch and validate
        agent_cards = await analyzer.fetch_all_agent_cards()
        assert len(agent_cards) > 0, "No agents configured"

        # Step 2: Quick quality check
        analysis = await analyzer.analyze_all_descriptions(agent_cards)

        # Step 3: Custom validation logic
        if analysis["critical_count"] > 0:
            # Log but don't fail (soft validation)
            print(f"⚠️ Warning: {analysis['critical_count']} agents need description improvements")

        # Step 4: Continue with other tests...

    finally:
        await analyzer.close()


if __name__ == "__main__":
    """Run examples (not meant to be run directly, just for reference)."""
    print("This file contains example usage patterns.")
    print("See the example functions for code snippets you can copy.")
    print("\nExample functions:")
    print("  - example_description_quality_basic()")
    print("  - example_description_quality_report()")
    print("  - example_coherence_basic()")
    print("  - example_custom_threshold()")
    print("  - example_compare_specific_pair()")
    print("  - example_evaluate_single_description()")
    print("  - example_batch_evaluate()")
    print("  - example_integration_test()")
