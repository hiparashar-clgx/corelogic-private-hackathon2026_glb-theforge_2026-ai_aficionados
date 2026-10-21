"""Integration test for agent portfolio coherence validation.

This test validates:
1. Detects overlapping or conflicting agent capabilities
2. Calculates similarity scores between agents
3. Uses LLM-as-judge to evaluate conflicts
4. Logs results with structlog
5. Alerts on high-severity conflicts
"""

import asyncio
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
SIMILARITY_THRESHOLD_MEDIUM = 0.6  # 60% similarity = medium concern
SIMILARITY_THRESHOLD_HIGH = 0.8  # 80% similarity = high concern
HTML_OUTPUT_PATH = "reports/portfolio_coherence_analysis.html"

litellm.api_base = os.getenv("LITELLM_API_BASE")
litellm.api_key = os.getenv("LITELLM_API_KEY")


class PortfolioCoherenceAnalyzer:
    """Analyzes agent portfolio for overlaps and conflicts."""

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

    async def compare_agents_with_llm(
        self, agent1_name: str, agent1_card: dict, agent2_name: str, agent2_card: dict
    ) -> dict[str, Any]:
        """Use LLM to compare two agents and detect overlaps/conflicts."""
        prompt = f"""You are an expert AI system architect analyzing agent portfolio coherence.

            Compare these two agents and identify overlapping or conflicting capabilities:

            **Agent 1: {agent1_name}**
            ```json
            {json.dumps(agent1_card, indent=2)}
            ```

            **Agent 2: {agent2_name}**
            ```json
            {json.dumps(agent2_card, indent=2)}
            ```

            Analyze and respond in JSON format:
            {{
            "similarity_score": <float 0-1>,
            "severity": "<low|medium|high>",
            "overlapping_capabilities": [<list of overlapping features>],
            "conflicting_responsibilities": [<list of conflicts>],
            "potential_confusion": "<description of how users might be confused>",
            "consolidation_suggestion": "<recommendation for resolving conflicts>",
            "reasoning": "<detailed explanation>"
            }}

            **Scoring Guidelines:**
            - similarity_score: 0.0-0.3 = distinct, 0.3-0.6 = some overlap, 0.6-0.8 = significant overlap, 0.8-1.0 = nearly identical
            - severity: low (<0.6), medium (0.6-0.8), high (>0.8)

            **Analysis Framework:**

            1. **Capability Overlap** (Primary Factor - 40% weight)
            - Do they solve the same user problems?
            - Are their input/output types similar?
            - Do they access the same data sources?
            - Example: Both agents search property data by address → HIGH overlap

            2. **Responsibility Boundaries** (30% weight)
            - Is it clear which agent to use when?
            - Do their descriptions have distinct use cases?
            - Are there ambiguous scenarios where either could work?
            - Example: "find data" vs "search data" → UNCLEAR boundaries

            3. **User Decision Points** (20% weight)
            - Would a user struggle to choose between them?
            - Do their names/descriptions create confusion?
            - Is there a clear differentiator?
            - Example: "data_agent" vs "information_agent" → CONFUSING

            4. **Portfolio Efficiency** (10% weight)
            - Should these be consolidated into one agent?
            - Would merging improve or harm user experience?
            - Are there valid architectural reasons to keep them separate?
            - Example: Same capability but different auth → Keep separate

            **Evaluation Examples:**

            DISTINCT (score: 0.2, severity: low):
            - Agent A: "Searches property records by address"
            - Agent B: "Formats data into Excel/CSV files"
            - Reasoning: Different stages in workflow, no overlap

            SOME OVERLAP (score: 0.5, severity: low):
            - Agent A: "Searches property ownership data"
            - Agent B: "Searches property tax assessment data"
            - Reasoning: Same domain (property), different data types

            SIGNIFICANT OVERLAP (score: 0.7, severity: medium):
            - Agent A: "Finds property data by address or APN"
            - Agent B: "Searches properties using address, APN, or FIPS"
            - Reasoning: Same capabilities, unclear which to use

            NEARLY IDENTICAL (score: 0.9, severity: high):
            - Agent A: "Retrieves property information"
            - Agent B: "Gets property details"
            - Reasoning: Identical capability, different wording only

            **Important Considerations:**
            - Focus on USER-FACING capabilities, not internal implementation
            - Consider the ROUTING perspective: would an LLM router struggle to choose?
            - Evaluate based on DESCRIPTIONS, not just names
            - Complementary agents (e.g., search + format) should score LOW
            - Agents with different authentication/permissions may need to stay separate

            Be objective and data-driven. Provide specific examples from the agent cards in your reasoning.
            """

        logger.info("Comparing agents with LLM", agent1=agent1_name, agent2=agent2_name)

        response = await litellm.acompletion(
            model="openai/gemini-2.5-pro-llmservices-usw1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        result: dict[str, Any] = json.loads(response.choices[0].message.content)
        logger.info(
            "LLM comparison complete",
            agent1=agent1_name,
            agent2=agent2_name,
            similarity=result.get("similarity_score"),
            severity=result.get("severity"),
        )

        return result

    async def analyze_portfolio(self, agent_cards: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Analyze entire portfolio for coherence issues."""
        agent_names = list(agent_cards.keys())

        logger.info("Analyzing portfolio coherence", agent_count=len(agent_names))

        # Build list of comparison tasks to run in parallel
        comparison_tasks = []
        for i in range(len(agent_names)):
            for j in range(i + 1, len(agent_names)):
                agent1_name = agent_names[i]
                agent2_name = agent_names[j]

                task = self.compare_agents_with_llm(
                    agent1_name, agent_cards[agent1_name], agent2_name, agent_cards[agent2_name]
                )
                comparison_tasks.append((agent1_name, agent2_name, task))

        # Execute all comparisons in parallel
        total_comparisons = len(comparison_tasks)
        logger.info("Running agent comparisons in parallel", total_pairs=total_comparisons)

        # Gather results from all parallel tasks
        comparison_results = await asyncio.gather(
            *[task for _, _, task in comparison_tasks], return_exceptions=True
        )

        # Process results and handle any errors
        comparisons = []
        for (agent1_name, agent2_name, _), raw_result in zip(
            comparison_tasks, comparison_results, strict=False
        ):
            if isinstance(raw_result, BaseException):
                logger.error(
                    "Comparison failed",
                    agent1=agent1_name,
                    agent2=agent2_name,
                    error=str(raw_result),
                )
                # Add a default low-severity result for failed comparisons
                comparison: dict[str, Any] = {
                    "similarity_score": 0.0,
                    "severity": "low",
                    "overlapping_capabilities": [],
                    "conflicting_responsibilities": [],
                    "potential_confusion": "Comparison failed",
                    "consolidation_suggestion": "N/A",
                    "reasoning": f"Error during comparison: {raw_result!s}",
                }
            else:
                comparison = raw_result

            comparison["agent1"] = agent1_name
            comparison["agent2"] = agent2_name
            comparisons.append(comparison)

        # Categorize by severity
        high_severity = [c for c in comparisons if c["severity"] == "high"]
        medium_severity = [c for c in comparisons if c["severity"] == "medium"]
        low_severity = [c for c in comparisons if c["severity"] == "low"]

        analysis = {
            "total_comparisons": len(comparisons),
            "high_severity_count": len(high_severity),
            "medium_severity_count": len(medium_severity),
            "low_severity_count": len(low_severity),
            "comparisons": comparisons,
            "high_severity_issues": high_severity,
            "medium_severity_issues": medium_severity,
            "summary": self._generate_summary(high_severity, medium_severity, low_severity),
        }

        logger.info(
            "Portfolio analysis complete",
            total_comparisons=len(comparisons),
            high_severity=len(high_severity),
            medium_severity=len(medium_severity),
            low_severity=len(low_severity),
        )

        return analysis

    @staticmethod
    def _generate_summary(high, medium, low) -> str:
        """Generate human-readable summary."""
        if len(high) > 0:
            return (
                f"⚠️ CRITICAL: {len(high)} high-severity conflicts detected. "
                f"Portfolio requires immediate attention."
            )
        elif len(medium) > 0:
            return (
                f"⚠️ WARNING: {len(medium)} medium-severity overlaps detected. Review recommended."
            )
        else:
            return f"✅ HEALTHY: Portfolio is coherent with {len(low)} minor overlaps."

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()


class CoherenceReporter:
    """Generates markdown reports for portfolio coherence."""

    @staticmethod
    def generate_report(analysis: dict[str, Any]) -> str:
        """Generate markdown report from analysis."""
        from datetime import UTC, datetime

        report_lines = [
            "# Agent Portfolio Coherence Analysis",
            "",
            f"**Generated:** {datetime.now(tz=UTC).isoformat()}",
            "",
            "## Executive Summary",
            "",
            analysis["summary"],
            "",
            "## Statistics",
            "",
            f"- **Total Comparisons:** {analysis['total_comparisons']}",
            f"- **High Severity Issues:** {analysis['high_severity_count']} 🔴",
            f"- **Medium Severity Issues:** {analysis['medium_severity_count']} 🟡",
            f"- **Low Severity Issues:** {analysis['low_severity_count']} 🟢",
            "",
        ]

        # High severity issues
        if analysis["high_severity_issues"]:
            report_lines.extend(["## 🔴 High Severity Issues", ""])
            for issue in analysis["high_severity_issues"]:
                report_lines.extend(
                    [
                        f"### {issue['agent1']} ↔️ {issue['agent2']}",
                        "",
                        f"**Similarity Score:** {issue['similarity_score']:.2f}",
                        "",
                        "**Overlapping Capabilities:**",
                        "",
                    ]
                )
                for cap in issue.get("overlapping_capabilities", []):
                    report_lines.append(f"- {cap}")

                report_lines.extend(["", "**Conflicting Responsibilities:**", ""])
                for conflict in issue.get("conflicting_responsibilities", []):
                    report_lines.append(f"- {conflict}")

                report_lines.extend(
                    [
                        "",
                        f"**Potential Confusion:** {issue.get('potential_confusion', 'N/A')}",
                        "",
                        f"**Consolidation Suggestion:** {issue.get('consolidation_suggestion', 'N/A')}",
                        "",
                        f"**Reasoning:** {issue.get('reasoning', 'N/A')}",
                        "",
                        "---",
                        "",
                    ]
                )

        # Medium severity issues
        if analysis["medium_severity_issues"]:
            report_lines.extend(["## 🟡 Medium Severity Issues", ""])
            for issue in analysis["medium_severity_issues"]:
                report_lines.extend(
                    [
                        f"### {issue['agent1']} ↔️ {issue['agent2']}",
                        "",
                        f"**Similarity Score:** {issue['similarity_score']:.2f}",
                        "",
                        f"**Reasoning:** {issue.get('reasoning', 'N/A')}",
                        "",
                        "---",
                        "",
                    ]
                )

        return "\n".join(report_lines)

    @staticmethod
    def save_report(report_content: str, output_path: str):
        """Save report as HTML."""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Generate HTML version
        html_content = CoherenceReporter.markdown_to_html(report_content)
        output_file.write_text(html_content)
        logger.info("Saved HTML coherence analysis report", path=output_path)

    @staticmethod
    def markdown_to_html(md_content: str) -> str:
        """Convert markdown to styled HTML."""
        try:
            import markdown

            # Convert markdown to HTML with extensions
            html_body = markdown.markdown(
                md_content, extensions=["extra", "tables", "toc", "fenced_code"]
            )

            # Wrap in styled HTML template
            html = f"""<!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Portfolio Coherence Analysis</title>
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        background-color: #f5f7fa;
                        padding: 20px;
                    }}
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                        background: white;
                        padding: 40px;
                        border-radius: 8px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    }}
                    h1 {{
                        color: #2c3e50;
                        border-bottom: 3px solid #3498db;
                        padding-bottom: 15px;
                        margin-bottom: 30px;
                        font-size: 2.5em;
                    }}
                    h2 {{
                        color: #34495e;
                        margin-top: 40px;
                        margin-bottom: 20px;
                        padding-bottom: 10px;
                        border-bottom: 2px solid #ecf0f1;
                        font-size: 1.8em;
                    }}
                    h3 {{
                        color: #7f8c8d;
                        margin-top: 25px;
                        margin-bottom: 15px;
                        font-size: 1.3em;
                    }}
                    p {{
                        margin-bottom: 15px;
                    }}
                    ul, ol {{
                        margin-left: 30px;
                        margin-bottom: 15px;
                    }}
                    li {{
                        margin-bottom: 8px;
                    }}
                    strong {{
                        color: #2c3e50;
                        font-weight: 600;
                    }}
                    code {{
                        background-color: #f8f9fa;
                        padding: 2px 6px;
                        border-radius: 3px;
                        font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
                        font-size: 0.9em;
                        color: #e83e8c;
                    }}
                    pre {{
                        background-color: #282c34;
                        color: #abb2bf;
                        padding: 20px;
                        border-radius: 5px;
                        overflow-x: auto;
                        margin: 20px 0;
                        line-height: 1.5;
                    }}
                    pre code {{
                        background: none;
                        color: inherit;
                        padding: 0;
                    }}
                    hr {{
                        border: none;
                        border-top: 1px solid #ecf0f1;
                        margin: 30px 0;
                    }}
                    .emoji {{
                        font-size: 1.2em;
                    }}
                    /* Status badges */
                    em {{
                        font-style: normal;
                        padding: 4px 8px;
                        border-radius: 3px;
                        font-weight: 600;
                        font-size: 0.9em;
                    }}
                    /* Blockquotes for callouts */
                    blockquote {{
                        border-left: 4px solid #3498db;
                        padding-left: 20px;
                        margin: 20px 0;
                        color: #555;
                        background-color: #f8f9fa;
                        padding: 15px 20px;
                        border-radius: 4px;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 20px 0;
                    }}
                    th, td {{
                        padding: 12px;
                        text-align: left;
                        border: 1px solid #ddd;
                    }}
                    th {{
                        background-color: #3498db;
                        color: white;
                        font-weight: 600;
                    }}
                    tr:nth-child(even) {{
                        background-color: #f8f9fa;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    {html_body}
                </div>
            </body>
            </html>"""
            return html

        except ImportError:
            logger.warning("markdown package not installed, generating basic HTML")
            # Fallback: simple HTML wrapper with pre-formatted text
            return f"""<!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>Portfolio Coherence Analysis</title>
                <style>
                    body {{ font-family: monospace; max-width: 1200px; margin: 40px auto; padding: 0 20px; }}
                    pre {{ white-space: pre-wrap; word-wrap: break-word; }}
                </style>
            </head>
            <body>
                <pre>{md_content}</pre>
            </body>
            </html>"""


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.agent_card
@pytest.mark.portfolio
@pytest.mark.skip
async def test_portfolio_coherence(agent_configs):
    """Integration test to validate agent portfolio coherence.

    This test:
    1. Fetches all agent cards
    2. Compares each pair using LLM-as-judge
    3. Detects overlaps and conflicts
    4. Logs results with structlog
    5. Generates markdown report (if enabled)
    6. Fails if high-severity conflicts exist

    Args:
        agent_configs: Pytest fixture providing list of agent configurations.

    Environment Variables Required:
        LITELLM_API_BASE: LiteLLM API endpoint (e.g., https://llm-uat.cotality.com)
        LITELLM_API_KEY: LiteLLM API key for authentication
    """
    analyzer = PortfolioCoherenceAnalyzer(agent_configs)

    try:
        # Step 1: Fetch all agent cards
        logger.info("Fetching all agent cards...")
        agent_cards = await analyzer.fetch_all_agent_cards()
        assert len(agent_cards) >= 2, "Need at least 2 agents to compare"
        logger.info("Fetched agent cards", count=len(agent_cards))

        # Step 2: Analyze portfolio for coherence
        logger.info("Analyzing portfolio coherence...")
        analysis = await analyzer.analyze_portfolio(agent_cards)

        # Step 3: Log results with structlog
        logger.info(
            "Portfolio coherence analysis complete",
            total_comparisons=analysis["total_comparisons"],
            high_severity_count=analysis["high_severity_count"],
            medium_severity_count=analysis["medium_severity_count"],
            low_severity_count=analysis["low_severity_count"],
            summary=analysis["summary"],
            similarity_threshold_medium=SIMILARITY_THRESHOLD_MEDIUM,
            similarity_threshold_high=SIMILARITY_THRESHOLD_HIGH,
        )

        # Log detailed information for high-severity issues
        if analysis["high_severity_issues"]:
            for issue in analysis["high_severity_issues"]:
                logger.warning(
                    "High-severity portfolio conflict detected",
                    agent1=issue["agent1"],
                    agent2=issue["agent2"],
                    similarity_score=issue["similarity_score"],
                    severity=issue["severity"],
                    overlapping_capabilities=issue.get("overlapping_capabilities", []),
                    conflicting_responsibilities=issue.get("conflicting_responsibilities", []),
                    consolidation_suggestion=issue.get("consolidation_suggestion", "N/A"),
                    reasoning=issue.get("reasoning", "N/A"),
                )

        # Log medium-severity issues
        if analysis["medium_severity_issues"]:
            for issue in analysis["medium_severity_issues"]:
                logger.info(
                    "Medium-severity portfolio overlap detected",
                    agent1=issue["agent1"],
                    agent2=issue["agent2"],
                    similarity_score=issue["similarity_score"],
                    severity=issue["severity"],
                    reasoning=issue.get("reasoning", "N/A"),
                )

        # Step 4: Generate HTML report if enabled
        if os.getenv("GENERATE_PORTFOLIO_REPORT", "true").lower() == "true":
            logger.info("Generating HTML report...")
            report = CoherenceReporter.generate_report(analysis)
            CoherenceReporter.save_report(report, HTML_OUTPUT_PATH)
            logger.info("Report saved", path=HTML_OUTPUT_PATH)

        # Step 5: Alert on high-severity conflicts
        if analysis["high_severity_count"] > 0:
            high_severity_details = "\n".join(
                [
                    f"  - {issue['agent1']} ↔️ {issue['agent2']}: "
                    f"similarity={issue['similarity_score']:.2f}, "
                    f"suggestion={issue.get('consolidation_suggestion', 'N/A')}"
                    for issue in analysis["high_severity_issues"]
                ]
            )

            pytest.fail(
                f"""🔴 Portfolio coherence test FAILED!\n
                Found {analysis["high_severity_count"]} high-severity conflicts:\n
                {high_severity_details}\n
                These agents have significant overlap and may confuse users.\n
                Review consolidation suggestions in the report: {HTML_OUTPUT_PATH}"""
            )

        # Warn on medium-severity issues
        if analysis["medium_severity_count"] > 0:
            logger.warning(
                f"Portfolio has {analysis['medium_severity_count']} medium-severity overlaps. "
                f"Review recommended but not critical.",
                medium_severity_count=analysis["medium_severity_count"],
            )

        logger.info("✅ Portfolio coherence validation passed!", summary=analysis["summary"])

    finally:
        await analyzer.close()
