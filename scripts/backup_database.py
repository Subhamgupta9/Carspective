#!/usr/bin/env python3
"""
CARspective — Phase 19F: Consistent Database Backup Utility

Provides consistent, online SQLite backups with companion cryptographic manifests,
strict integrity and foreign-key verification, and deterministic retention pruning.

Invariants:
- Uses SQLite Connection.backup() for consistent online snapshots without locking writers.
- Generates companion JSON manifest with SHA-256, table row counts, and Alembic version.
- Re-verifies backup integrity (PRAGMA integrity_check & foreign_key_check) before finalizing.
- Deterministic retention pruning protects historical snapshots and always preserves
  the newest valid backup.
- Strict read-only access to source database during backup creation.
"""

import argparse
import datetime
import hashlib
import json
import logging
import os
import re
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
logger = logging.getLogger("carspective.backup")

DEFAULT_DB_PATH = Path("data/database/carspective.db")
DEFAULT_BACKUP_DIR = Path("backups")
DEFAULT_RETENTION_COUNT = 7

EXPECTED_MODEL_PATH = Path("models/carspective_valuation_lgbm_v1.joblib")
EXPECTED_MODEL_MANIFEST_PATH = Path("models/carspective_valuation_lgbm_v1_manifest.json")
EXPECTED_MODEL_SHA256 = "4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1"

PROTECTED_SNAPSHOT_PATTERNS = [
    "*.phase19c_safety_backup*",
    "*.pre_cleanup_snapshot*",
    "*.safety_backup*",
    "*pre_restore_backup*",
]


class BackupError(Exception):
    """Raised when backup creation, verification, or pruning fails."""
    pass


def compute_sha256(filepath: Path) -> str:
    """Computes SHA-256 checksum of a file in 64KB blocks."""
    if not filepath.is_file():
        raise BackupError(f"File not found for hash calculation: {filepath}")
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_protected_path(path: Path) -> bool:
    """
    Checks if a given path matches protected immutable baseline patterns,
    safety backups, or production model artifacts. Resolves canonical paths
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

    # Explicit check against canonical baseline paths if present
    for baseline in [
        Path("data/database/carspective.db.phase19c_safety_backup"),
        Path("data/database/carspective.db.pre_cleanup_snapshot_20261009_191728"),
        Path("models/carspective_valuation_lgbm_v1.joblib"),
        Path("models/carspective_valuation_lgbm_v1_manifest.json"),
    ]:
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
        raise BackupError(f"Model artifact not found at {m_path}")

    actual_hash = compute_sha256(m_path)
    if actual_hash != EXPECTED_MODEL_SHA256:
        raise BackupError(
            f"Model artifact SHA-256 mismatch! Expected {EXPECTED_MODEL_SHA256}, got {actual_hash}"
        )

    manifest_data = {}
    if manifest_p.is_file():
        try:
            with open(manifest_p, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            manifest_sha = manifest_data.get("artifact", {}).get("sha256")
            if manifest_sha and manifest_sha != actual_hash:
                raise BackupError(
                    f"Model manifest SHA-256 mismatch! Manifest recorded {manifest_sha}, actual {actual_hash}"
                )
        except json.JSONDecodeError as e:
            raise BackupError(f"Model manifest JSON corrupted at {manifest_p}: {e}")

    logger.info(f"Model artifact verified: {m_path.name} (SHA-256: {actual_hash})")
    return {
        "model_file": str(m_path),
        "sha256": actual_hash,
        "size_bytes": m_path.stat().st_size,
        "verified": True,
        "manifest_file": str(manifest_p) if manifest_p.is_file() else None,
    }


def inspect_sqlite_database(db_path: Path) -> Tuple[Dict[str, int], Optional[str], List[Any]]:
    """
    Connects to a SQLite database in read-only mode and inspects:
    1. Table list and row counts
    2. Alembic revision (if table exists)
    3. Foreign key violation list
    """
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=10.0)
    try:
        # 1. Integrity check
        integrity = conn.execute("PRAGMA integrity_check;").fetchall()
        if not integrity or integrity != [("ok",)]:
            raise BackupError(f"Integrity check failed for {db_path}: {integrity}")

        # 2. Foreign key check
        fk_violations = conn.execute("PRAGMA foreign_key_check;").fetchall()

        # 3. Tables & row counts
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        )
        tables = [row[0] for row in cursor.fetchall()]
        table_counts: Dict[str, int] = {}
        for tbl in tables:
            cnt_row = conn.execute(f'SELECT COUNT(*) FROM "{tbl}";').fetchone()
            table_counts[tbl] = cnt_row[0] if cnt_row else 0

        # 4. Alembic version
        alembic_version = None
        if "alembic_version" in table_counts:
            v_row = conn.execute("SELECT version_num FROM alembic_version LIMIT 1;").fetchone()
            if v_row:
                alembic_version = str(v_row[0])

        return table_counts, alembic_version, fk_violations
    finally:
        conn.close()


def find_manifest_for_backup(backup_path: Path) -> Optional[Path]:
    """Locates companion manifest for a backup file."""
    # Check <name>.manifest.json
    cand1 = backup_path.with_name(f"{backup_path.stem}.manifest.json")
    if cand1.is_file():
        return cand1
    # Check <name>.db.manifest.json
    cand2 = backup_path.with_name(f"{backup_path.name}.manifest.json")
    if cand2.is_file():
        return cand2
    return None


def verify_backup(backup_path: Path, manifest_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Verifies a backup file against SQLite integrity, foreign key consistency,
    and its companion JSON manifest.
    """
    if not backup_path.is_file():
        raise BackupError(f"Backup file not found: {backup_path}")

    actual_hash = compute_sha256(backup_path)
    actual_size = backup_path.stat().st_size

    # Locate manifest
    m_path = manifest_path or find_manifest_for_backup(backup_path)
    manifest_data = None
    if m_path:
        if not m_path.is_file():
            raise BackupError(f"Specified manifest file not found: {m_path}")
        try:
            with open(m_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
        except json.JSONDecodeError as e:
            raise BackupError(f"Malformed JSON in companion manifest {m_path}: {e}")

        # Check hash
        recorded_hash = manifest_data.get("sha256")
        if recorded_hash and recorded_hash != actual_hash:
            raise BackupError(
                f"Backup SHA-256 mismatch against manifest! Recorded: {recorded_hash}, Actual: {actual_hash}"
            )

        # Check file size
        recorded_size = manifest_data.get("file_size_bytes")
        if recorded_size is not None and recorded_size != actual_size:
            raise BackupError(
                f"Backup file size mismatch against manifest! Recorded: {recorded_size}, Actual: {actual_size}"
            )

    # Inspect SQLite database
    table_counts, alembic_version, fk_violations = inspect_sqlite_database(backup_path)

    if fk_violations:
        raise BackupError(f"Foreign key violations detected in backup {backup_path}: {fk_violations}")

    if manifest_data:
        # Check table counts match manifest
        recorded_counts = manifest_data.get("table_counts", {})
        if recorded_counts and recorded_counts != table_counts:
            discrepancies = {
                t: (recorded_counts.get(t), table_counts.get(t))
                for t in set(recorded_counts) | set(table_counts)
                if recorded_counts.get(t) != table_counts.get(t)
            }
            raise BackupError(f"Table row count mismatch against manifest: {discrepancies}")

        # Check alembic version
        recorded_alembic = manifest_data.get("alembic_version")
        if recorded_alembic and recorded_alembic != alembic_version:
            raise BackupError(
                f"Alembic version mismatch! Recorded: {recorded_alembic}, Actual: {alembic_version}"
            )

    logger.info(
        f"Backup verified successfully: {backup_path.name} "
        f"({len(table_counts)} tables, Alembic: {alembic_version or 'None'}, SHA-256: {actual_hash[:16]}...)"
    )

    return {
        "backup_path": str(backup_path),
        "manifest_path": str(m_path) if m_path else None,
        "sha256": actual_hash,
        "file_size_bytes": actual_size,
        "alembic_version": alembic_version,
        "table_counts": table_counts,
        "foreign_key_violations": 0,
        "integrity_check": "ok",
        "verified": True,
    }


def prune_backups(
    backup_dir: Path,
    retention_count: int = DEFAULT_RETENTION_COUNT,
) -> List[Path]:
    """
    Applies deterministic retention pruning to the backup directory:
    - Retains the latest N valid backups (default: 7).
    - NEVER deletes the newest valid backup under any circumstances.
    - NEVER touches protected historical snapshots (*.phase19c_safety_backup*, *.pre_cleanup_snapshot*, etc.).
    - Deletes pruned .db files and their corresponding companion manifests.
    """
    if not backup_dir.is_dir():
        return []

    # Find candidate backup files
    candidate_backups: List[Tuple[Path, datetime.datetime, Optional[Path]]] = []

    for item in backup_dir.iterdir():
        if not item.is_file() or not item.name.endswith(".db"):
            continue

        # Strictly skip protected snapshots
        if is_protected_path(item):
            logger.info(f"Skipping protected snapshot from pruning consideration: {item.name}")
            continue

        # Look for companion manifest
        manifest_file = find_manifest_for_backup(item)
        if not manifest_file:
            # Not a managed backup from this utility; do not prune unmanaged .db files
            logger.info(f"Skipping unmanaged database file without companion manifest: {item.name}")
            continue

        # Validate candidate backup and manifest integrity
        try:
            with open(manifest_file, "r", encoding="utf-8") as mf:
                mdata = json.load(mf)

            if not isinstance(mdata, dict):
                logger.warning(f"Manifest {manifest_file.name} is not a valid JSON object; excluding from retention candidates.")
                continue

            recorded_sha = mdata.get("sha256")
            if not recorded_sha or not isinstance(recorded_sha, str):
                logger.warning(f"Manifest {manifest_file.name} missing valid sha256; excluding from retention candidates.")
                continue

            # Verify sha256 matches actual file on disk
            actual_sha = compute_sha256(item)
            if actual_sha != recorded_sha:
                logger.warning(f"Backup {item.name} failed checksum verification against manifest; excluding from retention candidates.")
                continue

            # Check file size
            recorded_size = mdata.get("file_size_bytes")
            if recorded_size is not None and item.stat().st_size != recorded_size:
                logger.warning(f"Backup {item.name} size mismatch against manifest; excluding from retention candidates.")
                continue

            # Read timestamp
            ts_str = mdata.get("timestamp_utc")
            if ts_str:
                backup_time = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            else:
                backup_time = datetime.datetime.fromtimestamp(item.stat().st_mtime, tz=datetime.timezone.utc)

        except Exception as e:
            logger.warning(f"Failed to validate backup candidate {item.name} ({e}); excluding from retention consideration.")
            continue

        candidate_backups.append((item, backup_time, manifest_file))

    # Sort descending by timestamp (newest first)
    candidate_backups.sort(key=lambda x: x[1], reverse=True)

    # Invariant: Must retain at least 1 backup (the newest) regardless of retention_count
    effective_retention = max(1, retention_count)

    if len(candidate_backups) <= effective_retention:
        logger.info(
            f"No pruning needed: {len(candidate_backups)} valid backups present "
            f"(retention threshold: {effective_retention})"
        )
        return []

    # Backups to prune are those beyond the retention threshold
    to_prune = candidate_backups[effective_retention:]
    pruned_paths: List[Path] = []

    for db_path, _, m_path in to_prune:
        # Double check it is not protected
        if is_protected_path(db_path):
            continue

        logger.info(f"Pruning expired backup: {db_path.name}")
        try:
            db_path.unlink()
            pruned_paths.append(db_path)
        except OSError as e:
            logger.warning(f"Failed to delete backup file {db_path}: {e}")

        if m_path and m_path.is_file():
            try:
                m_path.unlink()
            except OSError as e:
                logger.warning(f"Failed to delete manifest file {m_path}: {e}")

    logger.info(f"Retention pruning complete. Pruned {len(pruned_paths)} expired backup sets.")
    return pruned_paths


def create_backup(
    db_path: Path = DEFAULT_DB_PATH,
    output_dir: Path = DEFAULT_BACKUP_DIR,
    retention_count: int = DEFAULT_RETENTION_COUNT,
    prune_after: bool = True,
) -> Dict[str, Any]:
    """
    Creates a verified, consistent online SQLite backup using Connection.backup().
    Generates companion manifest and prunes expired backups according to retention policy.
    """
    if not db_path.is_file():
        raise BackupError(f"Source database not found at {db_path}")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp_dt = datetime.datetime.now(datetime.timezone.utc)
    ts_str = timestamp_dt.strftime("%Y%m%d_%H%M%S")
    backup_id = f"carspective_backup_{ts_str}"
    backup_filename = f"{backup_id}.db"
    manifest_filename = f"{backup_id}.manifest.json"

    backup_path = output_dir / backup_filename
    manifest_path = output_dir / manifest_filename

    # Temporary staging path during active backup
    temp_backup_path = output_dir / f".tmp_{backup_id}_{uuid.uuid4().hex[:8]}.db"

    logger.info(f"Initiating online backup of {db_path} -> {backup_path}")

    try:
        # 1. Online backup via SQLite Connection.backup()
        src_uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
        src_conn = sqlite3.connect(src_uri, uri=True, timeout=10.0)
        try:
            dest_conn = sqlite3.connect(temp_backup_path)
            try:
                # Perform online copy
                src_conn.backup(dest_conn)
            finally:
                dest_conn.close()
        finally:
            src_conn.close()

        # 2. Inspect temporary backup before finalizing
        table_counts, alembic_version, fk_violations = inspect_sqlite_database(temp_backup_path)

        if fk_violations:
            raise BackupError(
                f"Integrity check failed: Foreign key violations detected in generated backup: {fk_violations}"
            )

        # 3. Finalize file name atomically
        temp_backup_path.replace(backup_path)

        # 4. Compute cryptographic hash and size
        sha256_hash = compute_sha256(backup_path)
        file_size_bytes = backup_path.stat().st_size

        # 5. Build companion manifest
        manifest_data = {
            "manifest_version": 1,
            "backup_id": backup_id,
            "timestamp_utc": timestamp_dt.isoformat(),
            "source_database": str(db_path),
            "backup_file": backup_filename,
            "sha256": sha256_hash,
            "file_size_bytes": file_size_bytes,
            "alembic_version": alembic_version,
            "table_counts": table_counts,
            "integrity_check": "ok",
            "foreign_key_violations": 0,
        }

        with open(manifest_path, "w", encoding="utf-8") as mf:
            json.dump(manifest_data, mf, indent=2)

        logger.info(f"Companion manifest created at {manifest_path}")

        # 6. Re-verify finalized backup
        verification_result = verify_backup(backup_path, manifest_path)

        # 7. Retention pruning
        pruned_files: List[Path] = []
        if prune_after and retention_count > 0:
            pruned_files = prune_backups(output_dir, retention_count=retention_count)

        result = {
            "success": True,
            "backup_id": backup_id,
            "backup_path": str(backup_path),
            "manifest_path": str(manifest_path),
            "sha256": sha256_hash,
            "file_size_bytes": file_size_bytes,
            "alembic_version": alembic_version,
            "table_counts": table_counts,
            "pruned_files": [str(p) for p in pruned_files],
            "verified": verification_result.get("verified", False),
        }
        return result

    except Exception as e:
        # Clean up temporary staging file if left behind
        if temp_backup_path.exists():
            try:
                temp_backup_path.unlink()
            except OSError:
                pass
        raise BackupError(f"Backup creation failed: {e}") from e


def main() -> int:
    parser = argparse.ArgumentParser(
        description="CARspective Database Backup and Integrity Utility (Phase 19F)"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to source SQLite database (default: data/database/carspective.db)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help="Directory to store backups and manifests (default: backups)",
    )
    parser.add_argument(
        "--retention-count",
        type=int,
        default=DEFAULT_RETENTION_COUNT,
        help="Number of backups to retain during pruning (default: 7)",
    )
    parser.add_argument(
        "--verify",
        type=Path,
        metavar="BACKUP_PATH",
        help="Verify an existing backup file and its companion manifest",
    )
    parser.add_argument(
        "--prune-only",
        action="store_true",
        help="Execute retention pruning on output-dir without creating a new backup",
    )
    parser.add_argument(
        "--verify-model",
        action="store_true",
        help="Verify production valuation ML model artifact integrity",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output result as JSON to stdout",
    )

    args = parser.parse_args()

    try:
        # Check model artifact if requested
        if args.verify_model:
            model_info = verify_model_artifact()
            if args.json and not (args.verify or args.prune_only):
                print(json.dumps(model_info, indent=2))
                return 0

        # Verification mode
        if args.verify:
            res = verify_backup(args.verify)
            if args.json:
                print(json.dumps(res, indent=2))
            else:
                print(f"VERIFIED: {args.verify} (SHA-256: {res['sha256']})")
            return 0

        # Prune only mode
        if args.prune_only:
            pruned = prune_backups(args.output_dir, retention_count=args.retention_count)
            if args.json:
                print(json.dumps({"pruned": [str(p) for p in pruned]}, indent=2))
            else:
                print(f"Pruned {len(pruned)} files.")
            return 0

        # Default: Create new backup
        res = create_backup(
            db_path=args.db_path,
            output_dir=args.output_dir,
            retention_count=args.retention_count,
            prune_after=True,
        )

        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print(
                f"SUCCESS: Backup created at {res['backup_path']} "
                f"(SHA-256: {res['sha256'][:16]}..., Tables: {len(res['table_counts'])})"
            )
        return 0

    except BackupError as e:
        logger.error(f"Backup operation failed: {e}")
        if args.json:
            print(json.dumps({"error": str(e), "success": False}, indent=2))
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
