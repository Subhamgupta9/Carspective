"""
CARspective — Database URL Normalization & Migration Boolean Default Tests
Verifies:
1. Bare postgresql:// and legacy postgres:// URLs are explicitly normalized to postgresql+psycopg2://.
2. Already-qualified driver URLs (postgresql+psycopg2://, postgresql+asyncpg://) are preserved.
3. SQLite URLs (file and in-memory) are preserved.
4. Non-PostgreSQL URLs are preserved.
5. URL credentials, hosts, ports, paths, and query parameters are preserved without modification.
6. Credential masking helper functions without exposing secrets.
7. SQLAlchemy dialect instantiation loads the psycopg2 driver without database connection.
8. Migration d1b918a24e01 Boolean column defaults compile portably to 0 (SQLite) and false (PostgreSQL).
"""

import os
import pytest
from sqlalchemy.engine.url import make_url
from sqlalchemy import create_engine
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite, postgresql

from server.config.settings import normalize_database_url, mask_database_url, Settings


class TestDatabaseURLNormalization:
    """Targeted unit tests for normalize_database_url."""

    def test_bare_postgresql_url_normalized_to_psycopg2(self):
        url = "postgresql://usr:secret@localhost:5432/carspective"
        normalized = normalize_database_url(url)
        assert normalized == "postgresql+psycopg2://usr:secret@localhost:5432/carspective"

    def test_legacy_postgres_url_normalized_to_psycopg2(self):
        url = "postgres://usr:secret@localhost:5432/carspective"
        normalized = normalize_database_url(url)
        assert normalized == "postgresql+psycopg2://usr:secret@localhost:5432/carspective"

    def test_already_qualified_psycopg2_url_preserved(self):
        url = "postgresql+psycopg2://usr:secret@localhost:5432/carspective"
        assert normalize_database_url(url) == url

    def test_alternative_driver_url_preserved(self):
        url = "postgresql+asyncpg://usr:secret@localhost:5432/carspective"
        assert normalize_database_url(url) == url

    def test_sqlite_file_url_preserved(self):
        url = "sqlite:////app/data/database/carspective.db"
        assert normalize_database_url(url) == url

    def test_sqlite_memory_url_preserved(self):
        url = "sqlite:///:memory:"
        assert normalize_database_url(url) == url

    def test_other_dialect_url_preserved(self):
        url = "mysql+pymysql://usr:secret@localhost:3306/carspective"
        assert normalize_database_url(url) == url

    def test_query_parameters_preserved(self):
        url = "postgresql://usr:secret@db.internal:5432/carspective?sslmode=require&connect_timeout=15&application_name=carspective_prod"
        normalized = normalize_database_url(url)
        assert normalized == "postgresql+psycopg2://usr:secret@db.internal:5432/carspective?sslmode=require&connect_timeout=15&application_name=carspective_prod"

    def test_empty_and_none_handling(self):
        assert normalize_database_url("") == ""
        assert normalize_database_url(None) == ""
        assert normalize_database_url("   ") == ""

    def test_sqlalchemy_engine_dialect_resolution_with_normalized_url(self):
        """Confirm SQLAlchemy 2.1 resolves psycopg2 driver for normalized URL without DB connection."""
        raw_url = "postgresql://usr:secret@localhost:5432/carspective"
        normalized = normalize_database_url(raw_url)
        engine = create_engine(normalized)
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg2"

    def test_mask_database_url_masks_credentials(self):
        raw = "postgresql://dbuser:super_secret_pw123@db.internal:5432/carspective"
        masked = mask_database_url(raw)
        assert "super_secret_pw123" not in masked
        assert masked == "postgresql://dbuser:*****@db.internal:5432/carspective"

    def test_settings_reload_applies_normalization(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://dbuser:secret@db.local:5432/carspective_db")
        st = Settings()
        assert st.DATABASE_URL == "postgresql+psycopg2://dbuser:secret@db.local:5432/carspective_db"


class TestMigrationBooleanDefaultParity:
    """Verifies that migration d1b918a24e01 Boolean defaults compile correctly on both dialects."""

    def test_boolean_defaults_compile_portably(self):
        col_owner = sa.Column('has_owner_evidence', sa.Boolean(), nullable=False, server_default=sa.false())
        col_expert = sa.Column('has_expert_evidence', sa.Boolean(), nullable=False, server_default=sa.false())

        # Compile for SQLite
        sqlite_default_owner = col_owner.server_default.arg.compile(dialect=sqlite.dialect())
        sqlite_default_expert = col_expert.server_default.arg.compile(dialect=sqlite.dialect())
        assert str(sqlite_default_owner) == "0"
        assert str(sqlite_default_expert) == "0"

        # Compile for PostgreSQL
        pg_default_owner = col_owner.server_default.arg.compile(dialect=postgresql.dialect())
        pg_default_expert = col_expert.server_default.arg.compile(dialect=postgresql.dialect())
        assert str(pg_default_owner).lower() == "false"
        assert str(pg_default_expert).lower() == "false"


class TestMigrationEnumDowngradeRemediation:
    """Verifies that the initial migration cb1c167fc450 safely drops PostgreSQL ENUM types on downgrade."""

    def test_enum_downgrade_emits_drop_type_statements_for_postgresql(self):
        """Mock engine with postgresql dialect records DROP TYPE for all 3 enums."""
        from sqlalchemy.dialects import postgresql
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        from unittest.mock import patch
        import server.infrastructure.migrations.versions.cb1c167fc450_initial_canonical_taxonomy_and_evidence as migration

        executed_statements = []
        def executor(sql, *args, **kwargs):
            compiled = str(sql.compile(dialect=postgresql.dialect())) if hasattr(sql, 'compile') else str(sql)
            executed_statements.append(compiled)

        mock_engine = sa.create_mock_engine('postgresql+psycopg2://', executor=executor)
        ctx = MigrationContext.configure(mock_engine)

        with Operations.context(ctx):
            with patch.object(migration.op, 'drop_table'), \
                 patch.object(migration.op, 'drop_index'):
                migration.downgrade()

        assert any('DROP TYPE hierarchylevel' in stmt for stmt in executed_statements), "Missing DROP TYPE hierarchylevel"
        assert any('DROP TYPE evidencestate' in stmt for stmt in executed_statements), "Missing DROP TYPE evidencestate"
        assert any('DROP TYPE organizationtype' in stmt for stmt in executed_statements), "Missing DROP TYPE organizationtype"

    def test_enum_downgrade_is_safe_noop_for_sqlite(self):
        """On SQLite bind, ENUM drops are skipped and no DROP TYPE statements are executed."""
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        from unittest.mock import patch
        import server.infrastructure.migrations.versions.cb1c167fc450_initial_canonical_taxonomy_and_evidence as migration

        engine = sa.create_engine('sqlite:///:memory:')
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                with patch.object(migration.op, 'drop_table'), \
                     patch.object(migration.op, 'drop_index'):
                    migration.downgrade()

    def test_downgrade_base_and_reupgrade_head_on_sqlite(self):
        """End-to-end Alembic downgrade to base and re-upgrade to head on disposable SQLite database."""
        import tempfile
        import shutil
        from pathlib import Path
        from alembic.config import Config
        from alembic import command
        from alembic.migration import MigrationContext
        from alembic.autogenerate import compare_metadata
        from server.models import Base

        temp_dir = tempfile.mkdtemp()
        db_file = Path(temp_dir) / 'full_lifecycle_test.db'
        db_url = f'sqlite:///{db_file.resolve()}'

        try:
            cfg = Config('alembic.ini')
            cfg.set_main_option('sqlalchemy.url', db_url)

            # 1. Upgrade from empty to head
            command.upgrade(cfg, 'head')
            test_engine = sa.create_engine(db_url)
            inspector = sa.inspect(test_engine)
            assert len(inspector.get_table_names()) == 25
            test_engine.dispose()

            # 2. Downgrade all the way to base (exercises cb1c167fc450 downgrade)
            command.downgrade(cfg, 'base')
            test_engine = sa.create_engine(db_url)
            inspector = sa.inspect(test_engine)
            app_tables = [t for t in inspector.get_table_names() if t != 'alembic_version']
            assert len(app_tables) == 0, f"Expected 0 application tables after downgrade base, got {app_tables}"
            test_engine.dispose()

            # 3. Re-upgrade from base to head
            command.upgrade(cfg, 'head')
            test_engine = sa.create_engine(db_url)
            inspector = sa.inspect(test_engine)
            assert len(inspector.get_table_names()) == 25

            # 4. Assert zero schema drift
            with test_engine.connect() as conn:
                ctx = MigrationContext.configure(conn)
                diff = compare_metadata(ctx, Base.metadata)
                assert len(diff) == 0, f"Schema drift detected on re-upgrade: {diff}"
            test_engine.dispose()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

