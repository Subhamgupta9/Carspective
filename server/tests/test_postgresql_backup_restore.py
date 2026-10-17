"""
CARspective — Phase 21D: PostgreSQL Backup & Restore Test Suite

Validates backup creation, cryptographic manifest verification, valuation model invariants,
protected baseline snapshot protection, retention pruning, and restore safety guards.
All tests run with isolated temporary directories or mocked subprocesses.
"""

import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.backup_postgresql import (
    EXPECTED_MODEL_SHA256,
    PostgreSQLBackupError,
    compute_sha256,
    create_postgresql_backup,
    execute_pg_dump,
    find_manifest_for_backup,
    inspect_postgresql_database as backup_inspect_postgresql_database,
    is_protected_path,
    normalize_pg_url as backup_normalize_pg_url,
    prune_retention,
    to_sqlalchemy_url as backup_to_sqlalchemy_url,
    verify_model_artifact,
    verify_postgresql_backup,
)
from scripts.restore_postgresql import (
    PostgreSQLRestoreError,
    execute_pg_restore,
    inspect_postgresql_database as restore_inspect_postgresql_database,
    normalize_pg_url as restore_normalize_pg_url,
    restore_postgresql_backup,
    terminate_backend_connections,
    to_sqlalchemy_url as restore_to_sqlalchemy_url,
    verify_backup_candidate,
)


# ==============================================================================
# 1. CRYPTOGRAPHIC & PROTECTED PATH INVARIANTS
# ==============================================================================

def test_compute_sha256_success_and_missing(tmp_path: Path):
    sample = tmp_path / "sample.bin"
    sample.write_bytes(b"carspective_disaster_recovery_test_data")
    calculated_hash = compute_sha256(sample)
    assert len(calculated_hash) == 64

    with pytest.raises(PostgreSQLBackupError, match="File not found"):
        compute_sha256(tmp_path / "nonexistent.bin")


def test_is_protected_path():
    assert is_protected_path(Path("data/database/carspective.db.phase19c_safety_backup")) is True
    assert is_protected_path(Path("data/database/carspective.db.pre_cleanup_snapshot_20261009_191728")) is True
    assert is_protected_path(Path("models/carspective_valuation_lgbm_v1.joblib")) is True
    assert is_protected_path(Path("models/some_other_model.pkl")) is True
    assert is_protected_path(Path("backups/carspective_pre_restore_backup_2026.dump")) is True

    # Regular backup candidate is not protected
    assert is_protected_path(Path("backups/carspective_pg_backup_20261015_120000.dump")) is False


def test_verify_model_artifact_production():
    result = verify_model_artifact()
    assert result["verified"] is True
    assert result["sha256"] == EXPECTED_MODEL_SHA256
    assert result["size_bytes"] > 0


def test_verify_model_artifact_tampered(tmp_path: Path):
    fake_model = tmp_path / "tampered.joblib"
    fake_model.write_bytes(b"tampered_bytes")
    with pytest.raises(PostgreSQLBackupError, match="Model artifact SHA-256 mismatch"):
        verify_model_artifact(model_path=fake_model)


# ==============================================================================
# 2. MANIFEST VERIFICATION & TAMPERING DETECTION
# ==============================================================================

def test_verify_postgresql_backup_manifest_matching(tmp_path: Path):
    backup_file = tmp_path / "test_backup.dump"
    backup_file.write_bytes(b"simulated_pg_dump_content")
    file_sha = compute_sha256(backup_file)
    file_size = backup_file.stat().st_size

    manifest_file = tmp_path / "test_backup.dump.manifest.json"
    manifest_data = {
        "backup_uuid": "11111111-2222-3333-4444-555555555555",
        "timestamp_utc": "2026-10-15T12:00:00Z",
        "sha256": file_sha,
        "file_size_bytes": file_size,
        "database_type": "postgresql",
        "alembic_version": "f3d730c46a23",
        "table_row_counts": {"manufacturers": 7, "models": 10},
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    result = verify_postgresql_backup(backup_file)
    assert result["verified"] is True
    assert result["sha256"] == file_sha
    assert result["alembic_version"] == "f3d730c46a23"


def test_verify_postgresql_backup_detects_hash_mismatch(tmp_path: Path):
    backup_file = tmp_path / "test_backup.dump"
    backup_file.write_bytes(b"original_content")

    manifest_file = tmp_path / "test_backup.dump.manifest.json"
    manifest_data = {
        "backup_uuid": "test-uuid",
        "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
        "file_size_bytes": backup_file.stat().st_size,
    }
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    with pytest.raises(PostgreSQLBackupError, match="SHA-256 mismatch against manifest"):
        verify_postgresql_backup(backup_file)


# ==============================================================================
# 3. RETENTION PRUNING LOGIC
# ==============================================================================

def test_prune_retention_preserves_newest_and_protected(tmp_path: Path):
    # Create 5 mock backups with different timestamps
    backups = []
    for i in range(5):
        bf = tmp_path / f"carspective_pg_backup_{i}.dump"
        bf.write_bytes(f"backup_{i}".encode("utf-8"))
        mf = tmp_path / f"carspective_pg_backup_{i}.dump.manifest.json"
        mf.write_bytes(b"{}")
        # Set distinct mtimes
        os.utime(bf, (1000 + i * 10, 1000 + i * 10))
        backups.append(bf)

    # Protected backup that must never be pruned
    protected = tmp_path / "carspective_pg_safety_backup_special.dump"
    protected.write_bytes(b"protected_data")
    os.utime(protected, (500, 500))

    # Prune with retention count 2
    pruned = prune_retention(tmp_path, retention_count=2, dry_run=False)

    # Out of 5 candidates, oldest 3 should be pruned
    assert len(pruned) == 3
    assert protected.exists()  # Protected was not pruned
    # Newest backup must remain
    assert backups[-1].exists()
    assert backups[-2].exists()


# ==============================================================================
# 4. SUBPROCESS MOCKING FOR PG_DUMP & PG_RESTORE
# ==============================================================================

def test_execute_pg_dump_invokes_correct_flags_and_isolates_password(tmp_path: Path):
    out_file = tmp_path / "test.dump"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        execute_pg_dump("postgresql://user:secret_password@localhost:5432/db", out_file, pg_dump_bin="pg_dump")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        call_kwargs = mock_run.call_args[1]

        assert cmd[0] == "pg_dump"
        # Invariant: password must NOT be in command line argument
        assert "secret_password" not in str(cmd)
        assert "--dbname=postgresql://user@localhost:5432/db" in cmd
        assert "--format=custom" in cmd
        assert "--compress=9" in cmd
        assert "--no-owner" in cmd
        assert "--no-privileges" in cmd
        # Invariant: password must be passed securely via PGPASSWORD environment variable
        assert call_kwargs.get("env", {}).get("PGPASSWORD") == "secret_password"


def test_execute_pg_restore_invokes_correct_flags_and_isolates_password(tmp_path: Path):
    dump_file = tmp_path / "test.dump"
    dump_file.write_bytes(b"dump_data")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        execute_pg_restore("postgresql://user:secret_password@localhost:5432/db", dump_file, pg_restore_bin="pg_restore")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        call_kwargs = mock_run.call_args[1]

        assert cmd[0] == "pg_restore"
        # Invariant: password must NOT be in command line argument
        assert "secret_password" not in str(cmd)
        assert "--dbname=postgresql://user@localhost:5432/db" in cmd
        assert "--clean" in cmd
        assert "--if-exists" in cmd
        assert "--no-owner" in cmd
        assert "--no-privileges" in cmd
        # Invariant: password must be passed securely via PGPASSWORD environment variable
        assert call_kwargs.get("env", {}).get("PGPASSWORD") == "secret_password"


# ==============================================================================
# 5. RESTORE SAFETY GUARDS & INTEGRITY CHECKS
# ==============================================================================

def test_restore_postgresql_requires_confirm_overwrite_live(tmp_path: Path):
    backup_file = tmp_path / "candidate.dump"
    backup_file.write_bytes(b"dump_content")
    manifest = tmp_path / "candidate.dump.manifest.json"
    manifest.write_text(json.dumps({
        "sha256": compute_sha256(backup_file),
        "file_size_bytes": backup_file.stat().st_size,
        "alembic_version": "f3d730c46a23",
        "table_count": 25,
    }), encoding="utf-8")

    # Mock database inspection returning non-empty database
    with patch("scripts.restore_postgresql.inspect_postgresql_database") as mock_inspect:
        mock_inspect.return_value = {
            "current_database": "carspective_prod",
            "server_version": "PostgreSQL 16.0",
            "table_count": 25,
            "table_counts": {"manufacturers": 7},
            "alembic_version": "f3d730c46a23",
        }

        with pytest.raises(PostgreSQLRestoreError, match="Overwriting requires explicit --confirm-overwrite-live"):
            restore_postgresql_backup(
                backup_path=backup_file,
                db_url="postgresql://user:pass@localhost:5432/carspective_prod",
                confirm_overwrite_live=False,
            )


def test_restore_fails_closed_when_safety_backup_fails(tmp_path: Path):
    """Validates REL-01: restore must strictly abort if safety backup cannot be created."""
    backup_file = tmp_path / "candidate.dump"
    backup_file.write_bytes(b"dump_content")
    manifest = tmp_path / "candidate.dump.manifest.json"
    manifest.write_text(json.dumps({
        "sha256": compute_sha256(backup_file),
        "file_size_bytes": backup_file.stat().st_size,
        "alembic_version": "f3d730c46a23",
        "table_count": 25,
    }), encoding="utf-8")

    with patch("scripts.restore_postgresql.inspect_postgresql_database") as mock_inspect, \
         patch("scripts.restore_postgresql.create_safety_backup", side_effect=PostgreSQLRestoreError("Disk full")):
        mock_inspect.return_value = {
            "current_database": "carspective_prod",
            "server_version": "PostgreSQL 16.0",
            "table_count": 25,
            "table_counts": {"manufacturers": 7},
            "alembic_version": "f3d730c46a23",
        }

        with pytest.raises(PostgreSQLRestoreError, match="Disk full"):
            restore_postgresql_backup(
                backup_path=backup_file,
                db_url="postgresql://user:pass@localhost:5432/carspective_prod",
                confirm_overwrite_live=True,
            )


# ==============================================================================
# 6. DRIVER SELECTION & URL NORMALIZATION FOR CONSUMERS
# ==============================================================================

@pytest.mark.parametrize("norm_func", [backup_normalize_pg_url, restore_normalize_pg_url])
def test_normalize_pg_url_variants(norm_func):
    """
    Validates that normalize_pg_url yields clean libpq-compatible 'postgresql://' URLs
    and strips Python DBAPI specifiers like '+psycopg2'.
    """
    assert norm_func("postgresql://usr:secret@localhost:5432/carspective") == "postgresql://usr:secret@localhost:5432/carspective"
    assert norm_func("postgres://usr:secret@localhost:5432/carspective") == "postgresql://usr:secret@localhost:5432/carspective"
    assert norm_func("postgresql+psycopg2://usr:secret@localhost:5432/carspective") == "postgresql://usr:secret@localhost:5432/carspective"
    assert norm_func("") == ""
    assert norm_func(None) == ""
    assert norm_func("   ") == ""


@pytest.mark.parametrize("to_sa_func", [backup_to_sqlalchemy_url, restore_to_sqlalchemy_url])
def test_to_sqlalchemy_url_variants(to_sa_func):
    """
    Validates that to_sqlalchemy_url normalizes generic PostgreSQL URLs to
    explicitly select the 'psycopg2' DBAPI driver ('postgresql+psycopg2://').
    """
    assert to_sa_func("postgresql://usr:secret@localhost:5432/carspective") == "postgresql+psycopg2://usr:secret@localhost:5432/carspective"
    assert to_sa_func("postgres://usr:secret@localhost:5432/carspective") == "postgresql+psycopg2://usr:secret@localhost:5432/carspective"
    assert to_sa_func("postgresql+psycopg2://usr:secret@localhost:5432/carspective") == "postgresql+psycopg2://usr:secret@localhost:5432/carspective"
    assert to_sa_func("sqlite:///:memory:") == "sqlite:///:memory:"
    assert to_sa_func("") == ""
    assert to_sa_func(None) == ""
    assert to_sa_func("   ") == ""


def test_execute_pg_dump_normalizes_psycopg2_input_for_libpq(tmp_path: Path):
    """
    Confirms that execute_pg_dump normalizes a 'postgresql+psycopg2://' connection string
    down to standard 'postgresql://' before invoking the libpq pg_dump subprocess.
    """
    out_file = tmp_path / "test_norm.dump"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        execute_pg_dump("postgresql+psycopg2://user:secret_password@localhost:5432/db", out_file, pg_dump_bin="pg_dump")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        # Invariant: libpq command must NOT contain '+psycopg2'
        assert "+psycopg2" not in str(cmd)
        assert "--dbname=postgresql://user@localhost:5432/db" in cmd
        assert mock_run.call_args[1].get("env", {}).get("PGPASSWORD") == "secret_password"


def test_execute_pg_restore_normalizes_psycopg2_input_for_libpq(tmp_path: Path):
    """
    Confirms that execute_pg_restore normalizes a 'postgresql+psycopg2://' connection string
    down to standard 'postgresql://' before invoking the libpq pg_restore subprocess.
    """
    dump_file = tmp_path / "test_norm.dump"
    dump_file.write_bytes(b"data")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        execute_pg_restore("postgresql+psycopg2://user:secret_password@localhost:5432/db", dump_file, pg_restore_bin="pg_restore")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        # Invariant: libpq command must NOT contain '+psycopg2'
        assert "+psycopg2" not in str(cmd)
        assert "--dbname=postgresql://user@localhost:5432/db" in cmd
        assert mock_run.call_args[1].get("env", {}).get("PGPASSWORD") == "secret_password"


@pytest.mark.parametrize("inspect_fn", [backup_inspect_postgresql_database, restore_inspect_postgresql_database])
def test_inspect_database_passes_psycopg2_url_to_sqlalchemy(inspect_fn):
    """
    Confirms that inspect_postgresql_database in both backup and restore scripts
    converts raw 'postgresql://' into 'postgresql+psycopg2://' when calling sa.create_engine.
    """
    with patch("sqlalchemy.create_engine") as mock_create_engine:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = ("PostgreSQL 16.0", "carspective_prod")
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_create_engine.return_value = mock_engine

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_inspect.return_value.get_table_names.return_value = []
            inspect_fn("postgresql://usr:secret@localhost:5432/carspective_prod")

            mock_create_engine.assert_called_once()
            called_url = mock_create_engine.call_args[0][0]
            assert called_url == "postgresql+psycopg2://usr:secret@localhost:5432/carspective_prod"


def test_terminate_backend_connections_passes_psycopg2_url_to_sqlalchemy():
    """
    Confirms that terminate_backend_connections converts raw 'postgresql://'
    into 'postgresql+psycopg2://' when calling sa.create_engine.
    """
    with patch("sqlalchemy.create_engine") as mock_create_engine:
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = (2,)
        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn
        mock_create_engine.return_value = mock_engine

        terminated = terminate_backend_connections("postgresql://usr:secret@localhost:5432/carspective_prod")
        assert terminated == 2

        mock_create_engine.assert_called_once()
        called_url = mock_create_engine.call_args[0][0]
        assert called_url == "postgresql+psycopg2://usr:secret@localhost:5432/carspective_prod"
