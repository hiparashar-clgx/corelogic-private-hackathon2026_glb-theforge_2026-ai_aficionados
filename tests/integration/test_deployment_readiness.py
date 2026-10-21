"""Integration tests for deployment readiness.

Validates that the Procfile, Jenkinsfile, catalog-info.yaml, and .env.example
are present, correctly configured, and compatible with the Cotality deployment
workflow.  Any required manual environment configuration is caught here rather
than at deployment time.

Acceptance Criteria (ANE-3476): the generated project remains compatible with
the existing Cotality deployment workflow, and any required manual environment
configuration is documented rather than discovered during deployment.
"""

import re
from pathlib import Path
from typing import ClassVar

import pytest

_REPO_ROOT = Path(__file__).parent.parent.parent


class TestProcfile:
    """Verify the Procfile is present and correctly targets the server module."""

    @pytest.fixture(scope="class")
    def procfile_content(self) -> str:
        """Read Procfile contents once per class."""
        procfile = _REPO_ROOT / "Procfile"
        assert procfile.exists(), "Procfile is missing from the repository root."
        return procfile.read_text()

    def test_procfile_exists(self):
        """Procfile must be present in the repository root."""
        assert (_REPO_ROOT / "Procfile").exists(), (
            "Procfile is required for Cotality / Heroku-style deployment."
        )

    def test_procfile_defines_web_process(self, procfile_content):
        """Procfile must declare a 'web:' process type."""
        assert any(line.startswith("web:") for line in procfile_content.splitlines()), (
            "Procfile must define a 'web:' process for the HTTP server."
        )

    def test_procfile_web_command_references_python_or_app(self, procfile_content):
        """Procfile web entry must invoke Python or the 'app' project script."""
        web_line = next(
            (line for line in procfile_content.splitlines() if line.startswith("web:")), ""
        )
        assert "python" in web_line or "app" in web_line, (
            "Procfile web entry should reference 'python' or the 'app' entry-point script."
        )

    def test_procfile_referenced_server_module_exists(self, procfile_content):
        """Any Python file referenced in the Procfile web entry must exist."""
        web_line = next(
            (line for line in procfile_content.splitlines() if line.startswith("web:")), ""
        )
        match = re.search(r"python\s+([\w/]+\.py)", web_line)
        if match:
            module_path = _REPO_ROOT / match.group(1)
            assert module_path.exists(), (
                f"Procfile references '{match.group(1)}' but that file does not exist."
            )


class TestJenkinsfile:
    """Verify the Jenkinsfile is present and includes all required CI stages."""

    @pytest.fixture(scope="class")
    def jenkins_content(self) -> str:
        """Read Jenkinsfile contents once per class."""
        jenkinsfile = _REPO_ROOT / "Jenkinsfile"
        assert jenkinsfile.exists(), "Jenkinsfile is missing from the repository root."
        return jenkinsfile.read_text()

    def test_jenkinsfile_exists(self):
        """Jenkinsfile must be present in the repository root."""
        assert (_REPO_ROOT / "Jenkinsfile").exists(), (
            "Jenkinsfile is required for the Cotality CI/CD pipeline."
        )

    def test_jenkinsfile_has_unit_test_stage(self, jenkins_content):
        """Jenkinsfile must include a unit test stage."""
        assert "runUnitTests" in jenkins_content or "Unit Tests" in jenkins_content, (
            "Jenkinsfile must include a unit test stage."
        )

    def test_jenkinsfile_has_integration_test_stage(self, jenkins_content):
        """Jenkinsfile must include an integration test stage."""
        assert "runIntegrationTests" in jenkins_content or "Integration Tests" in jenkins_content, (
            "Jenkinsfile must include an integration test stage."
        )

    def test_jenkinsfile_has_lint_stage(self, jenkins_content):
        """Jenkinsfile must include a linting stage."""
        assert "ruff" in jenkins_content or "lint" in jenkins_content.lower(), (
            "Jenkinsfile must include a lint check."
        )

    def test_jenkinsfile_has_type_check_stage(self, jenkins_content):
        """Jenkinsfile must include a type-checking stage."""
        assert "mypy" in jenkins_content or "Type Check" in jenkins_content, (
            "Jenkinsfile must include a type check stage."
        )

    def test_jenkinsfile_uses_uv_builder(self, jenkins_content):
        """Jenkinsfile must use UvBuilder for uv-based dependency management."""
        assert "UvBuilder" in jenkins_content, (
            "Jenkinsfile must use UvBuilder for the uv package manager."
        )

    def test_jenkinsfile_nox_sessions_exist_in_noxfile(self, jenkins_content):
        """Nox sessions referenced in Jenkinsfile must be defined in noxfile.py."""
        nox_content = (_REPO_ROOT / "noxfile.py").read_text()
        nox_sessions_defined = re.findall(r"@nox\.session.*?\ndef (\w+)\(", nox_content, re.DOTALL)
        nox_calls_in_jenkins = re.findall(r"nox -s (\w+)", jenkins_content)

        for session in nox_calls_in_jenkins:
            assert session in nox_sessions_defined, (
                f"Jenkinsfile calls 'nox -s {session}' but no @nox.session named "
                f"'{session}' exists in noxfile.py."
            )


class TestCatalogInfo:
    """Verify catalog-info.yaml is present and has required fields for service discovery."""

    @pytest.fixture(scope="class")
    def catalog_content(self) -> str:
        """Read catalog-info.yaml contents once per class."""
        catalog = _REPO_ROOT / "catalog-info.yaml"
        assert catalog.exists(), "catalog-info.yaml is missing from the repository root."
        return catalog.read_text()

    def test_catalog_info_exists(self):
        """catalog-info.yaml must be present in the repository root."""
        assert (_REPO_ROOT / "catalog-info.yaml").exists(), (
            "catalog-info.yaml is required for Cotality service catalog registration."
        )

    def test_catalog_info_has_api_version(self, catalog_content):
        """catalog-info.yaml must declare an apiVersion."""
        assert "apiVersion:" in catalog_content, (
            "catalog-info.yaml must contain an 'apiVersion' field."
        )

    def test_catalog_info_has_kind(self, catalog_content):
        """catalog-info.yaml must declare a kind."""
        assert "kind:" in catalog_content, "catalog-info.yaml must contain a 'kind' field."

    def test_catalog_info_has_metadata(self, catalog_content):
        """catalog-info.yaml must have a metadata section."""
        assert "metadata:" in catalog_content, (
            "catalog-info.yaml must contain a 'metadata' section."
        )

    def test_catalog_info_has_spec(self, catalog_content):
        """catalog-info.yaml must have a spec section."""
        assert "spec:" in catalog_content, "catalog-info.yaml must contain a 'spec' section."

    def test_catalog_info_has_owner(self, catalog_content):
        """catalog-info.yaml must declare an owner for service accountability."""
        assert "owner:" in catalog_content, "catalog-info.yaml must declare an 'owner' field."

    def test_catalog_info_has_a2a_protocol_version(self, catalog_content):
        """catalog-info.yaml must declare the A2A protocolVersion."""
        assert "protocolVersion:" in catalog_content, (
            "catalog-info.yaml must contain 'protocolVersion' for A2A compatibility."
        )


class TestEnvExample:
    """Verify .env.example documents all environment variables required at runtime.

    Teams adopting the template need to know which variables to configure
    before deployment. Missing entries here mean undiscovered failures at
    deployment time — exactly what this acceptance criterion guards against.
    """

    REQUIRED_ENV_VARS: ClassVar[list[str]] = [
        "LITELLM_API_BASE",
        "LITELLM_API_KEY",
        "ENV",
        "ENABLE_AGENT_AUTH0",
    ]

    @pytest.fixture(scope="class")
    def env_example_content(self) -> str:
        """Read .env.example contents once per class."""
        env_file = _REPO_ROOT / ".env.example"
        assert env_file.exists(), (
            ".env.example must be present to document required environment variables."
        )
        return env_file.read_text()

    @pytest.mark.parametrize("env_var", REQUIRED_ENV_VARS)
    def test_required_var_documented_in_env_example(self, env_var, env_example_content):
        """Each required env var must be present in .env.example."""
        assert env_var in env_example_content, (
            f"Required env var '{env_var}' is not documented in .env.example. "
            "Add it so teams know which variables to configure before deployment."
        )
