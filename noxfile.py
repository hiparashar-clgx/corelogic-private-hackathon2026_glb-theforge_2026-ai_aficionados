import nox


@nox.session(python=["3.12", "3.13"])
def lint(session: nox.Session):
    session.install("ruff")
    session.run("ruff", "check", ".", external=True)


@nox.session(python=["3.12", "3.13"])
def format_check(session: nox.Session):
    session.install("ruff")
    session.run("ruff", "format", ".", "--check", external=True)


@nox.session(python=["3.12", "3.13"])
def format_code(session: nox.Session):
    session.install("ruff")
    session.run("ruff", "format", ".", external=True)


@nox.session(python=["3.12", "3.13"])
def type_check(session: nox.Session):
    """Run static type checking with mypy."""
    session.run("uv", "run", "--extra", "dev", "mypy", "src/", "tests/", "examples/", external=True)


@nox.session(python="3.12")
def tests(session: nox.Session):
    """Run the unit tests."""
    session.run("uv", "run", "pytest", "tests/unit/", "-v", *session.posargs, external=True)


@nox.session(python="3.12")
def integrations(session: nox.Session):
    """Run the integration tests."""
    session.run("uv", "run", "pytest", "tests/integration/", "-v", *session.posargs, external=True)


@nox.session(python=["3.12", "3.13"])
def sonarqube_analysis(session):
    """Run SonarQube analysis."""
    # Install necessary dependencies
    session.install(".")
    session.install("pysonar")  # Or other necessary scanner dependencies

    # Configure SonarQube properties (adjust as needed)
    sonar_properties = {
        "sonar.projectKey": "{{SONAR_PROJECT_KEY}}",  # TODO Replace with your project key
        "sonar.organization": "cotality",  # TODO Replace with your organization
        "sonar.projectName": "{{APPLICATION_NAME}}",  # TODO Replace with your project name
        "sonar.sources": ".",  # Path to your source code
        "sonar.python.version": session.python,  # Specify your Python version
        # Add other relevant properties like sonar.coverage.reportPaths for coverage analysis
        "sonar.host.url": "https://sonar.solutions.corelogic.com/",
        "sonar.sonarCloudUrl": "https://sonar.solutions.corelogic.com/",
        "sonar.token": "project_token_here",  # TODO Replace with your project token
    }

    # Construct the SonarScanner command
    command = ["pysonar"]
    for key, value in sonar_properties.items():
        command.append(f"-D{key}={value}")

    # Run the SonarScanner command
    session.run(*command)
