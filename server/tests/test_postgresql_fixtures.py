"""
CARspective — PostgreSQL & Dialect-Aware Test Fixture Unit Tests
Phase 21C Stage 3C: Local validation of fixture parameterization, dialect configuration,
and live database protection invariants.
"""

import os
from unittest.mock import patch
import pytest
import sqlalchemy as sa
from server.tests.conftest import is_live_database_url, test_engine


class TestPostgresFixtureSelectionAndSafety:
    """Verifies that test_engine respects TEST_DATABASE_URL and protects the live database."""

    def test_live_database_detection_identifies_production_database(self):
        """Verifies that live database paths are detected accurately."""
        assert is_live_database_url("sqlite:///data/database/carspective.db") is True
        assert is_live_database_url("sqlite:///C:/Projects/smart-used-car-price-prediction/data/database/carspective.db") is True
        assert is_live_database_url("sqlite:///C:\\Projects\\smart-used-car-price-prediction\\data\\database\\carspective.db") is True
        assert is_live_database_url("sqlite:////app/data/database/carspective.db") is True
        assert is_live_database_url("carspective.db") is True

    def test_live_database_detection_allows_in_memory_and_ephemeral_urls(self):
        """Verifies that in-memory SQLite and PostgreSQL URLs are not falsely flagged as live."""
        assert is_live_database_url("sqlite:///:memory:") is False
        assert is_live_database_url("sqlite:///tmp/test_ephemeral.db") is False
        assert is_live_database_url("postgresql+psycopg2://user:pass@localhost:5432/carspective_test_db") is False
        assert is_live_database_url("") is False
        assert is_live_database_url(None) is False

    def test_fixture_rejects_unsafe_live_database_configuration(self):
        """Setting TEST_DATABASE_URL to the live database must raise ValueError immediately."""
        with patch.dict(os.environ, {"TEST_DATABASE_URL": "sqlite:///data/database/carspective.db"}):
            with pytest.raises(ValueError, match="Unsafe test configuration.*targets the live database"):
                # Call generator function
                gen = test_engine.__wrapped__()
                next(gen)

    def test_fixture_defaults_to_in_memory_sqlite_when_unset(self):
        """When TEST_DATABASE_URL is unset, test_engine defaults to in-memory SQLite with foreign keys."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure TEST_DATABASE_URL is not set
            os.environ.pop("TEST_DATABASE_URL", None)
            gen = test_engine.__wrapped__()
            engine = next(gen)
            try:
                assert engine.url.drivername == "sqlite"
                assert engine.url.database == ":memory:"
                # Verify foreign keys are enabled via PRAGMA listener
                with engine.connect() as conn:
                    fk = conn.execute(sa.text("PRAGMA foreign_keys")).scalar()
                    assert fk == 1
            finally:
                try:
                    next(gen)
                except StopIteration:
                    pass

    def test_fixture_configures_postgresql_engine_without_sqlite_pragmas(self):
        """
        When TEST_DATABASE_URL is set to PostgreSQL, engine uses psycopg2 and does NOT attach SQLite PRAGMAs.
        """
        pg_test_url = "postgresql://test_user:test_secret@localhost:5432/ephemeral_test_db"
        with patch.dict(os.environ, {"TEST_DATABASE_URL": pg_test_url}):
            with patch("server.tests.conftest.create_engine") as mock_create_engine, \
                 patch("server.models.base.Base.metadata.create_all"):
                
                mock_engine = sa.create_engine("sqlite:///:memory:")
                mock_create_engine.return_value = mock_engine

                gen = test_engine.__wrapped__()
                engine = next(gen)

                # Verify create_engine was called with normalized URL and pool_pre_ping=True
                mock_create_engine.assert_called_once()
                args, kwargs = mock_create_engine.call_args
                assert args[0] == "postgresql+psycopg2://test_user:test_secret@localhost:5432/ephemeral_test_db"
                assert kwargs.get("pool_pre_ping") is True
                assert "connect_args" not in kwargs  # check_same_thread must NOT be passed to PostgreSQL

                try:
                    next(gen)
                except StopIteration:
                    pass


class TestPostgresCIWorkflowSpecification:
    """Verifies the postgres-integration-tests CI job configuration in .github/workflows/ci.yml."""

    @pytest.fixture(autouse=True)
    def load_ci_workflow(self):
        import yaml
        from pathlib import Path
        ci_path = Path(".github/workflows/ci.yml")
        assert ci_path.exists(), "ci.yml must exist"
        self.ci_data = yaml.safe_load(ci_path.read_text(encoding="utf-8"))
        self.jobs = self.ci_data.get("jobs", {})

    def test_postgres_job_exists_and_depends_on_security(self):
        """postgres-integration-tests must exist and depend on security-and-invariants."""
        assert "postgres-integration-tests" in self.jobs
        job = self.jobs["postgres-integration-tests"]
        assert job.get("runs-on") == "ubuntu-latest"
        assert job.get("needs") == "security-and-invariants"
        assert job.get("timeout-minutes") == 15

    def test_postgres_job_service_container_configuration(self):
        """Service container must run postgres:16-alpine with healthchecks and test-only credentials."""
        job = self.jobs["postgres-integration-tests"]
        services = job.get("services", {})
        assert "postgres" in services
        pg = services["postgres"]
        assert pg.get("image") == "postgres:16-alpine"
        assert "5432:5432" in pg.get("ports", [])
        
        env = pg.get("env", {})
        assert env.get("POSTGRES_USER") == "carspective_test"
        assert env.get("POSTGRES_DB") == "carspective_test_db"
        assert "test_password" in env.get("POSTGRES_PASSWORD", "")

        options = pg.get("options", "")
        assert "pg_isready" in options

    def test_postgres_job_environment_urls_use_explicit_psycopg2(self):
        """Job environment must set DATABASE_URL and TEST_DATABASE_URL with postgresql+psycopg2://."""
        job = self.jobs["postgres-integration-tests"]
        job_env = job.get("env", {})
        db_url = job_env.get("DATABASE_URL", "")
        test_url = job_env.get("TEST_DATABASE_URL", "")
        assert db_url.startswith("postgresql+psycopg2://")
        assert test_url.startswith("postgresql+psycopg2://")
        assert "carspective_test" in db_url

    def test_postgres_job_includes_remediated_downgrade_drill(self):
        """
        Confirms that the alembic downgrade base drill is restored in CI,
        verifying table removal, enum type removal, and clean re-upgrade.
        """
        job = self.jobs["postgres-integration-tests"]
        steps = job.get("steps", [])
        step_runs = [s.get("run", "") for s in steps]
        drill_steps = [r for r in step_runs if "downgrade base" in r]
        assert len(drill_steps) == 1, "Must contain exactly one downgrade base drill step"

        drill_script = drill_steps[0]
        assert "alembic downgrade base" in drill_script
        assert "alembic upgrade head" in drill_script
        assert "information_schema.tables" in drill_script
        assert "pg_type" in drill_script
        assert "organizationtype" in drill_script
        assert "evidencestate" in drill_script
        assert "hierarchylevel" in drill_script
        assert "f3d730c46a23" in drill_script
        assert "compare_metadata" in drill_script

    def test_postgres_job_includes_failure_diagnostics(self):
        """Job must capture container logs on step failure."""
        job = self.jobs["postgres-integration-tests"]
        steps = job.get("steps", [])
        failure_steps = [s for s in steps if s.get("if") == "failure()"]
        assert len(failure_steps) >= 1
        assert "docker logs" in failure_steps[0].get("run", "")

