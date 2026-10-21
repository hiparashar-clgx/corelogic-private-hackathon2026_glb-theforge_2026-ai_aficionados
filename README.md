# ADK Agent Template

This Python Agent ADK template can be used as a base for creating your own agents through Google's ADK (Agent Development Kit). The template provides some simple functionality to interact with sub-agents and connect to local & remote MCP servers.

The template uses [LiteLLM](https://www.litellm.ai/) as the default LLM provider. Note that using LiteLLM disables certain ADK features such code execution.


## 🚀 Release & Migration

| | |
|---|---|
| **Current template version** | `1.0.0` |
| **ADK version** | `google-adk[extensions,mcp]>=2.0.0` |
| **Cotality Agent SDK** | `cotality-agent-sdk>=2.0.0` |
| **Supported Python** | 3.12, 3.13 |

> **Upgrading from ADK v1?** See the [ADK v2 Migration Guide](docs/migration/adk-v2-migration-guide.md)
> for a full breakdown of breaking changes, migration steps, and the deprecation timeline.
>
> **Release notes and version history:** [CHANGELOG.md](CHANGELOG.md)


## Agentic Documentation

[TechDocs](https://driveway.corelogic.com/docs/default/Component/AgentDocs)


## URL

You can find the deployed agent card at:
```
${{GLOBAL:ORG_HYPHEN}}-${{GLOBAL:APPLICATION_NAME_HYPHEN}}.cntvusw1uat.solutions.corelogic.com/.well-known/agent-card.json
```

Or if you are deploying the Demo UI - More details on the Deploying the Demo UI [here](#deploying-the-demo-ui-using-adk-web-not-for-production):
```
${{GLOBAL:ORG_HYPHEN}}-${{GLOBAL:APPLICATION_NAME_HYPHEN}}.cntvusw1uat.solutions.corelogic.com/dev-ui/
```

For a more in-depth look at the agent, and to debug its logic, use the A2A Inspector. Quickstart guide [here](https://driveway.corelogic.com/docs/default/Component/AgentDocs/guides/use-a2a-inspector/#)

## CICD Pipeline

You can find the CICD pipeline for this project here, then navigating to the name of your new application:

[https://jenkins-cicd.solutions.corelogic.com/${{GLOBAL:ORG_HYPHEN}}/job/${{GLOBAL:ECOSYSTEM}}](https://jenkins-cicd.solutions.corelogic.com/${{GLOBAL:ORG_HYPHEN}}/job/${{GLOBAL:ECOSYSTEM}})


## IMPORTANT: The Vault Path of your LiteLLM API Key May Need Updating

Your LiteLLM API key is stored in Vault so please ensure the path to the key is matching what is defined in the `vaules.yaml` file for this new application.

```yaml
configurations:
  Secret:
    litellm_api_key: "{VAULTB64:UPDATE_LITELLM_API_KEY_VAULT_PATH_HERE:VALUE}"
```

Your values.yaml can be found in your `-configs` repo under `/pipeline/${{GLOBAL:APPLICATION_NAME_HYPHEN}}` which can usually be found here:

`https://github.com/corelogic-private/${{GLOBAL:ORG_HYPHEN}}-${{GLOBAL:ECOSYSTEM}}-configs/tree/master/pipeline/${{GLOBAL:APPLICATION_NAME_HYPHEN}}/uat-usw1/values.yaml`

Edit your environment specific `values.yaml` files to point to your LiteLLM API key vault path.

If the LiteLLM key was provisioned via the GenAi Sandbox then the path is most likely:

`app/litellm/uat/{USE_CASE_NAME}:value`

After updating the vault path, redeploy the agent for the changes to take effect. This can be done by manually triggering a build on the Jenkins pipeline for this application. View the [CICD Pipeline](#CICD-Pipeline) section for more details.

## Project Structure

The repository is organized as follows:

- `src/`
  Main source code for the agent and supporting modules.
  - `cotality/agent/agent.py`
    The code for the agent deployed from this repo is located here. Also the agent's tools
    are defined here in the _get_tool_list method.
  - `cotality/agent/server.py`
    A FastAPI server to run the agent as a web service.
  - `cotality/agent/fastapi_server.py`
    An alternative FastAPI server implementation with additional features like OpenTelemetry instrumentation.
  - `cotality/agent/client.py`
    An example client to programmatically interact with the agent server.
  - `cotality/agent/utils/mcp_tools/`
    Helper functions to create MCP tools for local and remote MCP servers.
  - `cotality/agent/utils/oauth2_middleware/`
    Helper function for OAuth2 authentication.
- `examples/`
  Example agents and usage patterns.
  - `agent_with_mcp_template/`
    Example agent implementation with its own source and utilities.
- `tests/`
  Evaluation sets for validating agent functionality.
  - `integration/agent_card/`
    Agent card validation tests for description quality and portfolio coherence.
    See `tests/integration/agent_card/README.md` for details.
- `pyproject.toml`
  Project dependencies and configuration.
- `noxfile.py`, `ruff.toml`
  Test configuration and linting configuration.
- `Procfile`, `Jenkinsfile`
  Deployment and CI/CD configuration.
- `catalog-info.yaml`
  Metadata for Driveway service catalog integration.


## Prerequisites

### Python and UV

Make sure that your [Python](https://www.python.org/downloads/) and [UV](https://github.com/astral-sh/uv) version meet the following requirements

- Python 3.12+ (<3.14)
- UV

Check your versions with the following commands:

```
$ python -V
$ uv --version
```

On MacOS, you can install UV with Homebrew:

```
brew install uv
```

Or using the official installer:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

*Currently installing on Windows WSL is not supported.*

## 🧑‍💻 Development Setup

### 1. Install Dependencies

From the project root, run:

```bash
uv sync --all-packages --extra dev
```

### 2. Set Up Pre-commit Hooks

Install pre-commit hooks to ensure code quality checks run automatically on every commit:

```bash
uv run pre-commit install
```

### Recommended IDE
We recommend using using [PyCharm](https://www.jetbrains.com/pycharm/download/) as your IDE. It has built in support for virtual environments and UV.

You can also use [VSCode](https://code.visualstudio.com/)

Get support on [#ask-ai-platform](https://corelogic.enterprise.slack.com/archives/C092X9F6KF0) for environment setup help.

### Artifactory API Key

To locally install the dependencies for the Cotality Agent Template follow the steps below:

1. Visit and log into https://artifactory.solutions.corelogic.com/ using your Cotality credentials
2. Click on the upper right icon and click on **Set Me Up**
3. Click on **pypi**
4. Paste in the following to the Repository field: `idap_agents_glb-agf-pypi-release-virtual`
5. Enter your password and generate a token.
6. Use this token to setup your UV config using the commands in the [Getting Started (Local)](#getting-started-local) section below.


## Getting Started (Local)
You will need a LiteLLM Key. Get support on [#ask-ai-platform](https://corelogic.enterprise.slack.com/archives/C092X9F6KF0)

Create an `.env` file at the root of the project (or rename the `.env.example` file) and enter the following details:

```
LITELLM_API_BASE=https://llm-uat.cotality.com
LITELLM_API_KEY=<your_litellm_api_key>
ENV=local
```

Install dependencies and set up virtual environment:
```bash
export UV_INDEX_JFROG_USERNAME=<YOUR_ARTIFACTORY_USERNAME>
export UV_INDEX_JFROG_PASSWORD=<YOUR_ARTIFACTORY_API_TOKEN>
uv sync --all-packages --extra dev
source .venv/bin/activate
```


## Run the Agent
Navigate to directory containing agent:
```bash
cd src/cotality
```
Open UI to chat with the agent: (or ```uv run adk run agent``` for a CLI instead)
```bash
uv run adk web
```
This will open up a local web server that should look similar to other AI chatbots. The UI will indicate which tool the agent uses to respond to the prompt, and you can click on each event to view more details about the communication between agents/tools.


Alternatively, you can run the agent as a server to access the agent card and health endpoints:
```
cd src/cotality/agent
uv run python3 server.py
```

To interact with a running agent server use `src/cotality/agent/client.py`

## Alternative Server Implementation (FastAPI)

For advanced use cases requiring OpenTelemetry instrumentation or other FastAPI-specific features, an alternative server implementation is available in `src/cotality/agent/fastapi_server.py`.

To run this server locally:
```bash
cd src/cotality/agent
uv run python3 fastapi_server.py
```

To deploy this version, update your `Procfile` to point to the FastAPI app:
```
web: uvicorn src.cotality.agent.fastapi_server:app --host 0.0.0.0 --port 8000
```


## OpenTelemetry Tracing

The agent supports OpenTelemetry tracing for observability. To enable Arize, set:

```env
PHOENIX_ENDPOINT=https://your-arize-otel-endpoint
PHOENIX_API_KEY=your-arize-api-key
```


## Connect to MCP Servers
- Add one or more MCP tools to the **agent's tool list** using the helpers in ```agent/utils/mcp_tools```
- For local MCP servers with *stdio* transport,
  - Use the  ```get_local_mcp_tool``` function and pass in the absolute path to the MCP server
- For remote MCP servers,
  - Use the ```get_sse_mcp_tool``` function and pass in the URL of the MCP server
- For *streamable* remote MCP servers,
  - Use the ```get_http_mcp_tool``` function and pass in the URL of the MCP server
- MCP transport docs: https://modelcontextprotocol.io/docs/concepts/transports#python-server

Example Usage:
```
tools=[
  get_local_mcp_tool("/Users/name/project/src/my_mcp_server/server.py"),
  get_sse_mcp_tool("http://server-address:port/sse"),
  get_http_mcp_tool("http://server-address:port/mcp")
]
```

- For editing the agent's tools find the `_get_tool_list` method in `src/cotality/agent/agent.py`

## Connect to Agents (A2A)

```python
      LlmAgent(
        ...
        tools=[agent_tool.AgentTool(agent=RemoteA2aAgent(
          name="AgentExpert",
          description="Real Estate Expert",
          agent_card=(
              "<AGENT_URL>/.well-known/agent-card.json"
          )))],
        ...
      )
```

- View a commented out example in the `_get_tool_list` method in `src/cotality/agent/agent.py`
- The Root Agent will use the Remote Agent if given a prompt that it believes the Remote Agent can answer. For example, if the Root Agent is given the prompt:
  - `Explain concessions in a real estate deal`
  - Then the Root Agent will reach out to the Real Estate Expert Agent


## LLM Retry Configuration

The template uses `create_litellm_with_retry` from the Cotality Agent SDK to provide automatic retry handling for LLM API calls. This includes exponential backoff for rate limit errors (429) and server errors (5xx).

### Simple Configuration

Customize individual retry parameters directly in the function call:

```python
from cotality_agent_sdk import create_litellm_with_retry

model = create_litellm_with_retry(
    model="openai/gemini-2.5-pro-litellm-usw1",
    api_base=os.getenv("LITELLM_API_BASE"),
    api_key=os.getenv("LITELLM_API_KEY"),
    # Customize retry behavior:
    num_retries=5,  # Number of retry attempts (default: 3)
    timeout=120,  # Request timeout in seconds (default: 60)
    fallbacks=["openai/gemini-2.5-fast-litellm-usw1"],  # Fallback models if primary fails
)
```

### Using Preset Configurations

For common use cases, the SDK provides preset configurations:

```python
from cotality_agent_sdk import (
    create_litellm_with_retry,
    get_default_retry_config,
    get_high_resilience_retry_config,
)

# Default config (3 retries, 1s delay, 60s timeout)
model = create_litellm_with_retry(
    model="openai/gpt-4",
    retry_config=get_default_retry_config(),
)

# High resilience config (5 retries, 2s delay, 120s timeout)
model = create_litellm_with_retry(
    model="openai/gpt-4",
    retry_config=get_high_resilience_retry_config(),
)
```

### Custom Configuration Object

For full control, create a custom `LiteLLMRetryConfig`:

```python
from cotality_agent_sdk import create_litellm_with_retry, LiteLLMRetryConfig

config = LiteLLMRetryConfig(
    num_retries=10,
    timeout=180,
    fallbacks=["openai/gpt-3.5-turbo"],
    context_window_fallback_dict={"gpt-4": "gpt-4-32k"},
)

model = create_litellm_with_retry(
    model="openai/gpt-4",
    retry_config=config,
)
```

### Mixing Config and Individual Parameters

Individual parameters override values from `retry_config`:

```python
# Start with high resilience config but override timeout
model = create_litellm_with_retry(
    model="openai/gpt-4",
    retry_config=get_high_resilience_retry_config(),
    timeout=300,  # Override the config's 120s timeout
)
```


## Authentication
Included in the template base is a server, oauth_middleware, and example client in src/cotality/agent. To enable the
OAuth middleware on the server the following code is already included:
```
app.add_middleware(OAuth2Middleware)
```

This middleware looks for parameters in your .env file in the root folder. Here is an example of the needed values for a UAT app:
```
ENABLE_AGENT_AUTH0=True
A2A_CLIENT_AUTH0_CLIENT_ID=<YOUR_CLIENT_ID_HERE>
A2A_CLIENT_AUTH0_CLIENT_SECRET=<YOUR_CLIENT_SECRET_HERE>
A2A_CLIENT_AUTH0_TOKEN_URL=https://api-uat.cotality.com/jwt-auth/token?grant_type=client_credentials
AGENT_AUTH0_JWK_URL=https://api-uat.cotality.com/edgemicro-auth/jwkPublicKeys
AGENT_AUTH0_ISSUER=https://api-uat.cotality.com/jwt-auth/token
AGENT_AUTH0_AUDIENCE=microgateway
```

To test the auth flow, after configuring the project, and creating and populating the .env file, you can run
the server.py and then the client.py in two separate terminals:
```
cd src/cotality/agent
uv run python3 server.py
```
```
cd src/cotality/agent
uv run python3 client.py
```

If the agent answers the query (by default how many planets in our solar system are there), the flow is working as intended.

### Customizing the Middleware
The Authentication is enabled with the ENABLE_AGENT_AUTH0 environment variable.
The default public (non-authenticated) paths are the health and agent card endpoints, it is suggested that these remain public:
```
public_paths = ["/health", "/.well-known/agent-card.json"]
```

## Configure Project Metadata
- Edit pyproject.toml
  - Update  the ```description``` and ```version``` elements under the ```[project]``` table.
  - Add authors under ```[tool.hatch.metadata]``` in the authors block, for example:
      ```toml
        [tool.hatch.metadata]
        authors = [
            { name = "User", email = "user@corelogic.com" },
        ]
      ```
  - Update ```[tool.hatch.build.targets.wheel]``` with the root source package
    ```toml
      [tool.hatch.build.targets.wheel]
      packages = ["src/<your_project_root>", "src/<other project root>"]
    ```

## Adding Secrets or Environment Specific Variables
This python based application does not use Spring Cloud Config Server. Instead, environment variables or secrets can be added to the `.env` file at the root of the project.
These variables can then be accessed in the code using `os.getenv("MY_VAR")`

For example to add a variable locally named `MY_VAR`:
1. Add to `.env` file:
2. ```
   MY_VAR=my_value
   ```


If you want a default value, you can use:
```python
my_var = os.getenv("MY_VAR", "default_value")
```

To give your deployed application access to these variables, you will need to add them to your pipeline config repo in the values.yml file for the specific environment. For example:
```yaml
...
env:
  - name: MY_VAR
    value: value_for_env
```


## Pre-Commit and Quality Checks
Install the pre-commit hooks:
```bash
uv run pre-commit install
```

## Testing, Formatting, Linting, and Static Type Checking

This project uses `nox` for task automation and `ruff` for linting and formatting. `mypy` is used for static type checking. 

All of the following commands must pass for the Agent to pass CI. 

```
uv sync --all-packages --extra dev
uv run --extra dev ruff format . --check
uv run --extra dev ruff check .
uv run --extra dev mypy src/ tests/ examples/
uv run nox -s tests
uv run nox -s integrations
```



### Using Nox

You can run `nox` through `uv` without installing it globally:

```bash
uv run nox -s tests
```

Available sessions:
- `nox -s lint`: Run linter (ruff)
- `nox -s format_check`: Check code formatting
- `nox -s format_code`: Format code
- `nox -s type_check`: Run static type checking (mypy)
- `nox -s tests`: Run unit tests
- `nox -s integrations`: Run integration tests

### Running Tests Directly

You can also run `pytest` directly using `uv`:

```bash
uv run pytest tests/unit
```

### Linting & Formatting with Ruff

Configuration is in `ruff.toml`.

To run ruff directly:
```bash
uv run ruff check .
uv run ruff format .
```

### Agent Card Validation Tests
Validate your agent description quality and portfolio coherence:

```bash
# Set your agent URL
export AGENT_URL=http://localhost:8000

# Run description quality validation
GENERATE_DESCRIPTION_REPORT=true uv run pytest tests/integration/agent_card/test_agent_description_quality.py -v

# For multi-agent portfolios, also validate coherence
export ADDITIONAL_AGENT_URLS=http://agent2:8000,http://agent3:8000
GENERATE_PORTFOLIO_REPORT=true uv run pytest tests/integration/agent_card/test_coherence_validation.py -v
```

See `tests/integration/agent_card/README.md` for detailed documentation.

### Agent Evaluation

This template is pre-wired to use the internal **`cotality-agent-eval-sdk`** for
agent evaluation instead of the native ADK `AgentEvaluator`. This gives you
standardized Cotality evaluation reporting out-of-the-box, plus optional
automatic publishing of results to GCS.

- Test entrypoint: `tests/integration/test_adk_evaluation.py`. It uses the SDK's
  `@evaluation_test` decorator and is automatically parametrized over every
  `*.evalset.json` file in `tests/integration/`.
- Evaluation criteria/thresholds come from `tests/integration/test_config.json`
  (ADK-native `EvalConfig` convention, auto-discovered by the SDK).
- Harness configuration lives in `configs/evaluation/`:
  - `evaluation_config.<ENV>.yaml` is used when the `ENV` env var is set (e.g.
    `evaluation_config.local.yaml` for `ENV=local`).
  - `evaluation_config.yaml` is the fallback used when `ENV` is unset.

Run the evaluation suite with:

```bash
uv run pytest tests/integration/test_adk_evaluation.py -v
```

Running evaluations locally requires `LITELLM_API_BASE`/`LITELLM_API_KEY` to be
set (see [Adding Secrets or Environment Specific Variables](#adding-secrets-or-environment-specific-variables)).

#### Enabling GCS Result Publishing

By default, evaluation results are written locally to `results_dir`
(`tests/integration/results`) and GCS publishing is disabled. To publish
results to GCS, uncomment and fill in the GCS section in your
`configs/evaluation/evaluation_config.<ENV>.yaml`:

```yaml
gcs_results_dir: gs://your-bucket/path
app_name: your-agent-name
org: your-org
space: your-space
```

`app_name`, `org`, and `space` are required whenever GCS publishing is
configured, and must not contain `/` or `\`.


# Deploying the Demo UI using adk-web (Not for Production)
Please read all the following notes below before deploying the Demo UI.
- By default, the agent server is deployed which does not have a UI.
- To deploy the Demo UI, change the `web` command in the `Procfile` to:
```
web: cd src/cotality/ && adk web --host 0.0.0.0 --port 8000
```
- The health endpoint will change to be `/dev-ui/assets/config/runtime-config.json` instead of `/health`
- You will need to update the health check in your `values.yaml` located in your cicd config repo to use the new health endpoint.
- You can find the repo that contains the `values.yaml` file in your config repo usually its called `{org}-{space}-configs`
- The `values.yaml` file to change would be in `/pipeline/{appname}/{environment}/values.yaml`
```yaml
probes:
  readinessProbe:
    httpGet:
      path: /dev-ui/assets/config/runtime-config.json
      port: 8000
    initialDelaySeconds: 60
  livenessProbe:
    httpGet:
      path: /dev-ui/assets/config/runtime-config.json
      port: 8000
    initialDelaySeconds: 60
  startupProbe:
    httpGet:
      path: /dev-ui/assets/config/runtime-config.json
      port: 8000
    initialDelaySeconds: 60
```

- After the probes and the Procfile are updated, the agent must be redeployed.
- Note this is only recommended for demo purposes, do not deploy the demo ui to production environments.
- *All sessions are publicly visible and can be accessed by anyone with the URL.*
- The Demo UI is not secure and does not have authentication.
- The sessions are stored in memory and will be lost if the server is restarted.
- Learn more about adk-web at the official repo https://github.com/google/adk-web


# Support

[#ask-ai-platform](https://corelogic.enterprise.slack.com/archives/C092X9F6KF0)

hzarate@cotality.com

phtruong@cotality.com

pwegner@cotality.com


# Feature Requests

[Github Issues](https://github.com/corelogic-private/idap_agents_glb-ag_foundation-python_adk_agent_template_base/issues)


# Contributing

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)

[Raise Pull Requests](https://github.com/corelogic-private/idap_agents_glb-ag_foundation-python_adk_agent_template_base/pulls)
