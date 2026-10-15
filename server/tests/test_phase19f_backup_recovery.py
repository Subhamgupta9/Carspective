"""
CARspective — Phase 19F: Backup, Restore, and Disaster Recovery Test Suite

Verifies:
1. Online SQLite backup creation with companion manifest generation.
2. End-to-end restore round-trip verification (table counts, data parity, schema parity).
3. Rejection of corrupted backup files (checksum mismatch, malformed database).
4. Rejection of altered or missing companion manifests.
5. Rejection of backups containing foreign-key violations.
6. Deterministic retention pruning (preserves newest valid backup and immutable historical snapshots).
7. Rejection of restoration targeting protected snapshots or model artifacts.
8. Model artifact SHA-256 validation utility and fail-closed behavior on corruption.
9. Temporary staging file cleanup on backup or restore failure.
10. Safety pre-restore snapshot generation when overwriting existing target database.

MANDATORY INVARIANT:
All tests execute strictly against temporary disposable databases created via
tempfile.TemporaryDirectory(). The persistent live database (carspective.db) and
historical safety snapshots are never touched, read, or modified by these tests.
"""

import datetime
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.backup_database import (
    BackupError,
    compute_sha256,
    create_backup,
    inspect_sqlite_database,
    is_protected_path,
    prune_backups,
    verify_backup,
    verify_model_artifact as backup_verify_model,
    DEFAULT_RETENTION_COUNT,
    EXPECTED_MODEL_SHA256,
    EXPECTED_MODEL_PATH,
)
from scripts.restore_database import (
    RestoreError,
    is_protected_target,
    restore_database,
    validate_backup_and_manifest,
    verify_model_artifact as restore_verify_model,
)


@pytest.fixture
def disposable_environment():
    """
    Creates an isolated temporary directory containing a synthetic SQLite database
    with multiple tables, foreign keys, and an Alembic version table.
    """
    temp_dir = tempfile.mkdtemp(prefix="carspective_test_phase19f_")
    base_path = Path(temp_dir)
    db_path = base_path / "test_source.db"
    backup_dir = base_path / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Initialize synthetic schema and data
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript("""
        CREATE TABLE alembic_version (
            version_num VARCHAR(32) NOT NULL PRIMARY KEY
        );
        INSERT INTO alembic_version VALUES ('f3d730c46a23');

        CREATE TABLE manufacturers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            country TEXT
        );

        CREATE TABLE vehicle_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            manufacturer_id INTEGER NOT NULL REFERENCES manufacturers(id),
            name TEXT NOT NULL,
            segment TEXT
        );

        CREATE TABLE market_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id INTEGER NOT NULL REFERENCES vehicle_models(id),
            price REAL NOT NULL,
            year INTEGER NOT NULL
        );

        INSERT INTO manufacturers (id, name, country) VALUES
            (1, 'Maruti Suzuki', 'India'),
            (2, 'Hyundai', 'South Korea'),
            (3, 'Honda', 'Japan');

        INSERT INTO vehicle_models (id, manufacturer_id, name, segment) VALUES
            (10, 1, 'Swift', 'Hatchback'),
            (11, 2, 'Creta', 'SUV'),
            (12, 3, 'City', 'Sedan');

        INSERT INTO market_observations (model_id, price, year) VALUES
            (10, 550000.0, 2019),
            (10, 620000.0, 2020),
            (11, 1150000.0, 2021),
            (12, 980000.0, 2018);
    """)
    conn.commit()
    conn.close()

    yield {
        "base_path": base_path,
        "db_path": db_path,
        "backup_dir": backup_dir,
    }

    # Teardown
    shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# 1. BACKUP CREATION AND COMPANION MANIFEST GENERATION
# ==============================================================================

def test_backup_creation_and_manifest(disposable_environment):
    """Verifies successful online backup creation and companion manifest completeness."""
    env = disposable_environment
    result = create_backup(
        db_path=env["db_path"],
        output_dir=env["backup_dir"],
        retention_count=7,
        prune_after=False,
    )

    assert result["success"] is True
    assert result["verified"] is True
    assert result["alembic_version"] == "f3d730c46a23"
    assert result["table_counts"]["manufacturers"] == 3
    assert result["table_counts"]["vehicle_models"] == 3
    assert result["table_counts"]["market_observations"] == 4
    assert result["table_counts"]["alembic_version"] == 1

    backup_path = Path(result["backup_path"])
    manifest_path = Path(result["manifest_path"])
    assert backup_path.is_file()
    assert manifest_path.is_file()

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["backup_file"] == backup_path.name
    assert manifest["sha256"] == compute_sha256(backup_path)
    assert manifest["file_size_bytes"] == backup_path.stat().st_size
    assert manifest["integrity_check"] == "ok"
    assert manifest["foreign_key_violations"] == 0
    assert "timestamp_utc" in manifest


# ==============================================================================
# 2. RESTORE ROUND-TRIP VERIFICATION
# ==============================================================================

def test_restore_roundtrip_verification(disposable_environment):
    """Verifies that restoring from a valid backup reproduces exact row counts and tables."""
    env = disposable_environment
    backup_res = create_backup(
        db_path=env["db_path"],
        output_dir=env["backup_dir"],
        retention_count=7,
    )
    backup_file = Path(backup_res["backup_path"])

    target_path = env["base_path"] / "restored_roundtrip.db"

    restore_res = restore_database(
        backup_path=backup_file,
        target_path=target_path,
        confirm_overwrite_live=False,
    )

    assert restore_res["success"] is True
    assert restore_res["verified"] is True
    assert target_path.is_file()

    # Verify restored SQLite data
    conn = sqlite3.connect(f"file:{target_path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        tables, alembic, fks = inspect_sqlite_database(target_path)
        assert tables == backup_res["table_counts"]
        assert alembic == "f3d730c46a23"
        assert fks == []

        rows = conn.execute("SELECT name FROM manufacturers ORDER BY id;").fetchall()
        assert [r[0] for r in rows] == ["Maruti Suzuki", "Hyundai", "Honda"]
    finally:
        conn.close()


# ==============================================================================
# 3. CORRUPTED BACKUP REJECTION (CHECKSUM MISMATCH)
# ==============================================================================

def test_corrupted_backup_rejection(disposable_environment):
    """Verifies that tampered or byte-corrupted backup files are rejected fail-closed."""
    env = disposable_environment
    backup_res = create_backup(
        db_path=env["db_path"],
        output_dir=env["backup_dir"],
    )
    backup_file = Path(backup_res["backup_path"])

    # Tamper with backup file bytes
    with open(backup_file, "r+b") as f:
        f.seek(100)
        original = f.read(4)
        f.seek(100)
        f.write(b"\xff\xff\xff\xff" if original != b"\xff\xff\xff\xff" else b"\x00\x00\x00\x00")

    target_path = env["base_path"] / "tampered_restore.db"

    with pytest.raises(RestoreError) as exc_info:
        restore_database(
            backup_path=backup_file,
            target_path=target_path,
        )

    assert "checksum mismatch" in str(exc_info.value).lower()
    assert not target_path.exists()


# ==============================================================================
# 4. ALTERED OR MISSING MANIFEST REJECTION
# ==============================================================================

def test_missing_manifest_rejection(disposable_environment):
    """Verifies that backups missing their companion manifest are rejected."""
    env = disposable_environment
    backup_res = create_backup(
        db_path=env["db_path"],
        output_dir=env["backup_dir"],
    )
    backup_file = Path(backup_res["backup_path"])
    manifest_file = Path(backup_res["manifest_path"])

    # Remove manifest
    manifest_file.unlink()

    target_path = env["base_path"] / "no_manifest_restore.db"
    with pytest.raises(RestoreError) as exc_info:
        restore_database(
            backup_path=backup_file,
            target_path=target_path,
        )

    assert "companion manifest not found" in str(exc_info.value).lower()
    assert not target_path.exists()


def test_altered_manifest_row_count_rejection(disposable_environment):
    """Verifies that manifest table count alterations cause immediate restore rejection."""
    env = disposable_environment
    backup_res = create_backup(
        db_path=env["db_path"],
        output_dir=env["backup_dir"],
    )
    backup_file = Path(backup_res["backup_path"])
    manifest_file = Path(backup_res["manifest_path"])

    # Alter row count in manifest
    with open(manifest_file, "r", encoding="utf-8") as f:
        mdata = json.load(f)
    mdata["table_counts"]["manufacturers"] = 999  # incorrect
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(mdata, f)

    target_path = env["base_path"] / "altered_manifest_restore.db"
    with pytest.raises(RestoreError) as exc_info:
        restore_database(
            backup_path=backup_file,
            target_path=target_path,
        )

    assert "table row counts mismatch" in str(exc_info.value).lower()
    assert not target_path.exists()


# ==============================================================================
# 5. REJECTION OF FOREIGN KEY VIOLATIONS
# ==============================================================================

def test_foreign_key_violation_in_backup_rejected(disposable_environment):
    """Verifies that backups with foreign key violations fail validation closed."""
    env = disposable_environment
    fk_corrupt_db = env["base_path"] / "fk_corrupt.db"

    # Create DB with FK violation by turning FK pragma OFF
    conn = sqlite3.connect(fk_corrupt_db)
    conn.execute("PRAGMA foreign_keys = OFF;")
    conn.executescript("""
        CREATE TABLE parents (id INTEGER PRIMARY KEY);
        CREATE TABLE children (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parents(id));
        INSERT INTO children VALUES (1, 9999); -- Orphaned reference
    """)
    conn.commit()
    conn.close()

    with pytest.raises(BackupError) as exc_info:
        create_backup(
            db_path=fk_corrupt_db,
            output_dir=env["backup_dir"],
        )

    assert "foreign key violations" in str(exc_info.value).lower()


# ==============================================================================
# 6. RETENTION PRUNING & HISTORICAL SNAPSHOT PROTECTION
# ==============================================================================

def test_retention_pruning_and_snapshot_protection(disposable_environment):
    """
    Verifies that retention pruning:
    1. Keeps the newest valid backup even when retention count is exceeded.
    2. Correctly prunes expired backups beyond the retention threshold.
    3. Strictly preserves protected historical snapshots matching invariant patterns.
    """
    env = disposable_environment
    bkp_dir = env["backup_dir"]

    # Create protected historical snapshot files in the backup directory
    prot1 = bkp_dir / "carspective.db.phase19c_safety_backup"
    prot1.write_bytes(b"dummy protected phase19c safety backup")
    prot2 = bkp_dir / "carspective.db.pre_cleanup_snapshot_20261009_191728"
    prot2.write_bytes(b"dummy protected pre_cleanup snapshot")
    prot3 = bkp_dir / "carspective.db.safety_backup_manual"
    prot3.write_bytes(b"dummy protected manual safety backup")

    # Generate 4 mock backups with artificial timestamps
    backup_files = []
    for i in range(4):
        time_offset = datetime.timedelta(hours=i)
        ts = (datetime.datetime(2026, 10, 1, 10, 0, 0, tzinfo=datetime.timezone.utc) + time_offset).strftime("%Y%m%d_%H%M%S")
        bfile = bkp_dir / f"carspective_backup_{ts}.db"
        mfile = bkp_dir / f"carspective_backup_{ts}.manifest.json"

        # Copy valid sqlite db
        shutil.copy(env["db_path"], bfile)
        sha = compute_sha256(bfile)
        mdata = {
            "backup_id": f"carspective_backup_{ts}",
            "timestamp_utc": (datetime.datetime(2026, 10, 1, 10, 0, 0, tzinfo=datetime.timezone.utc) + time_offset).isoformat(),
            "source_database": str(env["db_path"]),
            "backup_file": bfile.name,
            "sha256": sha,
            "file_size_bytes": bfile.stat().st_size,
            "table_counts": {"manufacturers": 3},
            "alembic_version": "f3d730c46a23",
            "integrity_check": "ok",
            "foreign_key_violations": 0,
        }
        with open(mfile, "w", encoding="utf-8") as f:
            json.dump(mdata, f)
        backup_files.append((bfile, mfile))

    # Total valid backups created: 4. Prune with retention_count=2
    pruned = prune_backups(bkp_dir, retention_count=2)

    assert len(pruned) == 2  # The 2 oldest backups should be pruned

    # Verify protected historical files remain 100% intact
    assert prot1.is_file()
    assert prot2.is_file()
    assert prot3.is_file()
    assert prot1.read_bytes() == b"dummy protected phase19c safety backup"

    # Verify the newest backups remain
    newest_bfile, newest_mfile = backup_files[-1]
    second_newest_bfile, second_newest_mfile = backup_files[-2]
    assert newest_bfile.is_file()
    assert newest_mfile.is_file()
    assert second_newest_bfile.is_file()
    assert second_newest_mfile.is_file()

    # Verify oldest backups were pruned
    oldest_bfile, oldest_mfile = backup_files[0]
    assert not oldest_bfile.exists()
    assert not oldest_mfile.exists()


def test_pruning_never_deletes_newest_backup_even_with_zero_retention(disposable_environment):
    """Verifies that pruning never deletes the single newest valid backup even if retention is 0."""
    env = disposable_environment
    bkp_dir = env["backup_dir"]

    # Create single backup
    bfile = bkp_dir / "carspective_backup_20261009_120000.db"
    mfile = bkp_dir / "carspective_backup_20261009_120000.manifest.json"
    shutil.copy(env["db_path"], bfile)
    with open(mfile, "w", encoding="utf-8") as f:
        json.dump({
            "backup_id": "carspective_backup_20261009_120000",
            "timestamp_utc": "2026-10-09T12:00:00Z",
            "backup_file": bfile.name,
            "sha256": compute_sha256(bfile),
            "file_size_bytes": bfile.stat().st_size,
        }, f)

    pruned = prune_backups(bkp_dir, retention_count=0)
    assert len(pruned) == 0
    assert bfile.is_file()
    assert mfile.is_file()


# ==============================================================================
# 7. REJECTION OF OVERWRITING PROTECTED SNAPSHOTS OR MODEL ARTIFACTS
# ==============================================================================

def test_restore_rejects_protected_targets(disposable_environment):
    """Verifies that restore immediately rejects targets matching protected patterns or model files."""
    env = disposable_environment
    backup_res = create_backup(db_path=env["db_path"], output_dir=env["backup_dir"])
    backup_file = Path(backup_res["backup_path"])

    forbidden_targets = [
        env["base_path"] / "carspective.db.phase19c_safety_backup",
        env["base_path"] / "carspective.db.pre_cleanup_snapshot_20261009_191728",
        env["base_path"] / "models" / "carspective_valuation_lgbm_v1.joblib",
        env["base_path"] / "model_backup.joblib",
        env["base_path"] / "arbitrary.pkl",
    ]

    for target in forbidden_targets:
        with pytest.raises(RestoreError) as exc_info:
            restore_database(
                backup_path=backup_file,
                target_path=target,
                confirm_overwrite_live=True,
            )
        assert "protected snapshot or model pattern" in str(exc_info.value).lower()


# ==============================================================================
# 8. PRODUCTION MODEL ARTIFACT SHA-256 VALIDATION
# ==============================================================================

def test_model_artifact_verification(disposable_environment):
    """Verifies that model artifact validation passes for authoritative model and catches tampering."""
    # 1. Authoritative model check
    res = backup_verify_model()
    assert res["verified"] is True
    assert res["sha256"] == EXPECTED_MODEL_SHA256

    res2 = restore_verify_model()
    assert res2["verified"] is True

    # 2. Corrupted model detection
    env = disposable_environment
    fake_model = env["base_path"] / "fake_model.joblib"
    fake_model.write_bytes(b"corrupted model contents")

    with pytest.raises(BackupError) as exc_info:
        backup_verify_model(model_path=fake_model)
    assert "sha-256 mismatch" in str(exc_info.value).lower()

    with pytest.raises(RestoreError) as exc_info2:
        restore_verify_model(model_path=fake_model)
    assert "sha-256 mismatch" in str(exc_info2.value).lower()


# ==============================================================================
# 9. TEMPORARY FILE CLEANUP ON FAILURE
# ==============================================================================

def test_temp_file_cleanup_on_restore_failure(disposable_environment):
    """Verifies that intermediate staging .tmp_* files are cleanly removed if restore fails."""
    env = disposable_environment
    backup_res = create_backup(db_path=env["db_path"], output_dir=env["backup_dir"])
    backup_file = Path(backup_res["backup_path"])

    target_path = env["base_path"] / "fail_cleanup_target.db"

    # Force a failure during final verification step by monkeypatching inspect_sqlite_database
    with patch("scripts.restore_database.inspect_sqlite_database") as mock_inspect:
        # First call (backup validation) works, second call (temp db check) raises error
        mock_inspect.side_effect = [
            (backup_res["table_counts"], "f3d730c46a23", []),
            RestoreError("Simulated mid-restore inspection failure"),
        ]

        with pytest.raises(RestoreError):
            restore_database(
                backup_path=backup_file,
                target_path=target_path,
            )

    # Check that no temporary staging files remain in target directory
    stray_tmp = list(target_path.parent.glob(".tmp_restore_*"))
    assert len(stray_tmp) == 0
    assert not target_path.exists()


# ==============================================================================
# 10. OVERWRITE CONFIRMATION AND PRE-RESTORE SAFETY SNAPSHOT
# ==============================================================================

def test_restore_overwrite_live_requires_flag_and_creates_safety_snapshot(disposable_environment):
    """
    Verifies that:
    1. Overwriting an existing database without --confirm-overwrite-live is blocked.
    2. Overwriting with --confirm-overwrite-live creates a verified pre-restore safety snapshot.
    """
    env = disposable_environment
    backup_res = create_backup(db_path=env["db_path"], output_dir=env["backup_dir"])
    backup_file = Path(backup_res["backup_path"])

    # Target is existing database
    target_path = env["base_path"] / "live_simulation.db"
    shutil.copy(env["db_path"], target_path)

    # 1. Unconfirmed attempt fails
    with pytest.raises(RestoreError) as exc_info:
        restore_database(
            backup_path=backup_file,
            target_path=target_path,
            confirm_overwrite_live=False,
        )
    assert "--confirm-overwrite-live" in str(exc_info.value)

    # 2. Confirmed attempt succeeds and produces pre_restore safety snapshot
    restore_res = restore_database(
        backup_path=backup_file,
        target_path=target_path,
        confirm_overwrite_live=True,
    )

    assert restore_res["success"] is True
    assert restore_res["safety_backup_path"] is not None
    safety_snap = Path(restore_res["safety_backup_path"])
    assert safety_snap.is_file()
    assert "pre_restore_backup" in safety_snap.name
    # Companion manifest for safety backup must exist
    safety_manifest = safety_snap.with_name(f"{safety_snap.name}.manifest.json")
    assert safety_manifest.is_file()


# ==============================================================================
# 11. CLI INTERFACE VERIFICATION
# ==============================================================================

def test_cli_backup_and_restore(disposable_environment):
    """Verifies that backup_database.py and restore_database.py CLI interfaces execute cleanly."""
    env = disposable_environment
    python_exe = sys.executable

    # 1. CLI Backup
    backup_cmd = [
        python_exe,
        "scripts/backup_database.py",
        "--db-path", str(env["db_path"]),
        "--output-dir", str(env["backup_dir"]),
        "--json",
    ]
    res_b = subprocess.run(backup_cmd, capture_output=True, text=True)
    assert res_b.returncode == 0, f"Backup CLI failed: {res_b.stderr}"
    stdout_b = res_b.stdout[res_b.stdout.find("{"):res_b.stdout.rfind("}") + 1]
    b_out = json.loads(stdout_b)
    assert b_out["success"] is True
    backup_file = Path(b_out["backup_path"])
    assert backup_file.is_file()

    # 2. CLI Verify-only
    verify_cmd = [
        python_exe,
        "scripts/restore_database.py",
        "--backup-path", str(backup_file),
        "--verify-only",
        "--json",
    ]
    res_v = subprocess.run(verify_cmd, capture_output=True, text=True)
    assert res_v.returncode == 0, f"Restore verify CLI failed: {res_v.stderr}"
    stdout_v = res_v.stdout[res_v.stdout.find("{"):res_v.stdout.rfind("}") + 1]
    v_out = json.loads(stdout_v)
    assert v_out["valid"] is True

    # 3. CLI Restore
    target_path = env["base_path"] / "cli_restored.db"
    restore_cmd = [
        python_exe,
        "scripts/restore_database.py",
        "--backup-path", str(backup_file),
        "--target-db-path", str(target_path),
        "--json",
    ]
    res_r = subprocess.run(restore_cmd, capture_output=True, text=True)
    assert res_r.returncode == 0, f"Restore CLI failed: {res_r.stderr}"
    stdout_r = res_r.stdout[res_r.stdout.find("{"):res_r.stdout.rfind("}") + 1]
    r_out = json.loads(stdout_r)
    assert r_out["success"] is True
    assert target_path.is_file()


# ==============================================================================
# 12. ADVERSARIAL TESTS (PHASE 19F FINAL SAFETY AUDIT)
# ==============================================================================

def test_relative_path_traversal_and_link_protection(disposable_environment):
    """
    Verifies that relative path traversal (../) or hardlinks pointing to
    protected snapshots or models are resolved canonically and rejected.
    """
    env = disposable_environment
    backup_res = create_backup(db_path=env["db_path"], output_dir=env["backup_dir"])
    backup_file = Path(backup_res["backup_path"])

    # Create dummy protected snapshot in a subdirectory
    sub_dir = env["base_path"] / "subdir"
    sub_dir.mkdir(parents=True, exist_ok=True)
    prot_snap = sub_dir / "carspective.db.phase19c_safety_backup"
    prot_snap.write_bytes(b"protected baseline")

    # Relative path navigation attempt
    traversal_target = sub_dir / "child" / ".." / "carspective.db.phase19c_safety_backup"

    with pytest.raises(RestoreError) as exc_info:
        restore_database(
            backup_path=backup_file,
            target_path=traversal_target,
            confirm_overwrite_live=True,
        )
    assert "protected snapshot or model pattern" in str(exc_info.value).lower()

    # Hardlink attempt (if supported by OS)
    hardlink_target = env["base_path"] / "innocent_looking_name.db"
    try:
        os.link(prot_snap, hardlink_target)
        with pytest.raises(RestoreError) as exc_info2:
            restore_database(
                backup_path=backup_file,
                target_path=hardlink_target,
                confirm_overwrite_live=True,
                protected_baselines=[prot_snap],
            )
        assert "protected snapshot or model pattern" in str(exc_info2.value).lower()
    except OSError:
        pass  # Link creation not permitted on this filesystem


def test_retention_pruning_protects_valid_backup_when_newer_backup_corrupted(disposable_environment):
    """
    Verifies that if a newer backup is corrupt (invalid manifest or corrupted file),
    retention pruning NEVER prunes the older valid backup.
    """
    env = disposable_environment
    bkp_dir = env["backup_dir"]

    # 1. Valid older backup at T1
    b1_file = bkp_dir / "carspective_backup_20261001_100000.db"
    m1_file = bkp_dir / "carspective_backup_20261001_100000.manifest.json"
    shutil.copy(env["db_path"], b1_file)
    with open(m1_file, "w", encoding="utf-8") as f:
        json.dump({
            "manifest_version": 1,
            "backup_id": "carspective_backup_20261001_100000",
            "timestamp_utc": "2026-10-01T10:00:00+00:00",
            "backup_file": b1_file.name,
            "sha256": compute_sha256(b1_file),
            "file_size_bytes": b1_file.stat().st_size,
            "table_counts": {"manufacturers": 3},
            "alembic_version": "f3d730c46a23",
            "integrity_check": "ok",
            "foreign_key_violations": 0,
        }, f)

    # 2. Newer corrupt backup at T2 (checksum mismatch / bad JSON)
    b2_file = bkp_dir / "carspective_backup_20261001_120000.db"
    m2_file = bkp_dir / "carspective_backup_20261001_120000.manifest.json"
    shutil.copy(env["db_path"], b2_file)
    with open(m2_file, "w", encoding="utf-8") as f:
        json.dump({
            "manifest_version": 1,
            "backup_id": "carspective_backup_20261001_120000",
            "timestamp_utc": "2026-10-01T12:00:00+00:00",
            "backup_file": b2_file.name,
            "sha256": "0000000000000000000000000000000000000000000000000000000000000000",  # mismatched
            "file_size_bytes": 999999,
        }, f)

    # Prune with retention_count=1
    pruned = prune_backups(bkp_dir, retention_count=1)

    # Invariant: Valid backup b1 MUST NOT be deleted!
    assert b1_file.is_file()
    assert m1_file.is_file()
    assert b1_file not in pruned


def test_manifest_security_schema_validation(disposable_environment):
    """
    Verifies that manifests missing required fields, containing invalid types,
    or claiming unsupported manifest versions fail closed.
    """
    env = disposable_environment
    backup_res = create_backup(db_path=env["db_path"], output_dir=env["backup_dir"])
    backup_file = Path(backup_res["backup_path"])
    manifest_file = Path(backup_res["manifest_path"])

    with open(manifest_file, "r", encoding="utf-8") as f:
        valid_manifest = json.load(f)

    # 1. Unsupported manifest version
    bad_manifest = dict(valid_manifest)
    bad_manifest["manifest_version"] = 99
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(bad_manifest, f)

    with pytest.raises(RestoreError) as exc_info:
        validate_backup_and_manifest(backup_file)
    assert "unsupported manifest version" in str(exc_info.value).lower()

    # 2. Missing mandatory field (timestamp_utc)
    bad_manifest = dict(valid_manifest)
    del bad_manifest["timestamp_utc"]
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(bad_manifest, f)

    with pytest.raises(RestoreError) as exc_info:
        validate_backup_and_manifest(backup_file)
    assert "missing mandatory fields" in str(exc_info.value).lower()

    # 3. Invalid sha256 checksum format
    bad_manifest = dict(valid_manifest)
    bad_manifest["sha256"] = "not_a_valid_hex_hash"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(bad_manifest, f)

    with pytest.raises(RestoreError) as exc_info:
        validate_backup_and_manifest(backup_file)
    assert "invalid sha256 format" in str(exc_info.value).lower()


def test_manifest_swapped_filename_rejection(disposable_environment):
    """
    Verifies that a manifest generated for backup A cannot be paired with backup B.
    """
    env = disposable_environment
    backup_res = create_backup(db_path=env["db_path"], output_dir=env["backup_dir"])
    backup_file = Path(backup_res["backup_path"])
    manifest_file = Path(backup_res["manifest_path"])

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Change recorded backup_file to point to another file
    manifest["backup_file"] = "carspective_backup_other.db"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    with pytest.raises(RestoreError) as exc_info:
        validate_backup_and_manifest(backup_file)
    assert "manifest was created for 'carspective_backup_other.db'" in str(exc_info.value).lower()


def test_stale_sidecar_cleanup_on_restore(disposable_environment):
    """
    Verifies that restore cleans up stale -wal and -shm files for the target database.
    """
    env = disposable_environment
    backup_res = create_backup(db_path=env["db_path"], output_dir=env["backup_dir"])
    backup_file = Path(backup_res["backup_path"])

    target_path = env["base_path"] / "target_with_sidecars.db"
    shutil.copy(env["db_path"], target_path)

    # Create stale sidecar files
    wal_file = target_path.with_name(f"{target_path.name}-wal")
    shm_file = target_path.with_name(f"{target_path.name}-shm")
    wal_file.write_bytes(b"stale wal data")
    shm_file.write_bytes(b"stale shm data")

    assert wal_file.is_file()
    assert shm_file.is_file()

    restore_res = restore_database(
        backup_path=backup_file,
        target_path=target_path,
        confirm_overwrite_live=True,
    )

    assert restore_res["success"] is True
    # Sidecars should be removed during clean atomic restore
    assert not wal_file.exists()
    assert not shm_file.exists()


def test_post_replacement_failure_automatic_rollback(disposable_environment):
    """
    Verifies that if post-replacement verification fails when overwriting an existing
    database with --confirm-overwrite-live, the target is automatically rolled back
    to the pre-restore safety snapshot.
    """
    env = disposable_environment
    backup_res = create_backup(db_path=env["db_path"], output_dir=env["backup_dir"])
    backup_file = Path(backup_res["backup_path"])

    target_path = env["base_path"] / "live_target.db"
    shutil.copy(env["db_path"], target_path)
    original_target_sha = compute_sha256(target_path)

    # Patch inspect_sqlite_database to fail ONLY on the post-replacement call
    with patch("scripts.restore_database.inspect_sqlite_database") as mock_inspect:
        # Calls:
        # 1. validate_backup_and_manifest
        # 2. create_safety_prerestore_backup
        # 3. temp_target inspection
        # 4. final target inspection -> RAISES ERROR
        mock_inspect.side_effect = [
            (backup_res["table_counts"], "f3d730c46a23", []),
            (backup_res["table_counts"], "f3d730c46a23", []),
            (backup_res["table_counts"], "f3d730c46a23", []),
            RestoreError("Simulated post-replacement disk error"),
        ]

        with pytest.raises(RestoreError) as exc_info:
            restore_database(
                backup_path=backup_file,
                target_path=target_path,
                confirm_overwrite_live=True,
            )
        assert "simulated post-replacement disk error" in str(exc_info.value).lower()

    # Invariant: target_path must be rolled back and intact
    assert target_path.is_file()
    assert compute_sha256(target_path) == original_target_sha
