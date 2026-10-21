"""Integration test for agent description quality validation.

This test validates:
1. Evaluates agent description clarity, actionability, and specificity
2. Uses LLM-as-judge for quality evaluation
3. Generates improvement suggestions
4. Logs results with structlog
5. Alerts on low-quality descriptions (<5/10)
"""

import json
import os
from pathlib import Path
from typing import Any

import httpx
import litellm
import pytest
import structlog

logger = structlog.get_logger(__name__)

# Configuration
AGENT_CARD_PATH = "/.well-known/agent-card.json"
MIN_ACCEPTABLE_SCORE = 5.0
HTML_OUTPUT_PATH = "reports/description_quality_analysis.html"

litellm.api_base = os.getenv("LITELLM_API_BASE")
litellm.api_key = os.getenv("LITELLM_API_KEY")


class DescriptionQualityAnalyzer:
    """Analyzes agent description quality using LLM-as-judge."""

    def __init__(self, agent_configs: list[dict[str, str]]):
        """Initialize the analyzer with agent configurations.

        Args:
            agent_configs: List of dicts with 'name' and 'env_var' keys for each agent.
        """
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.agent_configs = agent_configs

    def fetch_local_agent_card(self, agent_name: str) -> dict[str, Any]:
        """Fetch agent card from local MyAgent class.

        Args:
            agent_name: Name of the agent (for logging purposes).

        Returns:
            Agent card as a dictionary.
        """
        logger.info("Fetching local agent card", agent_name=agent_name)
        from src.cotality.agent.agent import MyAgent

        agent = MyAgent()
        agent_card = agent.get_agent_card(host="localhost", port=8000)
        card_data: dict[str, Any] = agent_card.model_dump()
        logger.info("Successfully fetched local agent card", agent_name=agent_name)
        return card_data

    async def fetch_agent_card(self, agent_name: str, agent_url: str) -> dict[str, Any]:
        """Fetch agent card from remote agent or local source.

        Args:
            agent_name: Name of the agent.
            agent_url: URL of the agent, or "local" to use local agent card.

        Returns:
            Agent card as a dictionary.
        """
        if agent_url.lower() == "local":
            return self.fetch_local_agent_card(agent_name)

        card_url = f"{agent_url}{AGENT_CARD_PATH}"
        logger.info("Fetching agent card", agent_name=agent_name, url=card_url)

        response = await self.http_client.get(card_url)
        response.raise_for_status()
        card_data: dict[str, Any] = response.json()
        logger.info("Successfully fetched agent card", agent_name=agent_name)
        return card_data

    async def fetch_all_agent_cards(self) -> dict[str, dict[str, Any]]:
        """Fetch all configured agent cards."""
        agent_cards = {}

        for config in self.agent_configs:
            agent_url = os.getenv(config["env_var"])
            if not agent_url:
                logger.warning(
                    "Agent URL not configured, skipping",
                    agent_name=config["name"],
                    env_var=config["env_var"],
                )
                continue

            try:
                card_data = await self.fetch_agent_card(config["name"], agent_url)
                agent_cards[config["name"]] = card_data
            except Exception as e:
                logger.error("Failed to fetch agent card", agent_name=config["name"], error=str(e))
                raise

        return agent_cards

    async def evaluate_description(self, agent_name: str, description: str) -> dict[str, Any]:
        """Evaluate agent description using LLM-as-judge."""
        prompt = f"""You are an expert AI system architect evaluating agent description quality.

        Agent descriptions should be clear, actionable, and specific to enable proper routing decisions in a multi-agent orchestration system.

        Evaluate the following agent description:

        **Agent Name:** {agent_name}

        **Description:**
        ```
        {description}
        ```

        Evaluate the description on three dimensions (1-10 scale):

        1. **Clarity** (1-10): Is the description clear, concise, and easy to understand?
        - Low (1-3): Vague, ambiguous, confusing
        - Medium (4-7): Somewhat clear but could be improved
        - High (8-10): Crystal clear, well-articulated

        2. **Actionability** (1-10): Does it clearly indicate WHEN to use this agent?
        - Low (1-3): Unclear use cases, no trigger conditions
        - Medium (4-7): Some indication of use cases but incomplete
        - High (8-10): Clear trigger conditions and use cases

        3. **Specificity** (1-10): Does it specify WHAT the agent does distinctly?
        - Low (1-3): Generic, could apply to many agents
        - Medium (4-7): Somewhat specific but lacks detail
        - High (8-10): Highly specific, distinct capabilities

        Respond in JSON format:
        {{
        "clarity_score": <float 1-10>,
        "actionability_score": <float 1-10>,
        "specificity_score": <float 1-10>,
        "overall_score": <float 1-10, average of the three>,
        "severity": "<critical|warning|good>",
        "strengths": [<list of what's good about this description>],
        "weaknesses": [<list of what needs improvement>],
        "improvement_suggestions": [<list of specific, actionable suggestions>],
        "recommended_description": "<your suggested improved description>",
        "reasoning": "<detailed explanation of your evaluation>"
        }}

        Severity guidelines:
        - critical: overall_score < 5.0 (blocks routing, needs immediate fix)
        - warning: overall_score 5.0-7.0 (works but could cause confusion)
        - good: overall_score > 7.0 (clear and effective)
        """

        logger.info("Evaluating description with LLM", agent_name=agent_name)

        response = await litellm.acompletion(
            model="openai/gemini-2.5-flash-litellm-usw1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        result: dict[str, Any] = json.loads(response.choices[0].message.content)
        result["agent_name"] = agent_name
        result["description"] = description

        logger.info(
            "Description evaluation complete",
            agent_name=agent_name,
            overall_score=result.get("overall_score"),
            severity=result.get("severity"),
        )

        return result

    async def analyze_all_descriptions(
        self, agent_cards: dict[str, dict[str, Any]]
    ) -> dict[str, Any]:
        """Evaluate all agent descriptions."""
        evaluations = []

        logger.info("Evaluating agent descriptions", agent_count=len(agent_cards))

        for agent_name, card_data in agent_cards.items():
            description = card_data.get("description", "")
            if not description:
                logger.warning("Agent has no description", agent_name=agent_name)
                continue

            evaluation = await self.evaluate_description(agent_name, description)
            evaluations.append(evaluation)

        # Categorize by severity
        critical = [e for e in evaluations if e["severity"] == "critical"]
        warning = [e for e in evaluations if e["severity"] == "warning"]
        good = [e for e in evaluations if e["severity"] == "good"]

        # Calculate averages
        avg_clarity = sum(e["clarity_score"] for e in evaluations) / len(evaluations)
        avg_actionability = sum(e["actionability_score"] for e in evaluations) / len(evaluations)
        avg_specificity = sum(e["specificity_score"] for e in evaluations) / len(evaluations)
        avg_overall = sum(e["overall_score"] for e in evaluations) / len(evaluations)

        # Generate summary
        if critical:
            summary = (
                f"🔴 CRITICAL: {len(critical)} agent(s) with poor descriptions (<5/10). "
                f"These will cause routing issues and require immediate attention."
            )
        elif warning:
            summary = (
                f"⚠️ WARNING: {len(warning)} agent(s) with suboptimal descriptions (5-7/10). "
                f"Review and improvement recommended."
            )
        else:
            summary = (
                f"✅ EXCELLENT: All {len(good)} agent descriptions are clear and effective (>7/10)."
            )

        analysis = {
            "total_evaluated": len(evaluations),
            "critical_count": len(critical),
            "warning_count": len(warning),
            "good_count": len(good),
            "evaluations": evaluations,
            "critical_issues": critical,
            "warning_issues": warning,
            "good_descriptions": good,
            "summary": summary,
            "average_scores": {
                "clarity": avg_clarity,
                "actionability": avg_actionability,
                "specificity": avg_specificity,
                "overall": avg_overall,
            },
        }

        logger.info(
            "Description evaluation complete",
            total=len(evaluations),
            critical=len(critical),
            warning=len(warning),
            good=len(good),
        )

        return analysis

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


class QualityReporter:
    """Generates HTML reports for description quality analysis."""

    @staticmethod
    def generate_report(analysis: dict[str, Any]) -> str:
        """Generate HTML report from analysis."""
        # Simple HTML generation - keeping it minimal
        avg_scores = analysis["average_scores"]

        html_parts = [
            "<!DOCTYPE html>",
            "<html><head>",
            "<title>Description Quality Analysis</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 40px; background: #f5f7fa; }",
            ".container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }",
            "h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 15px; }",
            "h2 { color: #34495e; margin-top: 30px; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }",
            ".summary { background: #e8f4f8; padding: 20px; margin: 20px 0; border-radius: 4px; border-left: 4px solid #3498db; }",
            ".stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 20px 0; }",
            ".stat-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }",
            ".stat-value { font-size: 2em; font-weight: bold; color: #2c3e50; }",
            ".stat-label { color: #6c757d; font-size: 0.9em; }",
            ".issue-card { background: white; border: 1px solid #dee2e6; padding: 20px; margin: 20px 0; border-radius: 8px; }",
            ".issue-card.critical { border-left: 4px solid #e74c3c; background: #fef5f5; }",
            ".issue-card.warning { border-left: 4px solid #f39c12; background: #fffbf0; }",
            ".issue-card.good { border-left: 4px solid #27ae60; background: #f0fdf4; }",
            ".score { display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; margin: 5px; color: white; }",
            ".score.critical { background: #e74c3c; }",
            ".score.warning { background: #f39c12; }",
            ".score.good { background: #27ae60; }",
            ".description-box { background: #f8f9fa; padding: 15px; border-radius: 4px; margin: 15px 0; font-family: monospace; font-size: 0.9em; }",
            ".recommendation-box { background: #e8f5e9; padding: 15px; border-radius: 4px; margin: 15px 0; font-family: monospace; font-size: 0.9em; }",
            "ul { margin: 15px 0; padding-left: 30px; }",
            "li { margin: 8px 0; }",
            "</style>",
            "</head><body><div class='container'>",
            "<h1>🎯 Agent Description Quality Analysis</h1>",
            f"<div class='summary'>{analysis['summary']}</div>",
            "<h2>📊 Statistics</h2>",
            "<div class='stats'>",
            f"<div class='stat-card'><div class='stat-label'>Total Evaluated</div><div class='stat-value'>{analysis['total_evaluated']}</div></div>",
            f"<div class='stat-card'><div class='stat-label'>Critical 🔴</div><div class='stat-value'>{analysis['critical_count']}</div></div>",
            f"<div class='stat-card'><div class='stat-label'>Warnings 🟡</div><div class='stat-value'>{analysis['warning_count']}</div></div>",
            f"<div class='stat-card'><div class='stat-label'>Good 🟢</div><div class='stat-value'>{analysis['good_count']}</div></div>",
            "</div>",
            "<h2>📈 Average Scores</h2>",
            "<div class='stats'>",
            f"<div class='stat-card'><div class='stat-label'>Clarity</div><div class='stat-value'>{avg_scores['clarity']:.1f}/10</div></div>",
            f"<div class='stat-card'><div class='stat-label'>Actionability</div><div class='stat-value'>{avg_scores['actionability']:.1f}/10</div></div>",
            f"<div class='stat-card'><div class='stat-label'>Specificity</div><div class='stat-value'>{avg_scores['specificity']:.1f}/10</div></div>",
            f"<div class='stat-card'><div class='stat-label'>Overall</div><div class='stat-value'>{avg_scores['overall']:.1f}/10</div></div>",
            "</div>",
        ]

        # Add critical issues
        if analysis["critical_issues"]:
            html_parts.append("<h2>🔴 Critical Issues</h2>")
            for issue in analysis["critical_issues"]:
                html_parts.extend(
                    [
                        "<div class='issue-card critical'>",
                        f"<h3>{issue['agent_name']}</h3>",
                        f"<span class='score critical'>Overall: {issue['overall_score']:.1f}/10</span>",
                        f"<span class='score critical'>Clarity: {issue['clarity_score']:.1f}/10</span>",
                        f"<span class='score critical'>Actionability: {issue['actionability_score']:.1f}/10</span>",
                        f"<span class='score critical'>Specificity: {issue['specificity_score']:.1f}/10</span>",
                        f"<h4>Current Description:</h4><div class='description-box'>{issue['description']}</div>",
                        "<h4>❌ Weaknesses:</h4><ul>",
                    ]
                )
                for weakness in issue.get("weaknesses", []):
                    html_parts.append(f"<li>{weakness}</li>")
                html_parts.append("</ul><h4>💡 Improvement Suggestions:</h4><ul>")
                for suggestion in issue.get("improvement_suggestions", []):
                    html_parts.append(f"<li>{suggestion}</li>")
                html_parts.extend(
                    [
                        "</ul>",
                        f"<h4>✨ Recommended:</h4><div class='recommendation-box'>{issue.get('recommended_description', 'N/A')}</div>",
                        "</div>",
                    ]
                )

        # Add warning issues
        if analysis["warning_issues"]:
            html_parts.append("<h2>🟡 Warning Issues</h2>")
            for issue in analysis["warning_issues"]:
                html_parts.extend(
                    [
                        "<div class='issue-card warning'>",
                        f"<h3>{issue['agent_name']}</h3>",
                        f"<span class='score warning'>Overall: {issue['overall_score']:.1f}/10</span>",
                        "<h4>💡 Improvement Suggestions:</h4><ul>",
                    ]
                )
                for suggestion in issue.get("improvement_suggestions", []):
                    html_parts.append(f"<li>{suggestion}</li>")
                html_parts.append("</ul></div>")

        # Add good descriptions
        if analysis["good_descriptions"]:
            html_parts.append("<h2>🟢 Good Descriptions</h2>")
            for desc in analysis["good_descriptions"]:
                html_parts.extend(
                    [
                        "<div class='issue-card good'>",
                        f"<h3>{desc['agent_name']}</h3>",
                        f"<span class='score good'>Overall: {desc['overall_score']:.1f}/10</span>",
                        "<h4>✅ Strengths:</h4><ul>",
                    ]
                )
                for strength in desc.get("strengths", []):
                    html_parts.append(f"<li>{strength}</li>")
                html_parts.append("</ul></div>")

        html_parts.extend(["</div></body></html>"])
        return "\n".join(html_parts)

    @staticmethod
    def save_report(report_content: str, output_path: str):
        """Save HTML report to file."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(report_content)
        logger.info("Saved description quality report", path=output_path)


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.agent_card
@pytest.mark.skipif(
    not os.getenv("LITELLM_API_BASE") or not os.getenv("LITELLM_API_KEY"),
    reason="LITELLM_API_BASE and LITELLM_API_KEY environment variables required",
)
async def test_agent_description_quality(agent_configs):
    """Integration test to validate agent description quality.

    This test:
    1. Fetches all agent cards
    2. Evaluates each description using LLM-as-judge
    3. Scores clarity, actionability, and specificity
    4. Logs results with structlog
    5. Generates HTML report (if enabled)
    6. Fails if critical issues exist (score < 5/10)

    Args:
        agent_configs: Pytest fixture providing list of agent configurations.

    Environment Variables Required:
        LITELLM_API_BASE: LiteLLM API endpoint (e.g., https://llm-uat.cotality.com)
        LITELLM_API_KEY: LiteLLM API key for authentication
    """
    analyzer = DescriptionQualityAnalyzer(agent_configs)

    try:
        # Step 1: Fetch all agent cards
        logger.info("Fetching all agent cards...")
        agent_cards = await analyzer.fetch_all_agent_cards()
        assert len(agent_cards) >= 1, "Need at least 1 agent to evaluate"
        logger.info("Fetched agent cards", count=len(agent_cards))

        # Step 2: Analyze all descriptions
        logger.info("Analyzing agent descriptions...")
        analysis = await analyzer.analyze_all_descriptions(agent_cards)

        # Step 3: Log results with structlog
        logger.info(
            "Description quality analysis complete",
            total_evaluated=analysis["total_evaluated"],
            critical_count=analysis["critical_count"],
            warning_count=analysis["warning_count"],
            good_count=analysis["good_count"],
            summary=analysis["summary"],
            average_scores=analysis["average_scores"],
        )

        # Log detailed information for critical issues
        if analysis["critical_issues"]:
            for issue in analysis["critical_issues"]:
                logger.error(
                    "Critical description quality issue",
                    agent_name=issue["agent_name"],
                    overall_score=issue["overall_score"],
                    clarity_score=issue["clarity_score"],
                    actionability_score=issue["actionability_score"],
                    specificity_score=issue["specificity_score"],
                    weaknesses=issue.get("weaknesses", []),
                    improvement_suggestions=issue.get("improvement_suggestions", []),
                )

        # Log warnings
        if analysis["warning_issues"]:
            for issue in analysis["warning_issues"]:
                logger.info(
                    "Description quality warning",
                    agent_name=issue["agent_name"],
                    overall_score=issue["overall_score"],
                    improvement_suggestions=issue.get("improvement_suggestions", []),
                )

        # Step 4: Generate HTML report if enabled
        if os.getenv("GENERATE_DESCRIPTION_REPORT", "true").lower() == "true":
            logger.info("Generating HTML report...")
            report = QualityReporter.generate_report(analysis)
            QualityReporter.save_report(report, HTML_OUTPUT_PATH)
            logger.info("Report saved", path=HTML_OUTPUT_PATH)

        # Step 5: Alert on critical issues
        if analysis["critical_count"] > 0:
            critical_details = "\n".join(
                [
                    f"  - {issue['agent_name']}: score={issue['overall_score']:.1f}/10"
                    for issue in analysis["critical_issues"]
                ]
            )

            pytest.fail(
                f"""🔴 Description quality test FAILED!\n
                Found {analysis["critical_count"]} agent(s) with poor descriptions (<{MIN_ACCEPTABLE_SCORE}/10):\n
                {critical_details}\n
                These descriptions are too vague and will cause routing issues.\n
                Review improvement suggestions in the report: {HTML_OUTPUT_PATH}"""
            )

        # Warn on medium-quality issues
        if analysis["warning_count"] > 0:
            logger.warning(
                f"Portfolio has {analysis['warning_count']} agent(s) with suboptimal descriptions. "
                f"Review recommended but not critical.",
                warning_count=analysis["warning_count"],
            )

        logger.info("✅ Description quality validation passed!", summary=analysis["summary"])

    finally:
        await analyzer.close()
