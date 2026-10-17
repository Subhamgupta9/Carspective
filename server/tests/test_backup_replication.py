"""
CARspective — Phase 23B: Backup Orchestration & Off-Site Replication Unit Tests
Tests concurrency locking, S3 replication adapter, verification, failure injection,
credential redaction, retention synchronization, and disaster recovery retrieval.
All tests run with isolated temporary directories and mocked cloud interactions.
"""

import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.orchestrate_backup import (
    BackupOrchestrationError,
    DryRunStorageAdapter,
    LockError,
    ProcessLock,
    S3StorageAdapter,
    SensitiveFilter,
    StorageError,
    orchestrate_backup,
    redact_sensitive_string,
    retrieve_remote_backup,
    verify_remote_backup,
)
from scripts.backup_postgresql import PostgreSQLBackupError


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def tmp_staging(tmp_path: Path) -> Path:
    staging = tmp_path / "staging_backups"
    staging.mkdir(parents=True, exist_ok=True)
    return staging


@pytest.fixture
def dummy_backup_files(tmp_staging: Path):
    """Creates a valid mock backup dump and matching companion manifest."""
    dump_path = tmp_staging / "carspective_pg_backup_20261017_120000.dump"
    dump_content = b"PGDMP_DUMMY_BINARY_DATA_FOR_UNIT_TESTS" * 20
    dump_path.write_bytes(dump_content)

    import hashlib
    hasher = hashlib.sha256()
    hasher.update(dump_content)
    sha256_hash = hasher.hexdigest()

    manifest_path = tmp_staging / "carspective_pg_backup_20261017_120000.dump.manifest.json"
    manifest_data = {
        "backup_uuid": "11111111-2222-3333-4444-555555555555",
        "backup_filename": dump_path.name,
        "database_type": "postgresql",
        "timestamp_utc": "2026-10-17T12:00:00+00:00",
        "sha256": sha256_hash,
        "file_size_bytes": len(dump_content),
        "database_name": "carspective_prod",
        "server_version": "16.1",
        "alembic_version": "f3d730c46a23",
        "table_count": 25,
        "table_row_counts": {"manufacturers": 7, "users": 1},
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    return dump_path, manifest_path, sha256_hash, len(dump_content)


# ==============================================================================
# 1. CONCURRENCY PROCESS LOCKING TESTS
# ==============================================================================

def test_process_lock_acquisition_and_release(tmp_path: Path):
    """Confirms ProcessLock acquires exclusively and cleans up on release."""
    lock_file = tmp_path / "test.lock"
    assert not lock_file.exists()

    with ProcessLock(lock_file) as lock:
        assert lock_file.exists()
        with open(lock_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert data.get("pid") == os.getpid()

    assert not lock_file.exists()


def test_process_lock_prevents_overlapping_runs(tmp_path: Path):
    """Confirms that an active lock prevents a concurrent process from executing."""
    lock_file = tmp_path / "test.lock"

    with ProcessLock(lock_file):
        # Attempt to acquire the same lock without timeout
        second_lock = ProcessLock(lock_file, timeout_seconds=0.0)
        with pytest.raises(LockError) as exc_info:
            second_lock.acquire()
        assert "Another backup orchestration job is currently running" in str(exc_info.value)


# ==============================================================================
# 2. LOCAL VERIFICATION & FAILURE INJECTION TESTS
# ==============================================================================

def test_orchestrate_backup_fails_closed_on_db_dump_failure(tmp_staging: Path):
    """Ensures that failure during local pg_dump aborts orchestration immediately."""
    with patch(
        "scripts.orchestrate_backup.create_postgresql_backup",
        side_effect=PostgreSQLBackupError("pg_dump process crashed"),
    ):
        with pytest.raises(BackupOrchestrationError) as exc:
            orchestrate_backup(
                db_url="postgresql://usr:pwd@localhost:5432/carspective_prod",
                staging_dir=tmp_staging,
                storage_adapter=None,
            )
        assert "Local PostgreSQL backup creation failed" in str(exc.value)


def test_orchestrate_backup_fails_closed_on_missing_manifest(tmp_staging: Path, dummy_backup_files):
    """Ensures pre-replication audit fails if companion manifest is missing."""
    dump_path, manifest_path, _, _ = dummy_backup_files
    manifest_path.unlink()  # Remove manifest to simulate corruption

    with patch("scripts.orchestrate_backup.create_postgresql_backup") as mock_create:
        mock_create.return_value = {
            "success": True,
            "backup_file": str(dump_path),
            "manifest_file": str(manifest_path),
            "sha256": "fakehash",
            "file_size_bytes": 100,
            "alembic_version": "f3d730c46a23",
            "table_count": 25,
            "pruned_backups": [],
        }
        with pytest.raises(BackupOrchestrationError) as exc:
            orchestrate_backup(
                db_url="postgresql://usr:pwd@localhost:5432/carspective_prod",
                staging_dir=tmp_staging,
                storage_adapter=None,
            )
        assert "Pre-replication integrity audit rejected backup" in str(exc.value)


def test_orchestrate_backup_fails_closed_on_manifest_checksum_mismatch(tmp_staging: Path, dummy_backup_files):
    """Ensures pre-replication audit fails if SHA-256 does not match file bytes."""
    dump_path, manifest_path, _, _ = dummy_backup_files

    # Tamper with manifest checksum
    with open(manifest_path, "r", encoding="utf-8") as f:
        m_data = json.load(f)
    m_data["sha256"] = "0000000000000000000000000000000000000000000000000000000000000000"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(m_data, f)

    with patch("scripts.orchestrate_backup.create_postgresql_backup") as mock_create:
        mock_create.return_value = {
            "success": True,
            "backup_file": str(dump_path),
            "manifest_file": str(manifest_path),
            "sha256": m_data["sha256"],
            "file_size_bytes": dump_path.stat().st_size,
            "alembic_version": "f3d730c46a23",
            "table_count": 25,
            "pruned_backups": [],
        }
        with pytest.raises(BackupOrchestrationError) as exc:
            orchestrate_backup(
                db_url="postgresql://usr:pwd@localhost:5432/carspective_prod",
                staging_dir=tmp_staging,
                storage_adapter=None,
            )
        assert "Pre-replication integrity audit rejected backup" in str(exc.value)


# ==============================================================================
# 3. S3 REPLICATION ADAPTER TESTS
# ==============================================================================

def test_s3_adapter_requires_bucket_name():
    """Confirms S3StorageAdapter rejects missing or empty bucket names."""
    with pytest.raises(StorageError) as exc:
        S3StorageAdapter(bucket_name="")
    assert "S3 bucket name must be specified" in str(exc.value)


def test_orchestrate_backup_success_with_s3_mock(tmp_staging: Path, dummy_backup_files):
    """
    Tests end-to-end backup orchestration with a mocked boto3 S3 client,
    verifying put_object arguments (SSE-S3 AES256, metadata) and head_object verification.
    """
    dump_path, manifest_path, sha256_hash, file_size = dummy_backup_files

    mock_client = MagicMock()
    mock_client.put_object.return_value = {"ETag": '"dummy-etag"'}
    mock_client.head_object.side_effect = [
        # Call 1: head_object on dump file
        {
            "ContentLength": file_size,
            "ServerSideEncryption": "AES256",
            "ETag": '"dummy-etag-1"',
            "Metadata": {"sha256": sha256_hash},
        },
        # Call 2: head_object on manifest file
        {
            "ContentLength": manifest_path.stat().st_size,
            "ServerSideEncryption": "AES256",
            "ETag": '"dummy-etag-2"',
            "Metadata": {"sha256": sha256_hash},
        },
    ]

    adapter = S3StorageAdapter(
        bucket_name="carspective-offsite-backups",
        region_name="ap-south-1",
        sse_algorithm="AES256",
        client=mock_client,
    )

    with patch("scripts.orchestrate_backup.create_postgresql_backup") as mock_create:
        mock_create.return_value = {
            "success": True,
            "backup_file": str(dump_path),
            "manifest_file": str(manifest_path),
            "sha256": sha256_hash,
            "file_size_bytes": file_size,
            "alembic_version": "f3d730c46a23",
            "table_count": 25,
            "pruned_backups": [],
        }

        result = orchestrate_backup(
            db_url="postgresql://usr:secret@localhost:5432/carspective_prod",
            staging_dir=tmp_staging,
            storage_adapter=adapter,
            s3_prefix="production/postgres/",
        )

        assert result["success"] is True
        assert result["replication"]["replicated"] is True
        assert result["replication"]["server_side_encryption"] == "AES256"
        assert result["replication"]["remote_dump_key"] == f"production/postgres/{dump_path.name}"
        assert result["replication"]["remote_manifest_key"] == f"production/postgres/{manifest_path.name}"

        # Verify client calls
        assert mock_client.put_object.call_count == 2
        first_call_kwargs = mock_client.put_object.call_args_list[0][1]
        assert first_call_kwargs["Bucket"] == "carspective-offsite-backups"
        assert first_call_kwargs["ServerSideEncryption"] == "AES256"
        assert first_call_kwargs["Metadata"]["sha256"] == sha256_hash


def test_orchestrate_backup_fails_closed_on_s3_upload_error(tmp_staging: Path, dummy_backup_files):
    """
    Ensures that S3 upload network/permission failure raises StorageError,
    fails closed, and PRESERVES the local backup file.
    """
    dump_path, manifest_path, sha256_hash, file_size = dummy_backup_files

    mock_client = MagicMock()
    mock_client.put_object.side_effect = RuntimeError("S3 AccessDenied 403")

    adapter = S3StorageAdapter(
        bucket_name="carspective-offsite-backups",
        client=mock_client,
    )

    with patch("scripts.orchestrate_backup.create_postgresql_backup") as mock_create:
        mock_create.return_value = {
            "success": True,
            "backup_file": str(dump_path),
            "manifest_file": str(manifest_path),
            "sha256": sha256_hash,
            "file_size_bytes": file_size,
            "alembic_version": "f3d730c46a23",
            "table_count": 25,
            "pruned_backups": [],
        }

        with pytest.raises(StorageError) as exc:
            orchestrate_backup(
                db_url="postgresql://usr:secret@localhost:5432/carspective_prod",
                staging_dir=tmp_staging,
                storage_adapter=adapter,
            )
        assert "Off-site backup replication failed" in str(exc.value)
        # Verify local backup and manifest remain completely preserved
        assert dump_path.is_file()
        assert manifest_path.is_file()


def test_orchestrate_backup_fails_closed_on_remote_size_mismatch(tmp_staging: Path, dummy_backup_files):
    """Ensures remote verification fails closed if remote ContentLength does not match local size."""
    dump_path, manifest_path, sha256_hash, file_size = dummy_backup_files

    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    mock_client.head_object.return_value = {
        "ContentLength": file_size + 999,  # Corrupted remote size
        "ServerSideEncryption": "AES256",
        "Metadata": {"sha256": sha256_hash},
    }

    adapter = S3StorageAdapter(bucket_name="my-bucket", client=mock_client)

    with patch("scripts.orchestrate_backup.create_postgresql_backup") as mock_create:
        mock_create.return_value = {
            "success": True,
            "backup_file": str(dump_path),
            "manifest_file": str(manifest_path),
            "sha256": sha256_hash,
            "file_size_bytes": file_size,
            "alembic_version": "f3d730c46a23",
            "table_count": 25,
            "pruned_backups": [],
        }
        with pytest.raises(StorageError) as exc:
            orchestrate_backup(
                db_url="postgresql://usr:secret@localhost:5432/carspective_prod",
                staging_dir=tmp_staging,
                storage_adapter=adapter,
            )
        assert "Remote S3 object size mismatch" in str(exc.value)


def test_orchestrate_backup_fails_closed_when_encryption_unverified(tmp_staging: Path, dummy_backup_files):
    """Ensures remote verification fails if remote object lacks required ServerSideEncryption."""
    dump_path, manifest_path, sha256_hash, file_size = dummy_backup_files

    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    mock_client.head_object.return_value = {
        "ContentLength": file_size,
        "ServerSideEncryption": None,  # Missing encryption
        "Metadata": {"sha256": sha256_hash},
    }

    adapter = S3StorageAdapter(bucket_name="my-bucket", sse_algorithm="AES256", client=mock_client)

    with patch("scripts.orchestrate_backup.create_postgresql_backup") as mock_create:
        mock_create.return_value = {
            "success": True,
            "backup_file": str(dump_path),
            "manifest_file": str(manifest_path),
            "sha256": sha256_hash,
            "file_size_bytes": file_size,
            "alembic_version": "f3d730c46a23",
            "table_count": 25,
            "pruned_backups": [],
        }
        with pytest.raises(StorageError) as exc:
            orchestrate_backup(
                db_url="postgresql://usr:secret@localhost:5432/carspective_prod",
                staging_dir=tmp_staging,
                storage_adapter=adapter,
            )
        assert "Remote S3 encryption mismatch" in str(exc.value)


# ==============================================================================
# 4. DRY-RUN & RETENTION SYNCHRONIZATION TESTS
# ==============================================================================

def test_orchestrate_backup_dry_run_mode(tmp_staging: Path, dummy_backup_files):
    """Confirms dry-run mode completes orchestration using DryRunStorageAdapter without cloud calls."""
    dump_path, manifest_path, sha256_hash, file_size = dummy_backup_files
    dry_adapter = DryRunStorageAdapter(bucket_name="test-dryrun-bucket")

    with patch("scripts.orchestrate_backup.create_postgresql_backup") as mock_create:
        mock_create.return_value = {
            "success": True,
            "backup_file": str(dump_path),
            "manifest_file": str(manifest_path),
            "sha256": sha256_hash,
            "file_size_bytes": file_size,
            "alembic_version": "f3d730c46a23",
            "table_count": 25,
            "pruned_backups": [],
        }

        result = orchestrate_backup(
            db_url="postgresql://usr:secret@localhost:5432/carspective_prod",
            staging_dir=tmp_staging,
            storage_adapter=dry_adapter,
            dry_run=True,
        )

        assert result["success"] is True
        assert result["dry_run"] is True
        assert result["replication"]["replicated"] is True


def test_orchestrate_backup_remote_retention_pruning(tmp_staging: Path, dummy_backup_files):
    """Confirms older remote backups are pruned while preserving the newly uploaded backup."""
    dump_path, manifest_path, sha256_hash, file_size = dummy_backup_files

    mock_client = MagicMock()
    mock_client.put_object.return_value = {}
    mock_client.head_object.side_effect = [
        # Call 1: head_object on dump file
        {
            "ContentLength": file_size,
            "ServerSideEncryption": "AES256",
            "Metadata": {"sha256": sha256_hash},
        },
        # Call 2: head_object on manifest file
        {
            "ContentLength": manifest_path.stat().st_size,
            "ServerSideEncryption": "AES256",
            "Metadata": {"sha256": sha256_hash},
        },
    ]

    # Simulate 3 existing remote backups
    paginator = MagicMock()
    paginator.paginate.return_value = [{
        "Contents": [
            {"Key": f"backups/{dump_path.name}", "Size": file_size},
            {"Key": "backups/carspective_pg_backup_20261016_120000.dump", "Size": file_size},
            {"Key": "backups/carspective_pg_backup_20261015_120000.dump", "Size": file_size},
            {"Key": "backups/carspective_pg_backup_20261014_120000.dump", "Size": file_size},
        ]
    }]
    mock_client.get_paginator.return_value = paginator

    adapter = S3StorageAdapter(bucket_name="my-bucket", client=mock_client)

    with patch("scripts.orchestrate_backup.create_postgresql_backup") as mock_create:
        mock_create.return_value = {
            "success": True,
            "backup_file": str(dump_path),
            "manifest_file": str(manifest_path),
            "sha256": sha256_hash,
            "file_size_bytes": file_size,
            "alembic_version": "f3d730c46a23",
            "table_count": 25,
            "pruned_backups": [],
        }

        result = orchestrate_backup(
            db_url="postgresql://usr:secret@localhost:5432/carspective_prod",
            staging_dir=tmp_staging,
            storage_adapter=adapter,
            s3_prefix="backups/",
            remote_retention_count=2,  # Retain only 2
        )

        assert result["success"] is True
        pruned = result["replication"]["pruned_remote"]
        # The oldest backup should be pruned; newly uploaded backup must NOT be pruned
        assert f"backups/{dump_path.name}" not in pruned
        assert mock_client.delete_object.called


# ==============================================================================
# 5. DISASTER RECOVERY RETRIEVAL TESTS
# ==============================================================================

def test_retrieve_remote_backup_downloads_and_verifies(tmp_path: Path, dummy_backup_files):
    """
    Tests retrieve_remote_backup: downloads remote dump and manifest to local dir
    and runs full cryptographic SHA-256 and manifest verification.
    """
    dump_path, manifest_path, sha256_hash, file_size = dummy_backup_files
    download_dir = tmp_path / "recovered_backups"

    mock_client = MagicMock()

    # When downloading, write the actual bytes to local path
    def mock_download(bucket, key, fileobj):
        if key.endswith(".manifest.json"):
            fileobj.write(manifest_path.read_bytes())
        else:
            fileobj.write(dump_path.read_bytes())

    mock_client.download_fileobj.side_effect = mock_download

    adapter = S3StorageAdapter(bucket_name="my-bucket", client=mock_client)
    res = retrieve_remote_backup(
        storage_adapter=adapter,
        remote_dump_key=f"carspective-backups/{dump_path.name}",
        output_dir=download_dir,
        verify=True,
    )

    assert res["success"] is True
    assert res["verified"] is True
    assert res["sha256"] == sha256_hash
    assert Path(res["retrieved_dump"]).is_file()
    assert Path(res["retrieved_manifest"]).is_file()


def test_verify_remote_backup_inspects_manifest_and_object(tmp_path: Path, dummy_backup_files):
    """Tests verify_remote_backup inspecting remote metadata without full dump download."""
    dump_path, manifest_path, sha256_hash, file_size = dummy_backup_files

    mock_client = MagicMock()
    mock_client.head_object.return_value = {
        "ContentLength": file_size,
        "ServerSideEncryption": "AES256",
        "Metadata": {"sha256": sha256_hash},
    }

    def mock_download(bucket, key, fileobj):
        fileobj.write(manifest_path.read_bytes())

    mock_client.download_fileobj.side_effect = mock_download

    adapter = S3StorageAdapter(bucket_name="my-bucket", client=mock_client)
    res = verify_remote_backup(
        storage_adapter=adapter,
        remote_dump_key=f"carspective-backups/{dump_path.name}",
    )

    assert res["verified"] is True
    assert res["sha256"] == sha256_hash
    assert res["file_size_bytes"] == file_size
    assert res["alembic_version"] == "f3d730c46a23"


# ==============================================================================
# 6. LOGGING & SENSITIVE CREDENTIAL REDACTION TESTS
# ==============================================================================

def test_sensitive_filter_redacts_credentials():
    """Confirms SensitiveFilter sanitizes database passwords, tokens, and AWS keys."""
    filt = SensitiveFilter()

    def make_record(msg: str, args: tuple = ()) -> logging.LogRecord:
        return logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0, msg=msg, args=args, exc_info=None
        )

    # 1. DB URL password in msg
    r1 = make_record("Connecting to postgresql://postgres:super_secret_pw@10.0.0.5:5432/carspective_prod")
    filt.filter(r1)
    assert "super_secret_pw" not in r1.msg
    assert "postgresql://postgres:*****@10.0.0.5:5432/carspective_prod" in r1.msg

    # 2. AWS Access Key ID in msg
    r2 = make_record("Using AWS Access Key AKIAIOSFODNN7EXAMPLE for S3 upload")
    filt.filter(r2)
    assert "AKIAIOSFODNN7EXAMPLE" not in r2.msg
    assert "AKIA****************" in r2.msg

    # 3. Bearer Token in msg
    r3 = make_record("Header Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")
    filt.filter(r3)
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in r3.msg
    assert "[REDACTED_TOKEN]" in r3.msg

    # 4. Format argument tuple with DB URL
    r4 = make_record("Database target: %s", ("postgresql://dbuser:super_secret_pwd@127.0.0.1:5432/carspective",))
    filt.filter(r4)
    assert "super_secret_pwd" not in r4.args[0]
    assert "postgresql://dbuser:*****@127.0.0.1:5432/carspective" in r4.args[0]
    assert "super_secret_pwd" not in r4.getMessage()

    # 5. Dict argument with AWS secret
    r5 = make_record("Credentials: %(key)s", ({"key": "AKIAIOSFODNN7EXAMPLE"},))
    filt.filter(r5)
    assert "AKIAIOSFODNN7EXAMPLE" not in str(r5.args)
    assert "AKIA****************" in str(r5.args)
    assert "AKIAIOSFODNN7EXAMPLE" not in r5.getMessage()
    assert "AKIA****************" in r5.getMessage()


def test_redact_sensitive_string_direct():
    """Confirms direct string redaction handles URLs, tokens, and AWS access keys."""
    raw = "Connect to postgresql://admin:my_secret@db.internal:5432/prod with AKIAIOSFODNN7EXAMPLE"
    sanitized = redact_sensitive_string(raw)
    assert "my_secret" not in sanitized
    assert "AKIAIOSFODNN7EXAMPLE" not in sanitized
    assert "postgresql://admin:*****@db.internal:5432/prod" in sanitized
    assert "AKIA****************" in sanitized


# ==============================================================================
# 7. REMEDIATION REGRESSION TESTS (SEC-01, DOC-01, SEC-03)
# ==============================================================================

def test_process_lock_stale_pid_recovery_posix(tmp_path: Path):
    """
    SEC-01: Confirms that ProcessLock detects dead PIDs on POSIX (ProcessLookupError)
    and reclaims the lock safely, while preserving locks held by active processes.
    """
    lock_file = tmp_path / "stale_posix.lock"

    # Case 1: Dead PID on POSIX raises ProcessLookupError -> must be recognized as stale!
    with open(lock_file, "w", encoding="utf-8") as f:
        json.dump({"pid": 99999999, "timestamp_utc": "2026-10-17T00:00:00Z"}, f)

    with patch("sys.platform", "linux"), patch("os.kill", side_effect=ProcessLookupError):
        lock = ProcessLock(lock_file)
        assert lock._is_stale() is True
        # Acquisition must successfully reclaim the stale lock
        lock.acquire()
        assert lock._acquired is True
        lock.release()

    # Case 2: Live PID on POSIX -> os.kill succeeds without error -> not stale!
    with open(lock_file, "w", encoding="utf-8") as f:
        json.dump({"pid": 12345, "timestamp_utc": "2026-10-17T00:00:00Z"}, f)

    with patch("sys.platform", "linux"), patch("os.kill", return_value=None):
        lock = ProcessLock(lock_file)
        assert lock._is_stale() is False

    # Case 3: PermissionError on POSIX -> process exists under different UID -> not stale!
    with open(lock_file, "w", encoding="utf-8") as f:
        json.dump({"pid": 1, "timestamp_utc": "2026-10-17T00:00:00Z"}, f)

    with patch("sys.platform", "linux"), patch("os.kill", side_effect=PermissionError):
        lock = ProcessLock(lock_file)
        assert lock._is_stale() is False

    # Case 4: Malformed JSON or negative/zero PID -> must be recognized as stale!
    with open(lock_file, "w", encoding="utf-8") as f:
        f.write("CORRUPT_NOT_JSON")
    lock = ProcessLock(lock_file)
    assert lock._is_stale() is True

    with open(lock_file, "w", encoding="utf-8") as f:
        json.dump({"pid": -99}, f)
    lock = ProcessLock(lock_file)
    assert lock._is_stale() is True


def test_process_lock_stale_pid_recovery_windows(tmp_path: Path):
    """
    SEC-01: Confirms that ProcessLock detects dead PIDs on Windows (OpenProcess == 0, GetLastError == 87)
    and reclaims stale lock, while respecting ERROR_ACCESS_DENIED (5) as an active process.
    """
    lock_file = tmp_path / "stale_win.lock"

    # Case 1: Dead PID on Windows -> OpenProcess returns 0, GetLastError returns 87
    with open(lock_file, "w", encoding="utf-8") as f:
        json.dump({"pid": 88888888, "timestamp_utc": "2026-10-17T00:00:00Z"}, f)

    mock_kernel32 = MagicMock()
    mock_kernel32.OpenProcess.return_value = 0
    mock_kernel32.GetLastError.return_value = 87

    with patch("sys.platform", "win32"), patch("ctypes.windll.kernel32", mock_kernel32):
        lock = ProcessLock(lock_file)
        assert lock._is_stale() is True

    # Case 2: Protected PID on Windows -> OpenProcess returns 0, GetLastError returns 5 (Access Denied)
    mock_kernel32.OpenProcess.return_value = 0
    mock_kernel32.GetLastError.return_value = 5

    with patch("sys.platform", "win32"), patch("ctypes.windll.kernel32", mock_kernel32):
        lock = ProcessLock(lock_file)
        assert lock._is_stale() is False


def test_orchestrate_backup_skip_on_lock_contention(tmp_staging: Path, dummy_backup_files):
    """
    DOC-01: Confirms that when a lock is actively held:
    1. By default (fail_on_lock=False): skips cleanly and returns skipped=True.
    2. With fail_on_lock=True: raises LockError for callers requiring hard failure.
    """
    dump_path, manifest_path, sha256_hash, file_size = dummy_backup_files
    lock_file = tmp_staging / "active_test.lock"

    # Acquire lock with a live lock
    with ProcessLock(lock_file):
        # 1. Default: skip cleanly
        res = orchestrate_backup(
            db_url="postgresql://usr:secret@localhost:5432/carspective_prod",
            staging_dir=tmp_staging,
            lock_file=lock_file,
            fail_on_lock=False,
        )
        assert res["success"] is True
        assert res["skipped"] is True
        assert res["reason"] == "lock_active"

        # 2. fail_on_lock=True: raises LockError
        with pytest.raises(LockError) as exc:
            orchestrate_backup(
                db_url="postgresql://usr:secret@localhost:5432/carspective_prod",
                staging_dir=tmp_staging,
                lock_file=lock_file,
                fail_on_lock=True,
            )
        assert "Another backup orchestration job is currently running" in str(exc.value)


def test_retrieve_remote_backup_rejects_path_traversal(tmp_path: Path):
    """SEC-03: Confirms retrieve_remote_backup rejects directory traversal attempts."""
    download_dir = tmp_path / "retrieve_target"
    mock_adapter = MagicMock()

    # Traversal attempt with ..
    with pytest.raises(StorageError) as exc1:
        retrieve_remote_backup(
            storage_adapter=mock_adapter,
            remote_dump_key="../../etc/shadow.dump",
            output_dir=download_dir,
        )
    assert "Invalid remote backup key" in str(exc1.value) or "Path traversal" in str(exc1.value)

    # Invalid extension (.sh instead of .dump)
    with pytest.raises(StorageError) as exc2:
        retrieve_remote_backup(
            storage_adapter=mock_adapter,
            remote_dump_key="backups/malicious_payload.sh",
            output_dir=download_dir,
        )
    assert "recognized dump suffix" in str(exc2.value)

    # Empty key
    with pytest.raises(StorageError) as exc3:
        retrieve_remote_backup(
            storage_adapter=mock_adapter,
            remote_dump_key="   ",
            output_dir=download_dir,
        )
    assert "Remote dump key must be specified" in str(exc3.value)


def test_retrieve_remote_backup_protected_path_rejection(tmp_path: Path):
    """SEC-03: Confirms retrieve_remote_backup rejects writing into protected historical snapshots."""
    mock_adapter = MagicMock()

    with pytest.raises(StorageError) as exc:
        retrieve_remote_backup(
            storage_adapter=mock_adapter,
            remote_dump_key="carspective.db.phase19c_safety_backup.dump",
            output_dir=tmp_path,
        )
    assert "Destination path is protected" in str(exc.value)


def test_retrieve_remote_backup_overwrite_guard(tmp_path: Path, dummy_backup_files):
    """
    SEC-03: Confirms retrieve_remote_backup fails when target file exists and overwrite=False,
    and succeeds when overwrite=True.
    """
    dump_path, manifest_path, sha256_hash, file_size = dummy_backup_files
    download_dir = tmp_path / "retrieve_overwrite_test"
    download_dir.mkdir(parents=True, exist_ok=True)

    # Pre-create destination file
    pre_existing_file = download_dir / dump_path.name
    pre_existing_file.write_bytes(b"PRE_EXISTING_USER_DATA")

    mock_client = MagicMock()

    def mock_download(bucket, key, fileobj):
        if key.endswith(".manifest.json"):
            fileobj.write(manifest_path.read_bytes())
        else:
            fileobj.write(dump_path.read_bytes())

    mock_client.download_fileobj.side_effect = mock_download
    adapter = S3StorageAdapter(bucket_name="my-bucket", client=mock_client)

    # 1. overwrite=False (default): must fail closed and preserve pre-existing file
    with pytest.raises(StorageError) as exc:
        retrieve_remote_backup(
            storage_adapter=adapter,
            remote_dump_key=f"backups/{dump_path.name}",
            output_dir=download_dir,
            overwrite=False,
        )
    assert "Destination dump file already exists" in str(exc.value)
    assert pre_existing_file.read_bytes() == b"PRE_EXISTING_USER_DATA"

    # 2. overwrite=True: replaces destination file
    res = retrieve_remote_backup(
        storage_adapter=adapter,
        remote_dump_key=f"backups/{dump_path.name}",
        output_dir=download_dir,
        overwrite=True,
    )
    assert res["success"] is True
    assert pre_existing_file.read_bytes() != b"PRE_EXISTING_USER_DATA"


def test_retrieve_remote_backup_partial_download_cleanup_on_failure(tmp_path: Path, dummy_backup_files):
    """
    SEC-03: Confirms that if download or cryptographic verification fails mid-operation,
    partial downloaded files are cleaned up while unrelated pre-existing files are preserved.
    """
    dump_path, manifest_path, sha256_hash, file_size = dummy_backup_files
    download_dir = tmp_path / "cleanup_test"
    download_dir.mkdir(parents=True, exist_ok=True)

    # Pre-existing unrelated file in download dir
    unrelated_file = download_dir / "unrelated_notes.txt"
    unrelated_file.write_text("DO_NOT_DELETE_ME")

    mock_client = MagicMock()

    def mock_download_corrupt(bucket, key, fileobj):
        if key.endswith(".manifest.json"):
            fileobj.write(manifest_path.read_bytes())
        else:
            fileobj.write(b"CORRUPTED_BYTES_MISMATCHED_CHECKSUM")

    mock_client.download_fileobj.side_effect = mock_download_corrupt
    adapter = S3StorageAdapter(bucket_name="my-bucket", client=mock_client)

    with pytest.raises(StorageError) as exc:
        retrieve_remote_backup(
            storage_adapter=adapter,
            remote_dump_key=f"backups/{dump_path.name}",
            output_dir=download_dir,
            verify=True,
        )
    assert "failed cryptographic verification" in str(exc.value)

    # Downloaded dump and manifest should be cleaned up
    assert not (download_dir / dump_path.name).exists()
    assert not (download_dir / manifest_path.name).exists()

    # Pre-existing unrelated file must remain intact
    assert unrelated_file.exists()
    assert unrelated_file.read_text() == "DO_NOT_DELETE_ME"
