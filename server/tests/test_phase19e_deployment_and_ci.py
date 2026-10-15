"""
CARspective — Phase 19E Deployment & CI/CD Foundation Tests
Validates production WSGI entrypoints, configuration fail-fast guards,
Dockerfile and .dockerignore security constraints, and CI workflow specifications.
All tests run with isolated configurations and NEVER touch the persistent database.
"""

import os
import re
import pytest
from pathlib import Path
from unittest.mock import patch
from server.config.settings import Settings, ConfigurationError


# ==============================================================================
# 1. PRODUCTION CONFIGURATION VALIDATION TESTS
# ==============================================================================

def test_production_config_rejects_debug_mode():
    """Validates that CARSPECTIVE_DEBUG=true is strictly prohibited in production mode."""
    with patch.dict(os.environ, {
        "CARSPECTIVE_ENV": "production",
        "CARSPECTIVE_DEBUG": "true",
        "SECRET_KEY": "a-very-secure-random-production-secret-key-12345",
        "ADMIN_API_KEY": "a-very-secure-random-production-admin-key-67890",
        "ALLOWED_HOSTS": "carspective.com",
        "CORS_ALLOWED_ORIGINS": "https://carspective.com",
        "DATABASE_URL": "sqlite:///:memory:",
    }, clear=True):
        prod_settings = Settings()
        assert prod_settings.IS_PRODUCTION is True
        assert prod_settings.DEBUG is True
        with pytest.raises(ConfigurationError, match="DEBUG mode .* must be disabled in production"):
            prod_settings.validate_production_config()


def test_production_config_rejects_empty_database_url():
    """Validates that DATABASE_URL must be specified and non-empty in production."""
    with patch.dict(os.environ, {
        "CARSPECTIVE_ENV": "production",
        "CARSPECTIVE_DEBUG": "false",
        "SECRET_KEY": "a-very-secure-random-production-secret-key-12345",
        "ADMIN_API_KEY": "a-very-secure-random-production-admin-key-67890",
        "ALLOWED_HOSTS": "carspective.com",
        "CORS_ALLOWED_ORIGINS": "https://carspective.com",
        "DATABASE_URL": "",
    }, clear=True):
        prod_settings = Settings()
        with pytest.raises(ConfigurationError, match="DATABASE_URL must be specified"):
            prod_settings.validate_production_config()


def test_production_config_accepts_valid_parameters():
    """Validates that valid production parameters pass validate_production_config without error."""
    with patch.dict(os.environ, {
        "CARSPECTIVE_ENV": "production",
        "CARSPECTIVE_DEBUG": "false",
        "SECRET_KEY": "a-very-secure-random-production-secret-key-12345",
        "ADMIN_API_KEY": "a-very-secure-random-production-admin-key-67890",
        "ALLOWED_HOSTS": "carspective.com,api.carspective.com",
        "CORS_ALLOWED_ORIGINS": "https://carspective.com",
        "DATABASE_URL": "sqlite:////app/data/database/carspective.db",
        "TRUSTED_PROXIES": "1",
    }, clear=True):
        prod_settings = Settings()
        # Should not raise ConfigurationError
        prod_settings.validate_production_config()
        assert prod_settings.IS_PRODUCTION is True
        assert prod_settings.DEBUG is False
        assert prod_settings.TRUSTED_PROXIES == 1


def test_production_config_rejects_wildcard_cors():
    """Validates that CORS wildcard '*' is prohibited in production."""
    with patch.dict(os.environ, {
        "CARSPECTIVE_ENV": "production",
        "CARSPECTIVE_DEBUG": "false",
        "SECRET_KEY": "a-very-secure-random-production-secret-key-12345",
        "ADMIN_API_KEY": "a-very-secure-random-production-admin-key-67890",
        "ALLOWED_HOSTS": "carspective.com",
        "CORS_ALLOWED_ORIGINS": "*",
        "DATABASE_URL": "sqlite:///:memory:",
    }, clear=True):
        prod_settings = Settings()
        with pytest.raises(ConfigurationError, match="Wildcard '\\*' is strictly forbidden"):
            prod_settings.validate_production_config()


# ==============================================================================
# 2. WSGI ENTRYPOINT TESTS
# ==============================================================================

def test_wsgi_module_exposes_flask_app():
    """Validates that server.wsgi imports cleanly and exposes a Flask callable."""
    import server.wsgi as wsgi_mod
    assert hasattr(wsgi_mod, "app")
    from flask import Flask
    assert isinstance(wsgi_mod.app, Flask)


def test_app_factory_fails_fast_in_production_with_insecure_settings():
    """Validates that create_app() raises ConfigurationError during startup if production settings are invalid."""
    from server.app import create_app
    from server.config import settings
    with patch.object(settings, "IS_PRODUCTION", True), \
         patch.object(settings, "SECRET_KEY", "PRODUCTION_SECRET_KEY_NOT_SET"), \
         patch.object(settings, "DEBUG", False):
        with pytest.raises(ConfigurationError, match="Production security violation"):
            create_app(validate_config=True)


# ==============================================================================
# 3. CONTAINERIZATION CONFIGURATION TESTS
# ==============================================================================

def test_dockerfile_structure_and_security_controls():
    """Validates Dockerfile best practices: multi-stage build, non-root user, libgomp1, and healthcheck."""
    dockerfile_path = Path("Dockerfile")
    assert dockerfile_path.exists(), "Dockerfile must exist!"
    content = dockerfile_path.read_text(encoding="utf-8")

    # Multi-stage check
    assert "AS frontend-builder" in content, "Dockerfile must use a dedicated frontend builder stage"
    assert "AS runtime" in content, "Dockerfile must define a dedicated runtime stage"

    # Base image pinning check
    assert re.search(r"FROM node:\d+(\.\d+)?-alpine", content), "Node image must be pinned"
    assert re.search(r"FROM python:\d+\.\d+(-slim)?", content), "Python image must be pinned"

    # Non-root user check
    assert "useradd" in content or "adduser" in content, "Must create a dedicated non-root user"
    assert "USER carspective" in content, "Must switch to non-root runtime user"

    # ML runtime dependency check (LightGBM requires libgomp1 on Linux)
    assert "libgomp1" in content, "LightGBM requires libgomp1 OpenMP runtime package"

    # Healthcheck check
    assert "HEALTHCHECK" in content, "Dockerfile must define a container HEALTHCHECK"
    assert "/health/liveness" in content, "HEALTHCHECK must target /health/liveness probe"

    # WSGI command check
    assert "gunicorn" in content, "Dockerfile CMD must invoke a production WSGI server"
    assert "server.wsgi:app" in content, "Dockerfile must point to server.wsgi:app"


def test_dockerignore_security_exclusions():
    """Validates that .dockerignore prevents sensitive files, local databases, and caches from entering build contexts."""
    dockerignore_path = Path(".dockerignore")
    assert dockerignore_path.exists(), ".dockerignore must exist!"
    content = dockerignore_path.read_text(encoding="utf-8")

    # Critical patterns that must be excluded
    required_exclusions = [
        ".env",
        "*.db",
        "*.snapshot*",
        "*.backup*",
        ".git",
        "__pycache__",
        ".venv",
        "client/node_modules",
        "scratch",
    ]

    for pattern in required_exclusions:
        assert any(pattern in line for line in content.splitlines()), f"Missing exclusion in .dockerignore: {pattern}"


# ==============================================================================
# 4. CI/CD WORKFLOW CONFIGURATION TESTS
# ==============================================================================

def test_github_actions_workflow_specification():
    """Validates GitHub Actions workflow configuration: jobs, triggers, YAML syntax, and invariant validations."""
    import yaml
    ci_path = Path(".github/workflows/ci.yml")
    assert ci_path.exists(), "GitHub Actions workflow .github/workflows/ci.yml must exist!"
    content = ci_path.read_text(encoding="utf-8")

    # Real YAML parser validation
    data = yaml.safe_load(content)
    assert data.get("name") == "CARspective CI/CD Pipeline"
    assert data.get("permissions", {}).get("contents") == "read", "Workflow must restrict permissions to read-only"

    # Verify triggers
    triggers = data.get("on") or data.get(True) or {}
    assert "push" in triggers
    assert "pull_request" in triggers

    # Verify jobs
    jobs = data.get("jobs", {})
    required_jobs = [
        "security-and-invariants",
        "backend-tests",
        "frontend-tests-and-build",
        "production-config-checks",
    ]
    for job in required_jobs:
        assert job in jobs, f"Missing required CI job: {job}"

    # Verify DAG dependencies
    assert jobs["backend-tests"].get("needs") == "security-and-invariants"
    assert set(jobs["production-config-checks"].get("needs")) == {"backend-tests", "frontend-tests-and-build"}

    # Verify third-party action pinning to 40-character commit SHAs
    for jid, jcfg in jobs.items():
        for step in jcfg.get("steps", []):
            if "uses" in step:
                action = step["uses"]
                assert "@" in action, f"Action must be pinned: {action}"
                sha_pin = action.split("@")[1].split()[0]
                assert len(sha_pin) == 40 and all(c in "0123456789abcdef" for c in sha_pin), \
                    f"Action {action} in job {jid} must be pinned to a 40-character commit SHA"

    # Verify model hash invariant check
    assert "4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1" in content, \
        "CI workflow must enforce valuation model SHA-256 invariant"

    # Verify inspection catalog invariant check
    assert "CANONICAL_CHECKLIST_CATALOG" in content
    assert "INSPECTION_CATALOG_VERSION" in content

    # Verify security audit step
    assert "pip-audit" in content, "CI workflow must include dependency vulnerability auditing"
