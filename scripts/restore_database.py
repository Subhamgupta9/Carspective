#!/usr/bin/env python3
"""
CARspective — Phase 19F: Database Restore and Recovery Utility

Provides verified, atomic restoration from SQLite backups with manifest
validation, foreign key validation, pre-restore safety backups, and
strict protection of historical snapshots and model artifacts.

Invariants:
- Validates backup checksum, file size, integrity, and foreign keys against manifest.
- Refuses to overwrite any protected snapshot (*.phase19c_safety_backup*, *.pre_cleanup_snapshot*, *.joblib).
- Overwriting existing target database requires explicit --confirm-overwrite-live flag.
- Creates verified pre-restore safety backup of existing live database before mutation.
- Performs atomic restoration via temporary staging file to avoid partial or corrupt states.
- Re-verifies restored target database integrity and foreign keys before declaring success.
"""

import argparse
import datetime
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("carspective.restore")

DEFAULT_TARGET_DB_PATH = Path("data/database/carspective.db")
EXPECTED_MODEL_PATH = Path("models/carspective_valuation_lgbm_v1.joblib")
EXPECTED_MODEL_MANIFEST_PATH = Path("models/carspective_valuation_lgbm_v1_manifest.json")
EXPECTED_MODEL_SHA256 = "4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1"

PROTECTED_SNAPSHOT_PATTERNS = [
    "*.phase19c_safety_backup*",
    "*.pre_cleanup_snapshot*",
    "*.safety_backup*",
    "*.joblib",
    "*.pkl",
]


class RestoreError(Exception):
    """Raised when backup validation or restoration fails."""
    pass


def compute_sha256(filepath: Path) -> str:
    """Computes SHA-256 checksum of a file in 64KB blocks."""
    if not filepath.is_file():
        raise RestoreError(f"File not found for hash calculation: {filepath}")
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_protected_target(
    path: Path,
    protected_baselines: Optional[List[Path]] = None,
) -> bool:
    """
    Checks if a target path is an immutable baseline snapshot or model artifact.
    Restoration to these paths is strictly forbidden. Resolves canonical paths
    to defeat symlink, hardlink, or relative path traversal bypass attempts.
    """
    try:
        resolved = path.resolve()
    except Exception:
        resolved = path

    # Check both unresolved path and canonical resolved path
    for p in (path, resolved):
        name = p.name
        posix = p.as_posix().lower()

        if "/models/" in f"/{posix}/" or name.endswith(".joblib") or name.endswith(".pkl"):
            return True

        for pattern in PROTECTED_SNAPSHOT_PATTERNS:
            import fnmatch
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(p.name, pattern):
                return True

    # Baseline paths to check
    baselines = protected_baselines or [
        Path("data/database/carspective.db.phase19c_safety_backup"),
        Path("data/database/carspective.db.pre_cleanup_snapshot_20261009_191728"),
        Path("models/carspective_valuation_lgbm_v1.joblib"),
        Path("models/carspective_valuation_lgbm_v1_manifest.json"),
    ]

    for baseline in baselines:
        try:
            b_resolved = baseline.resolve()
            if resolved == b_resolved:
                return True
            if path.exists() and b_resolved.exists() and os.path.samefile(resolved, b_resolved):
                return True
        except Exception:
            pass

    return False


def verify_model_artifact(
    model_path: Optional[Path] = None,
    manifest_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Verifies that the production valuation model artifact exists and matches
    both the expected authoritative SHA-256 hash and its companion manifest.
    Fails closed on any corruption or mismatch.
    """
    m_path = model_path or EXPECTED_MODEL_PATH
    manifest_p = manifest_path or EXPECTED_MODEL_MANIFEST_PATH

    if not m_path.is_file():
        raise RestoreError(f"Model artifact not found at {m_path}")

    actual_hash = compute_sha256(m_path)
    if actual_hash != EXPECTED_MODEL_SHA256:
        raise RestoreError(
            f"Model artifact SHA-256 mismatch! Expected {EXPECTED_MODEL_SHA256}, got {actual_hash}"
        )

    manifest_data = {}
    if manifest_p.is_file():
        try:
            with open(manifest_p, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            manifest_sha = manifest_data.get("artifact", {}).get("sha256")
            if manifest_sha and manifest_sha != actual_hash:
                raise RestoreError(
                    f"Model manifest SHA-256 mismatch! Manifest recorded {manifest_sha}, actual {actual_hash}"
                )
        except json.JSONDecodeError as e:
            raise RestoreError(f"Model manifest JSON corrupted at {manifest_p}: {e}")

    logger.info(f"Model artifact verified: {m_path.name} (SHA-256: {actual_hash})")
    return {
        "model_file": str(m_path),
        "sha256": actual_hash,
        "size_bytes": m_path.stat().st_size,
        "verified": True,
        "manifest_file": str(manifest_p) if manifest_p.is_file() else None,
    }


def find_manifest_for_backup(backup_path: Path) -> Optional[Path]:
    """Locates companion manifest for a backup file."""
    cand1 = backup_path.with_name(f"{backup_path.stem}.manifest.json")
    if cand1.is_file():
        return cand1
    cand2 = backup_path.with_name(f"{backup_path.name}.manifest.json")
    if cand2.is_file():
        return cand2
    return None


def inspect_sqlite_database(db_path: Path) -> Tuple[Dict[str, int], Optional[str], List[Any]]:
    """
    Connects to a SQLite database in read-only mode and inspects:
    1. Integrity check
    2. Foreign key violation list
    3. Table list and row counts
    4. Alembic revision (if table exists)
    """
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=10.0)
    try:
        integrity = conn.execute("PRAGMA integrity_check;").fetchall()
        if not integrity or integrity != [("ok",)]:
            raise RestoreError(f"Integrity check failed for {db_path}: {integrity}")

        fk_violations = conn.execute("PRAGMA foreign_key_check;").fetchall()

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        )
        tables = [row[0] for row in cursor.fetchall()]
        table_counts: Dict[str, int] = {}
        for tbl in tables:
            cnt_row = conn.execute(f'SELECT COUNT(*) FROM "{tbl}";').fetchone()
            table_counts[tbl] = cnt_row[0] if cnt_row else 0

        alembic_version = None
        if "alembic_version" in table_counts:
            v_row = conn.execute("SELECT version_num FROM alembic_version LIMIT 1;").fetchone()
            if v_row:
                alembic_version = str(v_row[0])

        return table_counts, alembic_version, fk_violations
    finally:
        conn.close()


def validate_backup_and_manifest(
    backup_path: Path,
    manifest_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Validates a backup file and its companion manifest before restoration.
    Fails closed if the manifest is missing, invalid, or checksums mismatch.
    """
    if not backup_path.is_file():
        raise RestoreError(f"Backup file does not exist: {backup_path}")

    m_path = manifest_path or find_manifest_for_backup(backup_path)
    if not m_path or not m_path.is_file():
        raise RestoreError(
            f"Companion manifest not found for backup {backup_path}. "
            f"Every backup must have a companion .manifest.json file."
        )

    try:
        with open(m_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
    except json.JSONDecodeError as e:
        raise RestoreError(f"Malformed JSON in companion manifest {m_path}: {e}")

    if not isinstance(manifest_data, dict):
        raise RestoreError(f"Manifest root must be a JSON object, got {type(manifest_data).__name__}")

    # Manifest schema version validation
    manifest_version = manifest_data.get("manifest_version", 1)
    if not isinstance(manifest_version, int) or manifest_version > 1:
        raise RestoreError(f"Unsupported manifest version: {manifest_version} (supported: 1)")

    # Mandatory field presence and type validation
    required_fields = [
        "sha256",
        "file_size_bytes",
        "timestamp_utc",
        "table_counts",
        "integrity_check",
        "foreign_key_violations",
    ]
    missing_fields = [f for f in required_fields if f not in manifest_data]
    if missing_fields:
        raise RestoreError(f"Manifest missing mandatory fields: {missing_fields}")

    recorded_sha = manifest_data["sha256"]
    if not isinstance(recorded_sha, str) or len(recorded_sha) != 64 or not all(c in "0123456789abcdef" for c in recorded_sha.lower()):
        raise RestoreError(f"Manifest contains invalid sha256 format: {recorded_sha}")

    recorded_size = manifest_data["file_size_bytes"]
    if not isinstance(recorded_size, int) or recorded_size < 0:
        raise RestoreError(f"Manifest contains invalid file_size_bytes: {recorded_size}")

    if not isinstance(manifest_data["timestamp_utc"], str) or not manifest_data["timestamp_utc"].strip():
        raise RestoreError("Manifest timestamp_utc must be a non-empty string")

    recorded_counts = manifest_data["table_counts"]
    if not isinstance(recorded_counts, dict) or not all(isinstance(k, str) and isinstance(v, int) and v >= 0 for k, v in recorded_counts.items()):
        raise RestoreError("Manifest table_counts must be a dictionary of table names to non-negative integer row counts")

    if manifest_data["integrity_check"] != "ok":
        raise RestoreError(f"Manifest integrity_check is not 'ok': {manifest_data['integrity_check']}")

    if manifest_data["foreign_key_violations"] != 0:
        raise RestoreError(f"Manifest records foreign key violations: {manifest_data['foreign_key_violations']}")

    # Filename parity check: manifest must match target backup filename
    recorded_filename = manifest_data.get("backup_file")
    if recorded_filename and recorded_filename != backup_path.name:
        raise RestoreError(
            f"Manifest was created for '{recorded_filename}', but backup file is '{backup_path.name}'"
        )

    # Checksum validation
    actual_sha = compute_sha256(backup_path)
    if actual_sha != recorded_sha:
        raise RestoreError(
            f"Backup checksum mismatch! Recorded: {recorded_sha}, Actual: {actual_sha}"
        )

    # Size validation
    actual_size = backup_path.stat().st_size
    if actual_size != recorded_size:
        raise RestoreError(
            f"Backup file size mismatch! Recorded: {recorded_size}, Actual: {actual_size}"
        )

    # Database internal inspection
    table_counts, alembic_version, fk_violations = inspect_sqlite_database(backup_path)

    if fk_violations:
        raise RestoreError(f"Foreign key violations in backup {backup_path}: {fk_violations}")

    if recorded_counts != table_counts:
        raise RestoreError(
            f"Table row counts mismatch against manifest! Recorded: {recorded_counts}, Actual: {table_counts}"
        )

    recorded_alembic = manifest_data.get("alembic_version")
    if recorded_alembic and recorded_alembic != alembic_version:
        raise RestoreError(
            f"Alembic version mismatch! Recorded: {recorded_alembic}, Actual: {alembic_version}"
        )

    logger.info(
        f"Backup validation succeeded: {backup_path.name} "
        f"({len(table_counts)} tables, Alembic: {alembic_version}, SHA-256: {actual_sha[:16]}...)"
    )

    return {
        "backup_path": str(backup_path),
        "manifest_path": str(m_path),
        "manifest_data": manifest_data,
        "sha256": actual_sha,
        "file_size_bytes": actual_size,
        "alembic_version": alembic_version,
        "table_counts": table_counts,
        "foreign_key_violations": 0,
        "integrity_check": "ok",
        "valid": True,
    }


def create_safety_prerestore_backup(target_path: Path) -> Path:
    """
    Creates an exact safety backup of the existing target database before overwriting.
    Checkpoints WAL if applicable and creates a byte-for-byte replica with manifest.
    """
    target_dir = target_path.parent
    timestamp_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    safety_name = f"{target_path.stem}.pre_restore_backup_{timestamp_str}.db"
    safety_path = target_dir / safety_name
    safety_manifest = target_dir / f"{safety_name}.manifest.json"

    logger.info(f"Creating pre-restore safety backup of live database: {safety_path}")

    # Checkpoint WAL if open/active to guarantee disk consistency
    try:
        conn = sqlite3.connect(target_path)
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        conn.close()
    except Exception:
        pass

    # Exact byte copy preserving original checksum and content
    shutil.copy2(target_path, safety_path)

    # Inspect and verify safety backup
    table_counts, alembic_version, fk_violations = inspect_sqlite_database(safety_path)
    if fk_violations:
        safety_path.unlink()
        raise RestoreError(f"Pre-restore safety backup failed foreign key check: {fk_violations}")

    sha = compute_sha256(safety_path)
    size = safety_path.stat().st_size

    manifest_data = {
        "manifest_version": 1,
        "backup_id": f"pre_restore_{timestamp_str}",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_database": str(target_path),
        "backup_file": safety_name,
        "sha256": sha,
        "file_size_bytes": size,
        "alembic_version": alembic_version,
        "table_counts": table_counts,
        "integrity_check": "ok",
        "foreign_key_violations": 0,
        "pre_restore_snapshot": True,
    }

    with open(safety_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    logger.info(f"Pre-restore safety backup verified and saved: {safety_path.name} (SHA-256: {sha[:16]}...)")
    return safety_path


def restore_database(
    backup_path: Path,
    target_path: Path = DEFAULT_TARGET_DB_PATH,
    manifest_path: Optional[Path] = None,
    confirm_overwrite_live: bool = False,
    verify_model: bool = False,
    protected_baselines: Optional[List[Path]] = None,
) -> Dict[str, Any]:
    """
    Restores a database from a verified backup with complete safety checks:
    1. Rejects restore to protected baseline snapshots or model files.
    2. Validates backup checksum, integrity, and manifest parity.
    3. Requires explicit confirmation if overwriting existing target database.
    4. Creates a verified pre-restore safety backup before mutating existing target.
    5. Performs atomic restore via temporary file.
    6. Verifies restored target database integrity before concluding.
    """
    # 1. Reject protected targets
    if is_protected_target(target_path, protected_baselines=protected_baselines):
        raise RestoreError(
            f"Restoration destination '{target_path}' matches protected snapshot or model pattern. "
            f"Overwriting baseline historical snapshots or models is strictly forbidden."
        )

    # 2. Validate backup and manifest
    validation_info = validate_backup_and_manifest(backup_path, manifest_path=manifest_path)

    # 3. Handle existing target database
    safety_backup_path: Optional[Path] = None
    if target_path.exists():
        if not confirm_overwrite_live:
            raise RestoreError(
                f"Target database already exists at '{target_path}'. "
                f"Restoration requires explicit confirmation flag '--confirm-overwrite-live'."
            )
        # Create pre-restore safety snapshot
        safety_backup_path = create_safety_prerestore_backup(target_path)

    # Ensure target parent directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # 4. Atomic restoration via temporary staging database
    temp_target = target_path.parent / f".tmp_restore_{target_path.stem}_{uuid.uuid4().hex[:8]}.db"

    try:
        # Perform online backup copy into temp target
        src_uri = f"file:{backup_path.resolve().as_posix()}?mode=ro"
        src_conn = sqlite3.connect(src_uri, uri=True, timeout=10.0)
        try:
            dest_conn = sqlite3.connect(temp_target)
            try:
                src_conn.backup(dest_conn)
            finally:
                dest_conn.close()
        finally:
            src_conn.close()

        # 5. Verify restored temp database
        temp_counts, temp_alembic, temp_fks = inspect_sqlite_database(temp_target)
        if temp_fks:
            raise RestoreError(f"Restored temporary database has foreign key violations: {temp_fks}")
        if temp_counts != validation_info["table_counts"]:
            raise RestoreError(
                f"Restored temporary database table counts do not match backup manifest! "
                f"Expected: {validation_info['table_counts']}, Got: {temp_counts}"
            )

        # 6. Clean up any existing WAL / SHM auxiliary files for the target
        wal_file = target_path.with_name(f"{target_path.name}-wal")
        shm_file = target_path.with_name(f"{target_path.name}-shm")
        if wal_file.exists():
            try:
                wal_file.unlink()
            except OSError as e:
                logger.warning(f"Failed to remove stale WAL file {wal_file}: {e}")
        if shm_file.exists():
            try:
                shm_file.unlink()
            except OSError as e:
                logger.warning(f"Failed to remove stale SHM file {shm_file}: {e}")

        # 7. Atomic replace
        temp_target.replace(target_path)

        # 8. Final verification of restored target with automatic rollback on failure
        try:
            final_counts, final_alembic, final_fks = inspect_sqlite_database(target_path)
            if final_fks:
                raise RestoreError(f"Post-restore foreign key check failed: {final_fks}")
            if final_counts != validation_info["table_counts"]:
                raise RestoreError(
                    f"Post-restore table count mismatch: Expected {validation_info['table_counts']}, Got {final_counts}"
                )
            final_sha = compute_sha256(target_path)
        except Exception as post_err:
            if safety_backup_path and safety_backup_path.is_file():
                logger.error(
                    f"Post-replacement verification failed ({post_err}). "
                    f"Rolling back to pre-restore safety snapshot: {safety_backup_path.name}"
                )
                try:
                    shutil.copy2(safety_backup_path, target_path)
                    logger.info("Rollback to pre-restore safety snapshot succeeded.")
                except Exception as rollback_err:
                    logger.critical(f"Rollback to pre-restore safety snapshot failed: {rollback_err}")
            raise

        # 9. Verify model artifact if requested
        model_result = None
        if verify_model:
            model_result = verify_model_artifact()

        logger.info(
            f"Restoration completed successfully: {target_path} "
            f"({len(final_counts)} tables, Alembic: {final_alembic}, SHA-256: {final_sha[:16]}...)"
        )

        return {
            "success": True,
            "target_path": str(target_path),
            "source_backup": str(backup_path),
            "safety_backup_path": str(safety_backup_path) if safety_backup_path else None,
            "sha256": final_sha,
            "table_counts": final_counts,
            "alembic_version": final_alembic,
            "model_verified": model_result.get("verified", False) if model_result else None,
            "verified": True,
        }

    except Exception as e:
        if temp_target.exists():
            try:
                temp_target.unlink()
            except OSError:
                pass
        raise RestoreError(f"Restore failed: {e}") from e


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CARspective Database Restore and Recovery Utility (Phase 19F)"
    )
    parser.add_argument(
        "--backup-path",
        type=Path,
        help="Path to the backup SQLite file (.db)",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        help="Path to companion JSON manifest (default: auto-detected)",
    )
    parser.add_argument(
        "--target-db-path",
        type=Path,
        default=DEFAULT_TARGET_DB_PATH,
        help="Target destination database path (default: data/database/carspective.db)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Validate backup and manifest integrity without restoring to target",
    )
    parser.add_argument(
        "--confirm-overwrite-live",
        action="store_true",
        help="Mandatory confirmation flag required when overwriting existing target database",
    )
    parser.add_argument(
        "--verify-model",
        action="store_true",
        help="Verify valuation ML model artifact integrity",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON to stdout",
    )

    args = parser.parse_args()

    try:
        # Check model artifact if requested without backup path
        if args.verify_model and not args.backup_path:
            model_info = verify_model_artifact()
            if args.json:
                print(json.dumps(model_info, indent=2))
            else:
                print(f"VERIFIED MODEL: {model_info['model_file']} (SHA-256: {model_info['sha256']})")
            return 0

        if not args.backup_path:
            parser.error("--backup-path is required unless running model verification only.")

        # Verification-only mode
        if args.verify_only:
            v_info = validate_backup_and_manifest(args.backup_path, manifest_path=args.manifest_path)
            if args.verify_model:
                v_info["model"] = verify_model_artifact()
            if args.json:
                print(json.dumps(v_info, indent=2))
            else:
                print(
                    f"BACKUP VALID: {args.backup_path.name} "
                    f"(SHA-256: {v_info['sha256']}, Tables: {len(v_info['table_counts'])})"
                )
            return 0

        # Full restore mode
        res = restore_database(
            backup_path=args.backup_path,
            target_path=args.target_db_path,
            manifest_path=args.manifest_path,
            confirm_overwrite_live=args.confirm_overwrite_live,
            verify_model=args.verify_model,
        )

        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(
                f"RESTORE SUCCESSFUL: {res['target_path']} "
                f"(SHA-256: {res['sha256'][:16]}..., Tables: {len(res['table_counts'])})"
            )
            if res.get("safety_backup_path"):
                print(f"Pre-restore safety snapshot created at: {res['safety_backup_path']}")

        return 0

    except RestoreError as e:
        logger.error(f"Restore operation failed: {e}")
        if args.json:
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
