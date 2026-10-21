# Agent Card Validation Tests

This directory contains validation tests for agent description quality and portfolio coherence. These tests help ensure your agent cards are clear, well-documented, and don't conflict with other agents in your portfolio.

## Overview

These tests are designed to work with both **single-agent repositories** and **multi-agent portfolios**:

- **Single Agent**: Run description quality validation on your agent
- **Multiple Agents**: Additionally validate portfolio coherence and detect overlaps

## Tests

### 1. `test_agent_description_quality.py`
Validates individual agent descriptions for clarity, actionability, and specificity using LLM-as-judge.

**What it tests:**
- **Clarity** (1-10): Is the description clear and understandable?
- **Actionability** (1-10): Does it explain WHEN to use the agent?
- **Specificity** (1-10): Does it explain WHAT the agent does distinctly?

**Fails if:** Any agent scores < 5.0

**Generates:** HTML report at `reports/description_quality_analysis.html`

**Use case:** Validate your agent's description before deployment or as part of CI/CD

### 2. `test_coherence_validation.py`
Validates the entire agent portfolio for overlaps and conflicts between agents.

**What it tests:**
- Capability overlap between agent pairs
- Conflicting responsibilities
- Similarity scores (0-1 scale)
- User confusion potential

**Fails if:** High-severity conflicts detected (similarity > 0.8)

**Generates:** HTML report at `reports/portfolio_coherence_analysis.html`

**Use case:** Multi-agent systems to detect redundant or conflicting capabilities

**Note:** Requires at least 2 agents. Automatically skipped for single-agent configurations.

### 3. `test_examples.py`
Contains example code showing how to use both tests programmatically.

## Quick Start

### Prerequisites

**Important:** The tests will automatically **skip** if `LITELLM_API_BASE` and `LITELLM_API_KEY` 
are not set, making it safe to run without credentials.

Set required environment variables:
```bash
# LiteLLM configuration (required for tests to run)
export LITELLM_API_BASE="https://llm-uat.cotality.com"
export LITELLM_API_KEY="your-api-key"

# By default, tests use local agent card (no AGENT_URL needed!)
# To override and use remote agent:
export USE_LOCAL_AGENT_CARD=false
export AGENT_URL="http://localhost:8000"

# For multi-agent portfolio tests:
export ADDITIONAL_AGENT_URLS="https://agent2.example.com,https://agent3.example.com"
```

### Run Tests

```bash
# Install dependencies first
uv sync --extra dev

# Run with local agent card (DEFAULT - no server needed!)
# Note: Tests will SKIP if LITELLM_API_BASE/KEY are not set
export LITELLM_API_BASE="https://llm-uat.cotality.com"
export LITELLM_API_KEY="your-api-key"
GENERATE_DESCRIPTION_REPORT=true uv run pytest tests/integration/agent_card/test_agent_description_quality.py -v

# Run without credentials (tests will skip gracefully)
uv run pytest tests/integration/agent_card/test_agent_description_quality.py -v

# Run description quality validation (remote agent)
export USE_LOCAL_AGENT_CARD=false
export AGENT_URL=http://localhost:8000
GENERATE_DESCRIPTION_REPORT=true uv run pytest tests/integration/agent_card/test_agent_description_quality.py -v

# Run portfolio coherence validation (multiple agents)
export USE_LOCAL_AGENT_CARD=false
export AGENT_URL=http://localhost:8000
export ADDITIONAL_AGENT_URLS=http://agent2:8000,http://agent3:8000
GENERATE_PORTFOLIO_REPORT=true uv run pytest tests/integration/agent_card/test_coherence_validation.py -v

# Run both
GENERATE_DESCRIPTION_REPORT=true GENERATE_PORTFOLIO_REPORT=true \
  uv run pytest tests/integration/agent_card/ -v

# Run only specific markers
uv run pytest tests/integration/agent_card/ -v -m agent_card
uv run pytest tests/integration/agent_card/ -v -m portfolio
```

## Reports

Both tests generate styled HTML reports that can be archived as Jenkins artifacts:

- `reports/description_quality_analysis.html` - Individual agent description scores
- `reports/portfolio_coherence_analysis.html` - Portfolio-wide conflict analysis

## Configuration

### Local Agent Card (Development Mode)

**DEFAULT BEHAVIOR:** The tests use the local agent card by default!

This means the template passes agent card validation tests out of the box without 
needing to start a server. The tests import your `MyAgent` class directly from 
`src.cotality.agent.agent` and use its `get_agent_card()` method.

```bash
# Run tests with defaults (uses local agent card)
export LITELLM_API_BASE="https://llm-uat.cotality.com"
export LITELLM_API_KEY="your-api-key"
uv run pytest tests/integration/agent_card/test_agent_description_quality.py -v
```

To test against a running agent server instead, set `USE_LOCAL_AGENT_CARD=false`:

```bash
# Test against running server
export USE_LOCAL_AGENT_CARD=false
export AGENT_URL=http://localhost:8000
export LITELLM_API_BASE="https://llm-uat.cotality.com"
export LITELLM_API_KEY="your-api-key"
uv run pytest tests/integration/agent_card/test_agent_description_quality.py -v
```

This is perfect for:
- **Template users**: Tests pass immediately without setup
- **Development**: Test agent card changes without deploying
- **CI/CD**: Validate descriptions before building containers
- **Rapid iteration**: Get feedback on agent card quality instantly

### Dynamic Configuration (Default for Template)

The tests use the `agent_configs` fixture from `conftest.py` which dynamically builds 
the agent list from environment variables.

**By default**, tests use the local agent card (no server required):

```python
# Default: Local agent card (no server needed)
# No environment variables required!

# Explicitly use local agent card
export USE_LOCAL_AGENT_CARD=true

# Use remote agent instead
export USE_LOCAL_AGENT_CARD=false
export AGENT_URL=http://localhost:8000

# Multiple remote agents (for teams with agent portfolios)
export USE_LOCAL_AGENT_CARD=false
export AGENT_URL=http://localhost:8000
export ADDITIONAL_AGENT_URLS=http://agent2:8000,http://agent3:8000

# Mixed: local agent + remote agents for portfolio testing
export USE_LOCAL_AGENT_CARD=true
export ADDITIONAL_AGENT_URLS=http://agent2:8000,http://agent3:8000
```

### Static Configuration (For Production Portfolios)

For teams managing multiple known agents, override the fixture in your project's 
`tests/integration/agent_card/conftest.py`:

```python
import pytest

# Hardcoded list of your agents
AGENT_CONFIGS = [
    {"name": "documentation_agent", "env_var": "DOCUMENTATION_AGENT_URL"},
    {"name": "search_agent", "env_var": "SEARCH_AGENT_URL"},
    {"name": "formatter_agent", "env_var": "FORMATTER_AGENT_URL"},
]


@pytest.fixture
def agent_configs():
    return AGENT_CONFIGS
```

Then set the corresponding environment variables:
```bash
export DOCUMENTATION_AGENT_URL=https://docs-agent.example.com
export SEARCH_AGENT_URL=https://search-agent.example.com
export FORMATTER_AGENT_URL=https://format-agent.example.com
```

## Thresholds

### Description Quality
- **Critical**: < 5.0/10 (test fails)
- **Warning**: 5.0-7.0/10 (test passes with warning)
- **Good**: > 7.0/10

### Portfolio Coherence
- **High severity**: similarity > 0.8 (test fails)
- **Medium severity**: similarity 0.6-0.8 (test passes with warning)
- **Low severity**: similarity < 0.6

## CI/CD Integration

### Jenkins

Example Jenkins pipeline stages for running these tests.

**Note:** By default, tests use the local agent card (no server needed). This is 
recommended for most use cases as it validates the agent card during the build 
without requiring a running server.

```groovy
// Agent Description Quality (Default: Uses Local Agent Card)
stage('Agent Description Quality') {
    steps {
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
            sh """
                export LITELLM_API_BASE='${env.LITELLM_API_BASE}'
                export LITELLM_API_KEY='${env.LITELLM_API_KEY}'
                export GENERATE_DESCRIPTION_REPORT='true'
                uv run pytest tests/integration/agent_card/test_agent_description_quality.py -v
            """
        }
    }
    post {
        always {
            archiveArtifacts artifacts: 'reports/description_quality_analysis.html', 
                           allowEmptyArchive: true
        }
    }
}

// Agent Description Quality (Alternative: Using Deployed Agent)
stage('Agent Description Quality - Remote') {
    when {
        expression { env.AGENT_URL != null }
    }
    steps {
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
            sh """
                export LITELLM_API_BASE='${env.LITELLM_API_BASE}'
                export LITELLM_API_KEY='${env.LITELLM_API_KEY}'
                export USE_LOCAL_AGENT_CARD='false'
                export AGENT_URL='${env.AGENT_URL}'
                export GENERATE_DESCRIPTION_REPORT='true'
                uv run pytest tests/integration/agent_card/test_agent_description_quality.py -v
            """
        }
    }
    post {
        always {
            archiveArtifacts artifacts: 'reports/description_quality_analysis.html', 
                           allowEmptyArchive: true
        }
    }
}

// Portfolio Coherence (only for multi-agent portfolios)
stage('Portfolio Coherence') {
    when {
        expression { env.ADDITIONAL_AGENT_URLS != null }
    }
    steps {
        catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
            sh """
                export LITELLM_API_BASE='${env.LITELLM_API_BASE}'
                export LITELLM_API_KEY='${env.LITELLM_API_KEY}'
                export ADDITIONAL_AGENT_URLS='${env.ADDITIONAL_AGENT_URLS}'
                export GENERATE_PORTFOLIO_REPORT='true'
                uv run pytest tests/integration/agent_card/test_coherence_validation.py -v
            """
        }
    }
    post {
        always {
            archiveArtifacts artifacts: 'reports/portfolio_coherence_analysis.html', 
                           allowEmptyArchive: true
        }
    }
}
```

For teams with multiple agents, customize `conftest.py`:

```python
import pytest

# Define your agent portfolio
AGENT_CONFIGS = [
    {"name": "my_agent_1", "env_var": "AGENT_1_URL"},
    {"name": "my_agent_2", "env_var": "AGENT_2_URL"},
]


@pytest.fixture
def agent_configs():
    return AGENT_CONFIGS
```

## Examples

See `test_examples.py` for usage examples including:
- Basic validation
- Custom thresholds
- Programmatic report generation
- Batch processing
- Integration with existing tests

## Architecture

Both tests follow the same pattern:

```
Analyzer Class
├── fetch_agent_card()
├── fetch_all_agent_cards()
└── analyze_*()

Reporter Class
├── generate_report()
└── save_report()

Pytest Test Function
├── Initialize Analyzer
├── Fetch agent cards
├── Analyze
├── Log results
├── Generate HTML report
└── Fail if critical issues
```

This consistent structure makes them easy to understand and maintain.

## Troubleshooting

### Tests are skipped
**Message:** `SKIPPED - LITELLM_API_BASE and LITELLM_API_KEY environment variables required`

**This is expected!** The tests automatically skip when LiteLLM credentials aren't set.

**Solution:** Set the required environment variables:
```bash
export LITELLM_API_BASE="https://llm-uat.cotality.com"
export LITELLM_API_KEY="your-actual-api-key"
```

### Missing dependencies
**Error:** `error: Failed to spawn: pytest - No such file or directory`

**Solution:** Install dev dependencies:
```bash
uv sync --extra dev
```

### Template validation works without credentials
The tests are designed to skip gracefully when credentials aren't available. This allows:
- Safe CI/CD pipelines that don't have LiteLLM access
- Local development without requiring API keys
- Template validation without external dependencies

To actually run the agent card quality checks, you need valid LiteLLM credentials.
