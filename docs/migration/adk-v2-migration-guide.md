# ADK v2 Migration Guide

This guide helps teams migrate existing agents from the ADK v1 template line
(`0.x`) to the ADK v2 template line (`1.x`).

---

## Table of Contents

1. [Who This Guide Is For](#who-this-guide-is-for)
2. [Release Summary](#release-summary)
3. [Breaking Changes](#breaking-changes)
4. [Compatible Changes](#compatible-changes)
5. [Step-by-Step Migration](#step-by-step-migration)
6. [Environment Variable Validation](#environment-variable-validation)
7. [Install, Run, Test, and Deploy](#install-run-test-and-deploy)
8. [Pre-Flight Compatibility Checklist](#pre-flight-compatibility-checklist)
9. [Deprecation and Support Window](#deprecation-and-support-window)
10. [Getting Help](#getting-help)

---

## Who This Guide Is For

- Teams that **created an agent using the ADK v1 template** (`0.x`) and want to
  adopt the new ADK v2 template (`1.0.0`).
- Teams **starting a new agent** who want to understand the v2 baseline.
- Platform engineers validating adoption readiness.

---

## Release Summary

| Field | Value |
|---|---|
| Template version | `1.0.0` |
| Cotality Agent SDK | `>=0.3.18` |
| ADK dependency | `google-adk[extensions,mcp]>=2.0.0,<3.0.0` |
| Supported Python | `3.12`, `3.13` |
| Dropped Python | `3.11` |
| Internal package index | `idap_agents_glb-agf-pypi-release-virtual` |

---

## Breaking Changes

These changes **require action** before your agent will run on the v2 template.

### 1. ADK v2 Public API Changes

`google-adk` v2 restructures several public APIs. Key areas of impact:

| Area | ADK v1 pattern | ADK v2 pattern |
|---|---|---|
| Agent runner invocation | `Runner.run(...)` | `Runner.run_async(...)` (sync wrapper removed) |
| Tool registration | `FunctionTool(fn)` | `tool` decorator or `FunctionTool(fn)` (check import path) |
| Session management | `InMemorySessionService()` | `InMemorySessionService()` (API unchanged; storage backends changed) |
| LLM model binding | Direct string on `LlmAgent` | Via `create_litellm_with_retry` from `cotality_agent_sdk` |
| MCP tool helpers | `get_local_mcp_tool`, `get_sse_mcp_tool` | Same helpers; import path unchanged |

> **Action:** Review `src/cotality/agent/agent.py` in your existing agent for
> direct ADK v1 runner and tool-registration calls and update to v2 equivalents.
> See the [ADK v2 changelog](https://github.com/google/adk-python/blob/main/CHANGELOG.md)
> for the full API diff.

---

### 2. Python 3.11 Dropped

The template now requires **Python 3.12 or 3.13**.

> **Action:** Upgrade your local runtime and any container base images.
>
> Check your current version:
> ```bash
> python --version
> ```
>
> Update `.python-version` in the project root if you manage the version there:
> ```
> 3.12
> ```
>
> Update your container/Procfile base image tag to a 3.12+ image.

---

### 3. `python-dotenv` Import Path

The dependency is now `dotenv>=0.9.9`. If your agent code imports directly from
`python-dotenv`:

```python
# v1 — may fail
from dotenv import load_dotenv
```

This import still works if `python-dotenv` is transitively installed, but the
explicit dependency is now the `dotenv` package. Verify your import paths are
not pinning `python-dotenv` in your own `pyproject.toml`.

> **Action:** Remove any explicit `python-dotenv` pin from your `pyproject.toml`
> and replace with `dotenv>=0.9.9`.

---

### 4. `google-genai` Upper Bound

`google-genai` is now pinned to `<3`. If you previously had an open upper bound
or used `google-genai>=3.x` APIs, you must revert to the v2 API surface.

> **Action:** Check for `google-genai` pins in your `pyproject.toml` and
> align to `>=2.4.0,<3`.

---

## Compatible Changes

These changes are **backwards-compatible**. No action is required unless you
want to adopt the new features.

| Change | Detail |
|---|---|
| `structlog` added | Structured logging is now a first-class dep. Existing `logging` usage continues to work. |
| `auth0-api-python` and `auth0-python` added | Backs the updated OAuth2 middleware. Agents that do not enable auth are unaffected. |
| `httpx` added | Async HTTP client. Available if your agent needs it. |
| FastAPI server (`fastapi_server.py`) added | Optional alternative to `server.py`; offers OpenTelemetry instrumentation. |
| Agent card integration tests added | New tests under `tests/integration/agent_card/`. These validate description quality and agent portfolio coherence. |
| `nox` session additions | `lint`, `format_check`, `format_code`, `type_check`, `tests`, `integrations` sessions are now available. |
| `google-cloud-aiplatform` floor raised | Minimum is now `>=1.138.0`. |

---

## Step-by-Step Migration

Follow these steps in order.

### Step 1 — Upgrade Python

Ensure you are running Python 3.12 or 3.13:

```bash
python --version        # must be 3.12.x or 3.13.x
uv python pin 3.12      # pin project to 3.12 if not already set
```

---

### Step 2 — Update `pyproject.toml` Dependencies

Apply the following changes to your agent's `pyproject.toml`:

```toml
[project]
requires-python = ">=3.12,<3.14"   # was >=3.11

dependencies = [
    "google-adk[extensions,mcp]>=2.0.0,<3.0.0",   # was >=1.x
    "google-genai>=2.4.0,<3",              # add upper bound <3
    "pydantic>=2.12.5",
    "google-cloud-aiplatform>=1.138.0",
    "dotenv>=0.9.9",                        # replaces python-dotenv
    "a2a-sdk>=0.3.23",
    "cotality-agent-sdk>=2.0.0",
    "litellm>=1.83.7,<=1.83.14",
    "auth0-api-python>=1.0.0b3",
    "auth0-python>=5.1.0",
    "httpx>=0.28.1",
    "structlog>=25.5.0",
]
```

---

### Step 3 — Sync the Lock File

Authenticate with Artifactory and re-sync:

```bash
export UV_INDEX_JFROG_USERNAME=<YOUR_ARTIFACTORY_USERNAME>
export UV_INDEX_JFROG_PASSWORD=<YOUR_ARTIFACTORY_API_TOKEN>

uv sync --all-packages --extra dev
```

Verify ADK v2 is installed:

```bash
uv pip show google-adk
# Name: google-adk
# Version: 2.x.x
```

---

### Step 4 — Update Agent Code for ADK v2 APIs

Open `src/cotality/agent/agent.py` and check for patterns that changed in
ADK v2.

**Runner construction** — use the `App` wrapper (recommended since ADK v2.x):

```python
from google.adk.apps.app import App

# v1 (old)
runner = Runner(app_name=<name>, agent=root_agent, ...)
for event in runner.run(user_id=..., session_id=..., new_message=...):
    ...

# v2 (new — preferred)
runner = Runner(
    app=App(name=<name>, root_agent=root_agent),
    session_service=...,
    artifact_service=...,
    memory_service=...,
)
async for event in runner.run_async(user_id=..., session_id=..., new_message=...):
    ...
```

**Vertex AI extras** — if your agent deploys to Vertex AI Agent Engine or uses
GCP-specific services (BigQuery, Cloud Storage, Spanner, etc.), add the `[gcp]`
extra to your `google-adk` dependency:

```toml
# pyproject.toml
"google-adk[extensions,mcp,gcp]>=2.0.0,<3.0.0"
```

Or install it directly:

```bash
# correct — extra is on google-adk, not a standalone package
pip install "google-adk[gcp]"
```

> **Note:** `[gcp]` pulls in `google-cloud-aiplatform[agent-engines]` and
> several other GCP client libraries. Only add it when Vertex AI services are
> required; it is **not** needed for the default LiteLLM + local deployment path.

**LLM model binding** — use the Cotality SDK helper (already the template default):

```python
from cotality_agent_sdk import create_litellm_with_retry

model = create_litellm_with_retry(
    model="openai/gemini-2.5-pro-litellm-usw1",
    api_base=os.getenv("LITELLM_API_BASE"),
    api_key=os.getenv("LITELLM_API_KEY"),
)
```

---

### Step 5 — Validate Environment Variables

See the [Environment Variable Validation](#environment-variable-validation) section below.

---

### Step 6 — Run Quality Checks

All of the following must pass before deploying:

```bash
uv run --extra dev ruff format . --check
uv run --extra dev ruff check .
uv run --extra dev mypy src/ tests/ examples/
uv run nox -s tests
uv run nox -s integrations
```

---

### Step 7 — Deploy

Update your `Procfile` if you switched server implementations, then redeploy
via the Jenkins pipeline. No pipeline structural changes are required for the
v2 upgrade.

---

## Environment Variable Validation

The following environment variables are required. Missing or incorrect values
will surface as runtime failures.

### Required Variables (all environments)

| Variable | Description | Example |
|---|---|---|
| `LITELLM_API_BASE` | LiteLLM proxy base URL | `https://llm-uat.cotality.com` |
| `LITELLM_API_KEY` | LiteLLM API key from Vault | _(from Vault)_ |
| `ENV` | Runtime environment tag | `local`, `uat`, `prod` |

### Optional Auth Variables

Required only when `ENABLE_AGENT_AUTH0=True`.

| Variable | Description |
|---|---|
| `ENABLE_AGENT_AUTH0` | Enable OAuth2 middleware (`True`/`False`) |
| `A2A_CLIENT_AUTH0_CLIENT_ID` | Auth0 client ID |
| `A2A_CLIENT_AUTH0_CLIENT_SECRET` | Auth0 client secret |
| `A2A_CLIENT_AUTH0_TOKEN_URL` | Token endpoint URL |
| `AGENT_AUTH0_JWK_URL` | JWK public keys endpoint |
| `AGENT_AUTH0_ISSUER` | Token issuer URL |
| `AGENT_AUTH0_AUDIENCE` | Expected audience value |

### Optional Observability Variables

| Variable | Description |
|---|---|
| `PHOENIX_ENDPOINT` | Arize OpenTelemetry endpoint |
| `PHOENIX_API_KEY` | Arize API key |

### Pre-Flight Validation Script

Run this script locally before deploying to surface missing or misconfigured
variables before they cause runtime failures:

```bash
python - <<'EOF'
import os, sys

required = ["LITELLM_API_BASE", "LITELLM_API_KEY", "ENV"]
auth_required = (
    ["A2A_CLIENT_AUTH0_CLIENT_ID", "A2A_CLIENT_AUTH0_CLIENT_SECRET",
     "A2A_CLIENT_AUTH0_TOKEN_URL", "AGENT_AUTH0_JWK_URL",
     "AGENT_AUTH0_ISSUER", "AGENT_AUTH0_AUDIENCE"]
    if os.getenv("ENABLE_AGENT_AUTH0", "False").lower() == "true"
    else []
)

missing = [v for v in required + auth_required if not os.getenv(v)]
if missing:
    print(f"❌ Missing required environment variables: {missing}")
    sys.exit(1)
print("✅ All required environment variables are set.")
EOF
```

> **Tip:** Copy `.env.example` to `.env` and fill in your values before running
> this check.

---

## Install, Run, Test, and Deploy

### Install Dependencies

```bash
export UV_INDEX_JFROG_USERNAME=<YOUR_ARTIFACTORY_USERNAME>
export UV_INDEX_JFROG_PASSWORD=<YOUR_ARTIFACTORY_API_TOKEN>
uv sync --all-packages --extra dev
source .venv/bin/activate
```

### Run Locally (ADK Web UI)

```bash
cd src/cotality
uv run adk web
```

### Run Locally (Server mode)

```bash
cd src/cotality/agent
uv run python3 server.py
```

### Run Tests

```bash
# Unit tests only
uv run pytest tests/unit

# All sessions via nox
uv run nox -s tests
uv run nox -s integrations
```

### Lint and Type Check

```bash
uv run nox -s lint
uv run nox -s type_check
```

### Deploy

Deployments go through the existing Jenkins pipeline. No structural changes
are required for the ADK v2 upgrade.

1. Push your changes to the feature branch and open a pull request.
2. The pipeline will run lint, type check, unit tests, and integration tests.
3. Merge to `master` triggers the deployment pipeline.

Pipeline URL pattern:
```
https://jenkins-cicd.solutions.corelogic.com/<ORG>/job/<ECOSYSTEM>
```

---

## Pre-Flight Compatibility Checklist

Before deploying an ADK v2-based agent, verify each item:

- [ ] Python runtime is 3.12 or 3.13
- [ ] `google-adk>=2.0.0,<3.0.0` installed (`uv pip show google-adk`)
- [ ] `cotality-agent-sdk>=2.0.0` installed
- [ ] `a2a-sdk>=0.3.23` installed
- [ ] `pyproject.toml` `requires-python` is `>=3.12,<3.14`
- [ ] No direct `python-dotenv` pin in `pyproject.toml`
- [ ] `google-genai` is pinned to `<3`
- [ ] Runner calls updated to `Runner(app=App(name=..., root_agent=...), ...)` and `runner.run_async(...)`
- [ ] All required environment variables are set (run pre-flight script)
- [ ] `uv run nox -s tests` passes
- [ ] `uv run nox -s integrations` passes
- [ ] `uv run --extra dev ruff check .` passes
- [ ] `uv run --extra dev mypy src/ tests/ examples/` passes

---

## Deprecation and Support Window

| Template Line | Status | End-of-Life |
|---|---|---|
| `1.x` (ADK v2) | ✅ Active — current supported line | TBD |
| `0.x` (ADK v1) | ⚠️ Deprecated as of 2026-06-18 | **2026-09-18** (90 days) |

Teams running on the `0.x` ADK v1 template are encouraged to complete migration
before **2026-09-18**. After that date the `0.x` line will receive no further
bug fixes or security patches.

---

## Getting Help

| Channel | Purpose |
|---|---|
| [#ask-ai-platform](https://corelogic.enterprise.slack.com/archives/C092X9F6KF0) | Migration support, environment setup questions |
| [GitHub Issues](https://github.com/corelogic-private/idap_agents_glb-ag_foundation-python_adk_agent_template_base/issues) | Bug reports, feature requests |
| [TechDocs](https://driveway.corelogic.com/docs/default/Component/AgentDocs) | Full agentic platform documentation |

Platform contacts: hzarate@cotality.com · phtruong@cotality.com · pwegner@cotality.com
