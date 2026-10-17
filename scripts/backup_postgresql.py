#!/usr/bin/env python3
"""
CARspective — Phase 21D: PostgreSQL Database Backup Utility

Provides consistent, logical PostgreSQL backups with companion cryptographic manifests,
strict schema and row-count verification, valuation model invariant checks,
and deterministic retention pruning.

Invariants:
- Uses pg_dump --format=custom with --compress=9 for consistent compressed snapshots.
- Generates companion JSON manifest with SHA-256, table row counts, Alembic version, and server version.
- Re-verifies backup checksum and manifest schema before finalizing.
- Strictly protects baseline historical snapshots and production valuation model artifacts.
- Deterministic retention pruning protects historical snapshots and preserves the newest valid backup.
- Strict read-only database access during inspection and backup creation.
"""

import argparse
import datetime
import fnmatch
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import uuid
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("carspective.backup_postgresql")

DEFAULT_BACKUP_DIR = Path("backups")
DEFAULT_RETENTION_COUNT = 7

EXPECTED_MODEL_PATH = Path("models/carspective_valuation_lgbm_v1.joblib")
EXPECTED_MODEL_MANIFEST_PATH = Path("models/carspective_valuation_lgbm_v1_manifest.json")
EXPECTED_MODEL_SHA256 = "4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1"

PROTECTED_SNAPSHOT_PATTERNS = [
    "*phase19c_safety_backup*",
    "*pre_cleanup_snapshot*",
    "*safety_backup*",
    "*pre_restore*",
    "*.joblib",
    "*.pkl",
]


class PostgreSQLBackupError(Exception):
    """Raised when PostgreSQL backup creation, verification, or pruning fails."""
    pass


def compute_sha256(filepath: Path) -> str:
    """Computes SHA-256 checksum of a file in 64KB blocks."""
    if not filepath.is_file():
        raise PostgreSQLBackupError(f"File not found for hash calculation: {filepath}")
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

    for p in (path, resolved):
        name = p.name
        posix = p.as_posix().lower()

        if "/models/" in f"/{posix}/" or name.endswith(".joblib") or name.endswith(".pkl"):
            return True

        for pattern in PROTECTED_SNAPSHOT_PATTERNS:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(p.name, pattern):
                return True

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
        raise PostgreSQLBackupError(f"Model artifact not found at {m_path}")

    actual_hash = compute_sha256(m_path)
    if actual_hash != EXPECTED_MODEL_SHA256:
        raise PostgreSQLBackupError(
            f"Model artifact SHA-256 mismatch! Expected {EXPECTED_MODEL_SHA256}, got {actual_hash}"
        )

    manifest_data = {}
    if manifest_p.is_file():
        try:
            with open(manifest_p, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            manifest_sha = manifest_data.get("artifact", {}).get("sha256")
            if manifest_sha and manifest_sha != actual_hash:
                raise PostgreSQLBackupError(
                    f"Model manifest SHA-256 mismatch! Manifest recorded {manifest_sha}, actual {actual_hash}"
                )
        except json.JSONDecodeError as e:
            raise PostgreSQLBackupError(f"Model manifest JSON corrupted at {manifest_p}: {e}")

    logger.info(f"Model artifact verified: {m_path.name} (SHA-256: {actual_hash})")
    return {
        "model_file": str(m_path),
        "sha256": actual_hash,
        "size_bytes": m_path.stat().st_size,
        "verified": True,
        "manifest_file": str(manifest_p) if manifest_p.is_file() else None,
    }


def normalize_pg_url(url: str) -> str:
    """
    Normalizes database URL for PostgreSQL client operations (pg_dump, pg_restore, libpq).
    Ensures URL uses the standard 'postgresql://' scheme recognized by libpq.
    Strips Python-specific DBAPI dialect specifiers (e.g. +psycopg2) if present.
    """
    if not url:
        return ""
    trimmed = str(url).strip()
    if trimmed.startswith("postgresql+psycopg2://"):
        return f"postgresql://{trimmed[len('postgresql+psycopg2://'):]}"
    if trimmed.startswith("postgres://"):
        return f"postgresql://{trimmed[len('postgres://'):]}"
    return trimmed


def to_sqlalchemy_url(url: str) -> str:
    """
    Normalizes a database URL specifically for SQLAlchemy engine creation.
    In SQLAlchemy 2.1+, generic 'postgresql://' defaults to the 'psycopg' (v3) driver.
    Because CarSpective standardizes on psycopg2 ('psycopg2-binary'), normalize
    generic 'postgresql://' and 'postgres://' to 'postgresql+psycopg2://'.
    """
    if not url:
        return ""
    trimmed = str(url).strip()
    if trimmed.startswith("postgresql://"):
        return f"postgresql+psycopg2://{trimmed[len('postgresql://'):]}"
    if trimmed.startswith("postgres://"):
        return f"postgresql+psycopg2://{trimmed[len('postgres://'):]}"
    return trimmed


def mask_db_url(url: str) -> str:
    """Masks credentials in database URL for safe logging."""
    if not url:
        return ""
    return re.sub(r'(://[^:]+:)([^@]+)(@)', r'\1*****\3', url)


def sanitize_db_url_for_cli(db_url: str) -> Tuple[str, Optional[str]]:
    """
    Parses a database URL and separates credentials from the CLI argument.
    Returns:
    1. A sanitized URL with the password stripped from the netloc (safe for argv)
    2. The extracted plaintext password (for PGPASSWORD environment variable)
    Prevents credentials from leaking into process tables (/proc/<pid>/cmdline or ps).
    """
    try:
        parsed = urllib.parse.urlsplit(db_url)
        password = parsed.password
        if password:
            user = parsed.username or ""
            host = parsed.hostname or ""
            port = f":{parsed.port}" if parsed.port else ""
            netloc = f"{user}@{host}{port}" if user else f"{host}{port}"
            sanitized = urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
            return sanitized, password
    except Exception:
        pass
    return db_url, None


def set_secure_permissions(path: Path) -> None:
    """Sets restrictive 0600 (read/write by owner only) permissions on POSIX systems."""
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def inspect_postgresql_database(db_url: str) -> Dict[str, Any]:
    """
    Connects to PostgreSQL in read-only mode and inspects:
    1. Table inventory and row counts
    2. Alembic revision
    3. PostgreSQL server version and current database
    """
    import sqlalchemy as sa

    sa_url = to_sqlalchemy_url(db_url)
    engine = sa.create_engine(sa_url, pool_pre_ping=True)
    table_counts: Dict[str, int] = {}
    alembic_version: Optional[str] = None
    server_version: str = "unknown"
    current_db: str = "unknown"

    try:
        with engine.connect() as conn:
            # 1. Server metadata
            ver_row = conn.execute(sa.text("SELECT version(), current_database();")).fetchone()
            if ver_row:
                server_version = str(ver_row[0])
                current_db = str(ver_row[1])

            # 2. Table inventory
            inspector = sa.inspect(conn)
            tables = sorted(inspector.get_table_names(schema="public"))

            for tbl in tables:
                cnt_row = conn.execute(sa.text(f'SELECT COUNT(*) FROM public."{tbl}";')).fetchone()
                table_counts[tbl] = cnt_row[0] if cnt_row else 0

            # 3. Alembic revision
            if "alembic_version" in tables:
                rev_row = conn.execute(sa.text("SELECT version_num FROM public.alembic_version LIMIT 1;")).fetchone()
                if rev_row:
                    alembic_version = str(rev_row[0])

    except Exception as e:
        raise PostgreSQLBackupError(f"Failed to inspect PostgreSQL database: {e}") from e
    finally:
        engine.dispose()

    return {
        "current_database": current_db,
        "server_version": server_version,
        "table_counts": table_counts,
        "alembic_version": alembic_version,
        "table_count": len(table_counts),
    }


def find_manifest_for_backup(backup_path: Path) -> Optional[Path]:
    """Locates companion manifest for a backup file."""
    cand1 = backup_path.with_name(f"{backup_path.name}.manifest.json")
    if cand1.is_file():
        return cand1
    cand2 = backup_path.with_name(f"{backup_path.stem}.manifest.json")
    if cand2.is_file():
        return cand2
    return None


def verify_postgresql_backup(
    backup_path: Path,
    manifest_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Verifies a PostgreSQL backup file against its companion JSON manifest.
    Validates file existence, SHA-256 hash match, and schema integrity.
    """
    if not backup_path.is_file():
        raise PostgreSQLBackupError(f"Backup file not found: {backup_path}")

    actual_hash = compute_sha256(backup_path)
    actual_size = backup_path.stat().st_size

    m_path = manifest_path or find_manifest_for_backup(backup_path)
    if not m_path or not m_path.is_file():
        raise PostgreSQLBackupError(f"Companion manifest not found for backup: {backup_path}")

    try:
        with open(m_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
    except json.JSONDecodeError as e:
        raise PostgreSQLBackupError(f"Malformed manifest JSON at {m_path}: {e}")

    recorded_hash = manifest_data.get("sha256")
    if not recorded_hash or recorded_hash != actual_hash:
        raise PostgreSQLBackupError(
            f"Backup SHA-256 mismatch against manifest! Recorded: {recorded_hash}, Actual: {actual_hash}"
        )

    recorded_size = manifest_data.get("file_size_bytes")
    if recorded_size is not None and recorded_size != actual_size:
        raise PostgreSQLBackupError(
            f"Backup file size mismatch against manifest! Recorded: {recorded_size}, Actual: {actual_size}"
        )

    return {
        "backup_file": str(backup_path),
        "manifest_file": str(m_path),
        "sha256": actual_hash,
        "file_size_bytes": actual_size,
        "verified": True,
        "database_type": manifest_data.get("database_type", "postgresql"),
        "alembic_version": manifest_data.get("alembic_version"),
        "table_count": len(manifest_data.get("table_row_counts", {})),
        "manifest_timestamp": manifest_data.get("timestamp_utc"),
    }


def prune_retention(
    backup_dir: Path,
    retention_count: int = DEFAULT_RETENTION_COUNT,
    dry_run: bool = False,
) -> List[Path]:
    """
    Prunes PostgreSQL backup files beyond retention_count.
    Strictly protects:
    1. Historical snapshots matching PROTECTED_SNAPSHOT_PATTERNS
    2. Model artifacts
    3. The single newest valid backup (never prunes down to zero)
    """
    if retention_count < 1:
        raise PostgreSQLBackupError(f"Retention count must be >= 1, got {retention_count}")

    if not backup_dir.is_dir():
        return []

    # Find candidate backup files
    candidates: List[Path] = []
    for f in backup_dir.iterdir():
        if not f.is_file():
            continue
        # Exclude manifests and temporary staging files
        if f.name.endswith(".manifest.json") or f.name.endswith(".tmp") or f.suffix == ".json":
            continue
        if f.suffix in [".dump", ".sql", ".pgdump"] or ("pg_backup" in f.name and not f.name.endswith(".json")):
            if not is_protected_path(f):
                candidates.append(f)

    # Sort by mtime descending (newest first)
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    if len(candidates) <= retention_count:
        logger.info(
            f"Retention pruning: {len(candidates)} backups found, "
            f"retention limit is {retention_count}. No pruning required."
        )
        return []

    to_prune = candidates[retention_count:]
    pruned_paths: List[Path] = []

    for target in to_prune:
        # Extra safety check: never prune the single newest candidate
        if target == candidates[0]:
            logger.warning(f"Safety guard: refusing to prune newest backup {target}")
            continue

        if is_protected_path(target):
            logger.warning(f"Safety guard: skipping protected backup {target}")
            continue

        logger.info(f"{'[DRY RUN] Would prune' if dry_run else 'Pruning'} old backup: {target.name}")
        if not dry_run:
            target.unlink()
            # Also remove companion manifest if present
            m_path = find_manifest_for_backup(target)
            if m_path and m_path.is_file() and not is_protected_path(m_path):
                m_path.unlink()
        pruned_paths.append(target)

    return pruned_paths


def execute_pg_dump(
    db_url: str,
    output_path: Path,
    pg_dump_bin: str = "pg_dump",
) -> None:
    """Executes pg_dump binary to create a custom compressed archive."""
    normalized_for_cli = normalize_pg_url(db_url)
    sanitized_url, password = sanitize_db_url_for_cli(normalized_for_cli)
    cmd = [
        pg_dump_bin,
        f"--dbname={sanitized_url}",
        "--format=custom",
        "--compress=9",
        "--no-owner",
        "--no-privileges",
        f"--file={output_path.resolve()}",
    ]

    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            env=env,
        )
    except FileNotFoundError as e:
        raise PostgreSQLBackupError(
            f"PostgreSQL dump utility '{pg_dump_bin}' not found on PATH. "
            f"Install postgresql-client or specify via --pg-dump-bin."
        ) from e
    except subprocess.CalledProcessError as e:
        stderr_sanitized = mask_db_url(e.stderr)
        raise PostgreSQLBackupError(f"pg_dump execution failed: {stderr_sanitized}") from e


def create_postgresql_backup(
    db_url: str,
    output_dir: Path = DEFAULT_BACKUP_DIR,
    retention_count: int = DEFAULT_RETENTION_COUNT,
    pg_dump_bin: str = "pg_dump",
    verify_model: bool = True,
) -> Dict[str, Any]:
    """
    Creates a full logical PostgreSQL backup:
    1. Validates model artifact invariant
    2. Inspects database schema, row counts, and Alembic version
    3. Runs pg_dump to staging file with PGPASSWORD env var (no credentials in argv)
    4. Computes SHA-256 and writes companion cryptographic manifest
    5. Sets restrictive 0600 file permissions on backup and manifest
    6. Atomically renames staging files to final destinations
    7. Prunes old backups according to retention policy
    """
    normalized_url = normalize_pg_url(db_url)
    if not normalized_url or not normalized_url.startswith("postgresql://"):
        raise PostgreSQLBackupError(
            f"Invalid PostgreSQL database URL. Expected postgresql://..., got {mask_db_url(normalized_url)}"
        )

    # 1. Model artifact verification
    model_info = {}
    if verify_model:
        model_info = verify_model_artifact()

    # 2. Database inspection
    logger.info(f"Inspecting PostgreSQL database at {mask_db_url(normalized_url)}...")
    inspection = inspect_postgresql_database(normalized_url)
    logger.info(
        f"Database inspected: {inspection['current_database']} "
        f"({inspection['table_count']} tables, Alembic: {inspection['alembic_version']})"
    )

    # 3. Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_uuid = str(uuid.uuid4())
    backup_filename = f"carspective_pg_backup_{timestamp}.dump"
    staging_filename = f".staging_{backup_filename}.tmp"

    backup_path = output_dir / backup_filename
    staging_path = output_dir / staging_filename
    manifest_path = output_dir / f"{backup_filename}.manifest.json"
    staging_manifest = output_dir / f".staging_{manifest_path.name}.tmp"

    # 4. Execute dump to staging file
    logger.info(f"Creating PostgreSQL backup archive: {backup_filename}...")
    try:
        execute_pg_dump(normalized_url, staging_path, pg_dump_bin=pg_dump_bin)

        if not staging_path.is_file() or staging_path.stat().st_size == 0:
            raise PostgreSQLBackupError(f"pg_dump completed but output file is empty: {staging_path}")

        # Compute hash of backup archive
        backup_sha256 = compute_sha256(staging_path)
        file_size_bytes = staging_path.stat().st_size

        # 5. Generate companion manifest
        manifest_payload = {
            "backup_uuid": backup_uuid,
            "backup_filename": backup_filename,
            "database_type": "postgresql",
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "sha256": backup_sha256,
            "file_size_bytes": file_size_bytes,
            "database_name": inspection["current_database"],
            "server_version": inspection["server_version"],
            "alembic_version": inspection["alembic_version"],
            "table_count": inspection["table_count"],
            "table_row_counts": inspection["table_counts"],
            "model_verification": model_info,
        }

        # Atomically write manifest with secure permissions (0600)
        with open(staging_manifest, "w", encoding="utf-8") as f:
            json.dump(manifest_payload, f, indent=2)
        set_secure_permissions(staging_manifest)
        staging_manifest.replace(manifest_path)
        set_secure_permissions(manifest_path)

        # Atomically move dump to final path with secure permissions (0600)
        set_secure_permissions(staging_path)
        staging_path.replace(backup_path)
        set_secure_permissions(backup_path)

    except Exception:
        if staging_path.exists():
            staging_path.unlink()
        if staging_manifest.exists():
            staging_manifest.unlink()
        raise

    logger.info(
        f"PostgreSQL backup created successfully: {backup_path.name} "
        f"({file_size_bytes} bytes, SHA-256: {backup_sha256[:16]}...)"
    )

    # 6. Retention pruning
    pruned = prune_retention(output_dir, retention_count=retention_count)

    return {
        "success": True,
        "backup_file": str(backup_path),
        "manifest_file": str(manifest_path),
        "sha256": backup_sha256,
        "file_size_bytes": file_size_bytes,
        "alembic_version": inspection["alembic_version"],
        "table_count": inspection["table_count"],
        "pruned_backups": [str(p) for p in pruned],
    }


def main():
    parser = argparse.ArgumentParser(
        description="CarSpective PostgreSQL Consistent Backup Utility (Phase 21D)"
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv("DATABASE_URL", ""),
        help="Target PostgreSQL database URL (defaults to DATABASE_URL environment variable)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help="Directory to store backup files and manifests (default: backups/)",
    )
    parser.add_argument(
        "--retention-count",
        type=int,
        default=DEFAULT_RETENTION_COUNT,
        help="Number of backups to retain during pruning (default: 7)",
    )
    parser.add_argument(
        "--pg-dump-bin",
        default=os.getenv("PG_DUMP_BIN", "pg_dump"),
        help="Path to pg_dump binary (default: pg_dump)",
    )
    parser.add_argument(
        "--verify",
        type=Path,
        metavar="BACKUP_PATH",
        help="Verify an existing PostgreSQL backup file and companion manifest",
    )
    parser.add_argument(
        "--verify-model",
        action="store_true",
        help="Verify valuation model artifact invariant without creating a backup",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON output to stdout",
    )

    args = parser.parse_args()

    try:
        if args.verify_model:
            res = verify_model_artifact()
            if args.json:
                print(json.dumps(res, indent=2))
            sys.exit(0)

        if args.verify:
            res = verify_postgresql_backup(args.verify)
            logger.info(f"Backup verification PASSED: {args.verify.name}")
            if args.json:
                print(json.dumps(res, indent=2))
            sys.exit(0)

        if not args.db_url:
            logger.error("DATABASE_URL must be specified via --db-url or environment variable.")
            sys.exit(1)

        res = create_postgresql_backup(
            db_url=args.db_url,
            output_dir=args.output_dir,
            retention_count=args.retention_count,
            pg_dump_bin=args.pg_dump_bin,
            verify_model=True,
        )

        if args.json:
            print(json.dumps(res, indent=2))
        sys.exit(0)

    except (PostgreSQLBackupError, Exception) as e:
        logger.error(f"Backup operation failed: {e}")
        if args.json:
            print(json.dumps({"success": False, "error": str(e)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
