# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Dependency Upgrades — ADK & A2A Platform Refresh (ANE-3777)

Updates the base template to the latest approved `google-adk` and `a2a-sdk`
releases, aligned with the versions required by `cotality-agent-sdk` and
`cotality-agent-eval-sdk`, and regenerates the lock file. `a2a-sdk` 1.x
restructures `a2a.types` from Pydantic models to protobuf-generated
messages, which required source changes in this template (see below).

#### Artifact Versions

| Artifact | Before | After |
|---|---|---|
| **google-adk[extensions,mcp]** | `>=2.0.0` (locked 2.3.0) | `>=2.6.3,<3` (locked 2.6.3) |
| **litellm** | `>=1.83.7,<=1.83.14` | `>=1.84` (locked 1.85.7) |
| **a2a-sdk** | `>=0.3.23,<0.4` (locked 0.3.26) | `>=1.1.2,<2.0.0` (locked 1.1.2) |
| **cotality-agent-sdk** | `>=2.0.0` (locked 2.0.3) | `>=2.1.5` (locked 2.1.5) |
| **cotality-agent-eval-sdk** (dev) | `>=2.0.6` | `>=2.1.7` (locked 2.1.8) |
| **google-genai** | `>=2.4.0,<3` (locked 2.11.0) | unchanged (still resolves to 2.11.0) |

The `a2a-sdk` and `cotality-agent-sdk` floors were chosen to match the
constraints declared by the latest `cotality-agent-eval-sdk` release
(2.1.7/2.1.8), which requires `a2a-sdk<2.0.0,>=1.1.2` and
`google-adk[eval]<2.7.0,>=2.6.2`. `cotality-agent-sdk` 2.1.5 was published
to add support for the restructured `a2a-sdk` 1.x API (it now uses
`a2a.helpers.proto_helpers.new_data_part`/`new_text_part` instead of the
removed `DataPart`/`TextPart` classes).

#### Breaking Changes & Source Code Updates

`a2a-sdk` 1.x replaces the Pydantic `a2a.types` models with protobuf
messages, changing several APIs this template depends on directly:

- **`AgentCard` no longer has a top-level `url` field.** The RPC endpoint
  is now expressed via `supported_interfaces: list[AgentInterface]`, each
  with its own `url` and `protocol_binding`. Updated
  `src/cotality/agent/agent.py`'s `MyAgent.get_agent_card()` to build
  `supported_interfaces=[AgentInterface(url=..., protocol_binding=TransportProtocol.JSONRPC)]`
  instead of passing `url=` directly. Note: the served
  `/.well-known/agent-card.json` HTTP response still includes a
  backward-compatible top-level `url` field (injected by the SDK's own
  `agent_card_to_dict()`/`to_compat_agent_card()` helpers), so clients
  reading the JSON payload are unaffected.
- **`a2a.server.apps.A2AStarletteApplication` was removed.** Rewrote
  `src/cotality/agent/server.py` and `src/cotality/agent/fastapi_server.py`
  to mount A2A routes directly via
  `a2a.server.routes.create_agent_card_routes()` and
  `create_jsonrpc_routes()` (FastAPI uses the
  `add_a2a_routes_to_fastapi()` convenience wrapper). `DefaultRequestHandler`
  now requires `agent_card` as a constructor argument (previously only the
  wrapping app needed it).
- **`TransportProtocol` moved from `a2a.types` to `a2a.utils.constants`**,
  and its enum values changed casing (`jsonrpc` → `JSONRPC`, `http_json` →
  `HTTP_JSON`). Updated the import and references in
  `src/cotality/agent/client.py`.
- **`ClientConfig.supported_transports` was renamed to
  `supported_protocol_bindings`.** Updated `client.py` accordingly.
- **`a2a.client.create_text_message_object` was removed.** Replaced with
  `a2a.helpers.proto_helpers.new_text_message(text, role=Role.ROLE_USER)`
  in `client.py`.
- **Client-side `AgentCard(**agent_card_data)` construction from a fetched
  JSON dict no longer works** (protobuf messages don't accept camelCase
  kwargs). Replaced with `a2a.client.card_resolver.parse_agent_card()`,
  the SDK's own helper for parsing a fetched agent card JSON payload,
  including legacy field compatibility handling.
- Removed vestigial dead code in `agent.py`'s `get_agent_card()` that
  constructed an unused `DefaultRequestHandler` (a leftover from an earlier
  iteration); it served no purpose and would have needed the new required
  `agent_card` kwarg.
- Updated `tests/unit/test_agent.py::TestMyAgentCard` to check
  `card.supported_interfaces[0].url` instead of the removed `card.url`,
  and simplified the `agent` fixture since the mocked
  `DefaultRequestHandler`/`CotalityAgentExecutor`/`InMemoryTaskStore`
  symbols no longer appear in `agent.py`.
- `google-adk[extensions]` 2.6.3 raises its own `litellm` floor to `>=1.84`,
  which required relaxing the previous `litellm<=1.83.14` ceiling in this
  template. The old ceiling was tied to ADK 2.2.0's requirements and is now
  stale.

#### Validation

- `uv lock` regenerated cleanly (273 packages resolved); `uv sync --locked
  --all-extras` confirms the lock is reproducible.
- `pytest tests/unit/ tests/integration/` — 120 passed, 3 skipped
  (pre-existing skips), 0 failed.
- `ruff check .` and `ruff format . --check` — clean.
- `mypy src/ tests/ examples/` — same single pre-existing, unrelated
  `import-untyped` warning for `cotality_agent_eval_sdk` (no `py.typed`
  marker upstream); no new type errors introduced.

#### Known Limitations / Follow-up

- `A2aAgentExecutor` (from `google-adk`) and `A2aAgentExecutorConfig` remain
  marked `[EXPERIMENTAL]` upstream by Google ADK; this is a pre-existing
  condition unrelated to this upgrade.
- `MCPToolset` continues to emit a pre-existing deprecation warning in favor
  of `McpToolset`; not addressed here as it's unrelated to this upgrade.

---

## [1.0.0] — 2026-06-18

### 🚨 BREAKING CHANGE — ADK v2 Upgrade

This release upgrades the base template and the Cotality Agent SDK to target
**Google ADK v2**. Because ADK v2 introduces backwards-incompatible API and
dependency changes, this is a **SemVer-major** release. Teams on the ADK v1
template line **must** follow the [ADK v2 Migration Guide](docs/migration/adk-v2-migration-guide.md)
before adopting this version.

---

### Artifact Versions

| Artifact | Version |
|---|---|
| **Template** | `1.0.0` |
| **cotality-agent-sdk** | `>=2.0.0` |
| **google-adk[extensions,mcp]** | `>=2.0.0` |
| **google-genai** | `>=2.4.0,<3` |
| **a2a-sdk** | `>=0.3.23` |
| **litellm** | `>=1.83.7,<=1.83.14` |
| **Python** | `>=3.12, <3.14` (3.12 or 3.13) |

---

### What Changed

#### Breaking Changes (require migration action)

- **ADK v2 dependency** — `google-adk` minimum version raised to `>=2.0.0`.
  ADK v2 restructures several public APIs (agent runner, tool registration,
  session management). Code written against ADK v1 will not run without
  changes. See the [migration guide](docs/migration/adk-v2-migration-guide.md)
  for a full diff of affected APIs.
- **Python 3.11 dropped** — minimum supported version is now Python 3.12.
  Consumers still on 3.11 must upgrade their runtime before adopting this
  template version.
- **`dotenv` package replaced** — dependency is now `dotenv>=0.9.9` (thin
  wrapper). Any direct use of the old `python-dotenv` import path must be
  updated to `dotenv`.
- **`google-genai` upper-bound tightened** — pinned to `<3` to prevent
  accidental adoption of breaking google-genai v3 APIs.

#### Compatible Changes (no action required)

- `structlog>=25.5.0` added as a first-class dependency for structured logging.
- `auth0-api-python>=1.0.0b3` and `auth0-python>=5.1.0` added to support the
  updated OAuth2 middleware in `server.py`.
- `httpx>=0.28.1` added for async HTTP client support.
- `google-cloud-aiplatform>=1.138.0` version floor raised.
- FastAPI alternative server (`fastapi_server.py`) added with OpenTelemetry
  instrumentation support.
- Agent card integration tests added under `tests/integration/agent_card/`.
- `nox` sessions added: `lint`, `format_check`, `format_code`, `type_check`,
  `tests`, `integrations`.

---

### Required Consumer Actions

1. **Upgrade Python runtime** to 3.12 or 3.13 if currently on 3.11.
2. **Update `pyproject.toml`** ADK dependency to `google-adk[extensions,mcp]>=2.0.0`.
3. **Run the dependency migration script / uv sync** — see the
   [migration guide](docs/migration/adk-v2-migration-guide.md#step-by-step-migration).
4. **Validate environment variables** — new required vars added; run the
   pre-flight validation steps in the
   [migration guide](docs/migration/adk-v2-migration-guide.md#environment-variable-validation).
5. **Review breaking API changes** in your agent code — especially tool
   registration and runner invocation patterns.

---

### Deprecation & Support Window

| Line | Status | EOL |
|---|---|---|
| ADK v2 template (`1.x`) | ✅ Active / Supported | TBD |
| ADK v1 template (`0.x`) | ⚠️ Deprecated | 90 days from this release (2026-09-18) |

Teams are encouraged to migrate within the 90-day window. The platform team
will provide migration support via
[#ask-ai-platform](https://corelogic.enterprise.slack.com/archives/C092X9F6KF0).

---

### Adoption Readiness

To verify your project is using the correct artifacts, run:

```bash
uv pip show google-adk cotality-agent-sdk a2a-sdk
```

Expected output (minimums):

```
Name: google-adk
Version: 2.x.x

Name: cotality-agent-sdk
Version: 0.3.18 or higher

Name: a2a-sdk
Version: 0.3.23 or higher
```

---

## [0.1.0] — Initial Release

- Initial ADK v1-based agent template.
- Basic LiteLLM integration, MCP tool helpers, A2A support, OAuth2 middleware.
