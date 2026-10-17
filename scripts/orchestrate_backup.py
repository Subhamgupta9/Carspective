#!/usr/bin/env python3
"""
CARspective — Phase 23B: PostgreSQL Backup Orchestration & Off-Site Replication Tooling

Orchestrates consistent PostgreSQL logical backups with companion cryptographic manifests,
verified encrypted off-site replication (S3-compatible object storage), concurrency locking,
deterministic retention synchronization, and verified disaster recovery retrieval.

Safety Invariants:
- Reuses verified backup & verification engines in scripts/backup_postgresql.py.
- Cross-platform process locking prevents overlapping execution and corruption.
- Verifies local backup & manifest integrity BEFORE attempting replication.
- Enforces Server-Side Encryption (SSE-S3 AES256 or SSE-KMS) on all remote objects.
- Verifies remote object existence, byte size, and metadata SHA-256 POST-upload.
- Never deletes the only verified local copy before the off-site copy is confirmed.
- Fails closed on any step failure with non-zero exit code and structured JSON diagnostics.
- Masks all credentials, access keys, secrets, and database URLs in logs and outputs.
- Never falls back silently to local storage when off-site replication is requested.
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import re
import sys
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is on sys.path for direct CLI script execution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from scripts.backup_postgresql import (
        PostgreSQLBackupError,
        compute_sha256,
        create_postgresql_backup,
        is_protected_path,
        mask_db_url,
        set_secure_permissions,
        verify_model_artifact,
        verify_postgresql_backup,
    )
except ModuleNotFoundError as _import_err:
    if _import_err.name in ("scripts", "scripts.backup_postgresql"):
        from backup_postgresql import (
            PostgreSQLBackupError,
            compute_sha256,
            create_postgresql_backup,
            is_protected_path,
            mask_db_url,
            set_secure_permissions,
            verify_model_artifact,
            verify_postgresql_backup,
        )
    else:
        raise


# ==============================================================================
# LOGGING & CREDENTIAL REDACTION
# ==============================================================================

REDACTION_PATTERNS = [
    (re.compile(r"(://[^:]+:)([^@]+)(@)"), r"\1*****\3"),  # DB URLs with password
    (re.compile(r"(AKIA[0-9A-Z]{16})"), r"AKIA****************"),  # AWS Access Key IDs
    (re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]{8,}", re.IGNORECASE), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"(aws_secret_access_key\s*=\s*)[^\s]+", re.IGNORECASE), r"\1[REDACTED_SECRET]"),
    (re.compile(r"(password\s*[:=]\s*)[^\s,;]+", re.IGNORECASE), r"\1[REDACTED_PASSWORD]"),
]


def redact_sensitive_string(text: Any) -> Any:
    """Redacts passwords, tokens, access keys, and credentials from a text string or object representation."""
    if not isinstance(text, str):
        return text
    result = text
    for pattern, repl in REDACTION_PATTERNS:
        result = pattern.sub(repl, result)
    return result


class SensitiveFilter(logging.Filter):
    """
    Redacts passwords, tokens, access keys, and credentials from log messages,
    including format argument tuples and mappings.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_string(record.msg)
        if record.args:
            if isinstance(record.args, tuple):
                record.args = tuple(
                    redact_sensitive_string(a) if isinstance(a, str) else a
                    for a in record.args
                )
            elif isinstance(record.args, dict):
                record.args = {
                    k: redact_sensitive_string(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
        return True


logger = logging.getLogger("carspective.orchestrate_backup")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    _handler.addFilter(SensitiveFilter())
    logger.addHandler(_handler)


# ==============================================================================
# EXCEPTIONS
# ==============================================================================

class BackupOrchestrationError(Exception):
    """Raised when backup orchestration or local verification fails."""
    pass


class StorageError(Exception):
    """Raised when remote off-site storage or replication fails."""
    pass


class LockError(Exception):
    """Raised when another backup orchestration process is actively executing."""
    pass


# ==============================================================================
# PROCESS CONCURRENCY LOCKING
# ==============================================================================

class ProcessLock:
    """
    Cross-platform process lock using atomic file creation and PID tracking.
    Prevents overlapping cron/timer executions from corrupting retention or active files.
    """

    def __init__(self, lock_path: Path, timeout_seconds: float = 0.0):
        self.lock_path = lock_path.resolve()
        self.timeout_seconds = timeout_seconds
        self._acquired = False

    def acquire(self) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        start_time = time.time()

        while True:
            try:
                # Open with O_CREAT | O_EXCL for atomic creation
                fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                with os.fdopen(fd, "w") as f:
                    f.write(json.dumps({
                        "pid": os.getpid(),
                        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        "acquired_by": "carspective.orchestrate_backup",
                    }))
                self._acquired = True
                logger.debug(f"Acquired process lock: {self.lock_path}")
                return
            except FileExistsError:
                # Lock file exists: check if process is stale
                if self._is_stale():
                    logger.warning(f"Reclaiming stale lock file from inactive PID: {self.lock_path}")
                    self._release_file()
                    continue

                if self.timeout_seconds <= 0 or (time.time() - start_time) >= self.timeout_seconds:
                    raise LockError(
                        f"Another backup orchestration job is currently running (lock active: {self.lock_path}). "
                        f"Aborting to prevent concurrent storage mutation."
                    )
                time.sleep(0.5)

    def _is_stale(self) -> bool:
        try:
            if not self.lock_path.exists():
                return True

            # Guard against mid-write race condition: check file age
            try:
                st = self.lock_path.stat()
                if (time.time() - st.st_mtime) < 1.0 and st.st_size == 0:
                    return False
            except OSError:
                pass

            with open(self.lock_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return True
                data = json.loads(content)

            pid = data.get("pid")
            if not pid or not isinstance(pid, int) or pid <= 0:
                return True

            # Check if PID is still alive
            if sys.platform == "win32":
                import ctypes
                kernel32 = ctypes.windll.kernel32
                handle = kernel32.OpenProcess(1024, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
                if handle == 0:
                    err = kernel32.GetLastError()
                    if err == 5:  # ERROR_ACCESS_DENIED: process exists but cannot query
                        return False
                    return True  # Process does not exist (e.g. ERROR_INVALID_PARAMETER 87)
                kernel32.CloseHandle(handle)
                return False
            else:
                try:
                    os.kill(pid, 0)
                    return False  # Signal 0 succeeded: process is alive
                except ProcessLookupError:
                    return True   # ESRCH: process does not exist -> lock is stale!
                except PermissionError:
                    return False  # EPERM: process exists (different user) -> lock is active!
        except Exception:
            return True

    def _release_file(self) -> None:
        try:
            if self.lock_path.exists():
                self.lock_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to remove lock file {self.lock_path}: {e}")

    def release(self) -> None:
        if self._acquired:
            self._release_file()
            self._acquired = False
            logger.debug(f"Released process lock: {self.lock_path}")

    def __enter__(self) -> "ProcessLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()


# ==============================================================================
# OBJECT STORAGE ADAPTER INTERFACE & IMPLEMENTATIONS
# ==============================================================================

class ObjectStorageAdapter(ABC):
    """Abstract interface for off-site backup replication storage providers."""

    @abstractmethod
    def upload_file(
        self,
        local_path: Path,
        remote_key: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Uploads a local file to remote object storage with encryption and metadata."""
        pass

    @abstractmethod
    def verify_object(
        self,
        remote_key: str,
        expected_size: int,
        expected_sha256: Optional[str] = None,
        expected_sse: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Verifies existence, byte size, encryption, and checksum metadata of a remote object."""
        pass

    @abstractmethod
    def download_file(self, remote_key: str, local_path: Path) -> Path:
        """Downloads a remote object to a local filesystem destination."""
        pass

    @abstractmethod
    def list_backups(self, prefix: str) -> List[Dict[str, Any]]:
        """Lists candidate backup objects matching the given prefix, sorted newest first."""
        pass

    @abstractmethod
    def delete_object(self, remote_key: str) -> bool:
        """Deletes a remote object. Fails closed on unauthorized deletion."""
        pass


class S3StorageAdapter(ObjectStorageAdapter):
    """
    Amazon S3 and S3-compatible (MinIO, Cloudflare R2, Ceph) object storage adapter.
    Enforces Server-Side Encryption (SSE-S3 or SSE-KMS) and SHA-256 metadata verification.
    """

    def __init__(
        self,
        bucket_name: str,
        region_name: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        sse_algorithm: str = "AES256",
        kms_key_id: Optional[str] = None,
        client: Optional[Any] = None,
    ):
        if not bucket_name or not bucket_name.strip():
            raise StorageError("S3 bucket name must be specified and non-empty.")

        self.bucket_name = bucket_name.strip()
        self.region_name = (region_name or "us-east-1").strip()
        self.endpoint_url = endpoint_url.strip() if endpoint_url else None
        self.sse_algorithm = (sse_algorithm or "AES256").strip()
        self.kms_key_id = kms_key_id.strip() if kms_key_id else None

        if client is not None:
            self._client = client
        else:
            try:
                import boto3
                from botocore.config import Config
            except ImportError as e:
                raise StorageError(
                    "boto3 package is required for S3 off-site replication. "
                    "Install via: pip install boto3"
                ) from e

            cfg = Config(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            )
            client_kwargs: Dict[str, Any] = {
                "region_name": self.region_name,
                "config": cfg,
            }
            if self.endpoint_url:
                client_kwargs["endpoint_url"] = self.endpoint_url

            self._client = boto3.client("s3", **client_kwargs)

    def upload_file(
        self,
        local_path: Path,
        remote_key: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if not local_path.is_file():
            raise StorageError(f"Local file not found for S3 upload: {local_path}")

        file_size = local_path.stat().st_size
        extra_args: Dict[str, Any] = {
            "ContentType": content_type,
            "ServerSideEncryption": self.sse_algorithm,
        }
        if self.sse_algorithm == "aws:kms" and self.kms_key_id:
            extra_args["SSEKMSKeyId"] = self.kms_key_id
        if metadata:
            extra_args["Metadata"] = {k.lower(): str(v) for k, v in metadata.items()}

        logger.info(f"Uploading {local_path.name} to s3://{self.bucket_name}/{remote_key} (SSE: {self.sse_algorithm})...")
        try:
            with open(local_path, "rb") as f:
                self._client.put_object(
                    Bucket=self.bucket_name,
                    Key=remote_key,
                    Body=f,
                    **extra_args,
                )
            return {
                "bucket": self.bucket_name,
                "key": remote_key,
                "size_bytes": file_size,
                "server_side_encryption": self.sse_algorithm,
            }
        except Exception as e:
            raise StorageError(f"Failed to upload {local_path.name} to S3 ({remote_key}): {e}") from e

    def verify_object(
        self,
        remote_key: str,
        expected_size: int,
        expected_sha256: Optional[str] = None,
        expected_sse: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info(f"Verifying remote S3 object: s3://{self.bucket_name}/{remote_key}...")
        try:
            resp = self._client.head_object(Bucket=self.bucket_name, Key=remote_key)
        except Exception as e:
            raise StorageError(f"Failed to retrieve metadata for remote S3 object {remote_key}: {e}") from e

        actual_size = resp.get("ContentLength")
        if actual_size != expected_size:
            raise StorageError(
                f"Remote S3 object size mismatch for {remote_key}! Expected {expected_size} bytes, got {actual_size}"
            )

        actual_sse = resp.get("ServerSideEncryption")
        req_sse = expected_sse or self.sse_algorithm
        if req_sse and actual_sse != req_sse:
            raise StorageError(
                f"Remote S3 encryption mismatch for {remote_key}! Expected {req_sse}, got {actual_sse}"
            )

        meta = resp.get("Metadata", {})
        remote_sha = meta.get("sha256")
        if expected_sha256:
            if not remote_sha or remote_sha.lower() != expected_sha256.lower():
                raise StorageError(
                    f"Remote S3 SHA-256 metadata mismatch for {remote_key}! Expected {expected_sha256}, got {remote_sha}"
                )

        # Diagnostic inspection of S3 Object Lock metadata (if configured on bucket).
        # Note: The application does NOT enforce or configure bucket-level WORM immutability;
        # Object Lock policies must be configured at the cloud bucket level.
        lock_mode = resp.get("ObjectLockMode")
        retain_until = resp.get("ObjectLockRetainUntilDate")

        logger.info(
            f"Remote S3 object verified: s3://{self.bucket_name}/{remote_key} "
            f"({actual_size} bytes, SSE: {actual_sse})"
        )
        return {
            "verified": True,
            "bucket": self.bucket_name,
            "key": remote_key,
            "size_bytes": actual_size,
            "server_side_encryption": actual_sse,
            "etag": (resp.get("ETag") or "").strip('"'),
            "metadata_sha256": remote_sha,
            "object_lock_mode": lock_mode,
            "object_lock_retain_until": str(retain_until) if retain_until else None,
        }

    def download_file(self, remote_key: str, local_path: Path) -> Path:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        staging_path = local_path.parent / f".staging_dl_{local_path.name}.tmp"
        logger.info(f"Downloading s3://{self.bucket_name}/{remote_key} to {local_path}...")
        try:
            with open(staging_path, "wb") as f:
                self._client.download_fileobj(self.bucket_name, remote_key, f)
            set_secure_permissions(staging_path)
            staging_path.replace(local_path)
            set_secure_permissions(local_path)
            return local_path
        except Exception as e:
            if staging_path.exists():
                staging_path.unlink()
            raise StorageError(f"Failed to download remote S3 object {remote_key}: {e}") from e

    def list_backups(self, prefix: str) -> List[Dict[str, Any]]:
        clean_prefix = prefix.lstrip("/")
        try:
            paginator = self._client.get_paginator("list_objects_v2")
            results = []
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=clean_prefix):
                for item in page.get("Contents", []):
                    key = item.get("Key", "")
                    if key.endswith(".dump"):
                        results.append({
                            "key": key,
                            "size": item.get("Size"),
                            "last_modified": item.get("LastModified"),
                            "etag": (item.get("ETag") or "").strip('"'),
                        })
            results.sort(key=lambda x: str(x["key"]), reverse=True)
            return results
        except Exception as e:
            raise StorageError(f"Failed to list remote backups in s3://{self.bucket_name}/{clean_prefix}: {e}") from e

    def delete_object(self, remote_key: str) -> bool:
        logger.info(f"Deleting remote S3 object: s3://{self.bucket_name}/{remote_key}")
        try:
            self._client.delete_object(Bucket=self.bucket_name, Key=remote_key)
            return True
        except Exception as e:
            raise StorageError(f"Failed to delete remote S3 object {remote_key}: {e}") from e


class DryRunStorageAdapter(ObjectStorageAdapter):
    """
    Simulates off-site object storage for dry-run validation and environments
    where cloud infrastructure has not yet been provisioned.
    """

    def __init__(self, bucket_name: str = "carspective-dryrun-bucket", sse_algorithm: str = "AES256"):
        self.bucket_name = bucket_name
        self.sse_algorithm = sse_algorithm
        self.simulated_objects: Dict[str, Dict[str, Any]] = {}

    def upload_file(
        self,
        local_path: Path,
        remote_key: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if not local_path.is_file():
            raise StorageError(f"Local file not found for upload: {local_path}")
        size = local_path.stat().st_size
        self.simulated_objects[remote_key] = {
            "size": size,
            "metadata": metadata or {},
            "sse": self.sse_algorithm,
        }
        logger.info(f"[DRY-RUN] Simulated upload: s3://{self.bucket_name}/{remote_key} ({size} bytes)")
        return {
            "bucket": self.bucket_name,
            "key": remote_key,
            "size_bytes": size,
            "server_side_encryption": self.sse_algorithm,
            "dry_run": True,
        }

    def verify_object(
        self,
        remote_key: str,
        expected_size: int,
        expected_sha256: Optional[str] = None,
        expected_sse: Optional[str] = None,
    ) -> Dict[str, Any]:
        obj = self.simulated_objects.get(remote_key)
        if not obj:
            raise StorageError(f"[DRY-RUN] Remote object missing in dry-run store: {remote_key}")
        if obj["size"] != expected_size:
            raise StorageError(f"[DRY-RUN] Size mismatch: expected {expected_size}, got {obj['size']}")
        logger.info(f"[DRY-RUN] Verified object: s3://{self.bucket_name}/{remote_key}")
        return {
            "verified": True,
            "bucket": self.bucket_name,
            "key": remote_key,
            "size_bytes": obj["size"],
            "server_side_encryption": self.sse_algorithm,
            "dry_run": True,
        }

    def download_file(self, remote_key: str, local_path: Path) -> Path:
        raise NotImplementedError("Download is not supported in dry-run adapter mode.")

    def list_backups(self, prefix: str) -> List[Dict[str, Any]]:
        clean_prefix = prefix.lstrip("/")
        matches = [
            {"key": k, "size": v["size"]}
            for k, v in self.simulated_objects.items()
            if k.startswith(clean_prefix) and k.endswith(".dump")
        ]
        matches.sort(key=lambda x: str(x["key"]), reverse=True)
        return matches

    def delete_object(self, remote_key: str) -> bool:
        return self.simulated_objects.pop(remote_key, None) is not None


# ==============================================================================
# ORCHESTRATION ENGINE
# ==============================================================================

def orchestrate_backup(
    db_url: str,
    staging_dir: Path,
    retention_count: int = 7,
    storage_adapter: Optional[ObjectStorageAdapter] = None,
    s3_prefix: str = "carspective-backups/",
    remote_retention_count: Optional[int] = None,
    lock_file: Optional[Path] = None,
    dry_run: bool = False,
    pg_dump_bin: str = "pg_dump",
    fail_on_lock: bool = False,
) -> Dict[str, Any]:
    """
    Executes an end-to-end backup orchestration cycle:
    1. Acquires exclusive process lock to prevent concurrent runs.
    2. Runs PostgreSQL backup utility into local staging directory.
    3. Re-verifies local backup archive & companion manifest integrity.
    4. Replicates dump and manifest to encrypted off-site object storage.
    5. Performs post-upload remote existence, size, and metadata verification.
    6. Synchronizes remote retention without deleting active/latest backups.
    7. Fails closed with structured diagnostics on any step error.
    """
    staging_dir = staging_dir.resolve()
    staging_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_file.resolve() if lock_file else (staging_dir / ".orchestrate_backup.lock")

    logger.info("Initiating CarSpective backup orchestration cycle...")
    masked_url = mask_db_url(db_url)
    logger.info(f"Target Database: {masked_url}")
    logger.info(f"Staging Directory: {staging_dir}")
    logger.info(f"Local Retention: {retention_count} backups")

    lock = ProcessLock(lock_path)
    try:
        lock.acquire()
    except LockError as le:
        if fail_on_lock:
            raise
        logger.warning(
            f"Another backup orchestration job is currently running (lock: {lock_path}). "
            "Skipping this scheduled execution to avoid concurrent storage mutation."
        )
        return {
            "success": True,
            "skipped": True,
            "reason": "lock_active",
            "message": f"Backup execution skipped: lock active at {lock_path}",
            "lock_file": str(lock_path),
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    try:
        # 1. Execute local PostgreSQL backup
        try:
            local_result = create_postgresql_backup(
                db_url=db_url,
                output_dir=staging_dir,
                retention_count=retention_count,
                pg_dump_bin=pg_dump_bin,
                verify_model=True,
            )
        except Exception as e:
            raise BackupOrchestrationError(f"Local PostgreSQL backup creation failed: {e}") from e

        backup_file = Path(local_result["backup_file"])
        manifest_file = Path(local_result["manifest_file"])
        backup_sha256 = local_result["sha256"]
        file_size_bytes = local_result["file_size_bytes"]
        alembic_version = local_result["alembic_version"]
        table_count = local_result["table_count"]

        # 2. Re-verify local backup & manifest integrity before attempting off-site upload
        try:
            verified_info = verify_postgresql_backup(backup_file)
            if not verified_info.get("verified"):
                raise BackupOrchestrationError(f"Pre-replication local verification failed for {backup_file.name}")
        except Exception as e:
            raise BackupOrchestrationError(f"Pre-replication integrity audit rejected backup: {e}") from e

        # 3. Handle off-site replication
        replication_result: Optional[Dict[str, Any]] = None

        if storage_adapter is not None:
            clean_prefix = s3_prefix.strip("/")
            remote_dump_key = f"{clean_prefix}/{backup_file.name}" if clean_prefix else backup_file.name
            remote_manifest_key = f"{clean_prefix}/{manifest_file.name}" if clean_prefix else manifest_file.name

            metadata = {
                "sha256": backup_sha256,
                "alembic-version": alembic_version,
                "table-count": str(table_count),
                "created-at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }

            try:
                # Upload dump archive
                dump_upload = storage_adapter.upload_file(
                    local_path=backup_file,
                    remote_key=remote_dump_key,
                    content_type="application/octet-stream",
                    metadata=metadata,
                )

                # Upload companion manifest
                manifest_upload = storage_adapter.upload_file(
                    local_path=manifest_file,
                    remote_key=remote_manifest_key,
                    content_type="application/json",
                    metadata=metadata,
                )

                # Post-upload remote verification
                dump_verify = storage_adapter.verify_object(
                    remote_key=remote_dump_key,
                    expected_size=file_size_bytes,
                    expected_sha256=backup_sha256,
                )
                manifest_verify = storage_adapter.verify_object(
                    remote_key=remote_manifest_key,
                    expected_size=manifest_file.stat().st_size,
                )

                # Remote retention pruning (if requested and supported)
                pruned_remote = []
                if remote_retention_count and remote_retention_count > 0:
                    try:
                        remote_backups = storage_adapter.list_backups(prefix=clean_prefix)
                        # Filter to only backups in current namespace
                        candidates = [
                            b for b in remote_backups
                            if b["key"] != remote_dump_key and not is_protected_path(Path(b["key"]))
                        ]
                        if len(candidates) >= remote_retention_count:
                            to_prune = candidates[remote_retention_count - 1:]
                            for b in to_prune:
                                k = b["key"]
                                storage_adapter.delete_object(k)
                                # Delete companion manifest if exists
                                try:
                                    storage_adapter.delete_object(f"{k}.manifest.json")
                                except Exception:
                                    pass
                                pruned_remote.append(k)
                                logger.info(f"Pruned older remote backup: {k}")
                    except Exception as pe:
                        logger.warning(f"Remote retention pruning encountered error (non-fatal): {pe}")

                replication_result = {
                    "replicated": True,
                    "storage_provider": storage_adapter.__class__.__name__,
                    "remote_dump_key": remote_dump_key,
                    "remote_manifest_key": remote_manifest_key,
                    "server_side_encryption": dump_verify.get("server_side_encryption"),
                    "etag": dump_verify.get("etag"),
                    "object_lock_mode": dump_verify.get("object_lock_mode"),
                    "object_lock_retain_until": dump_verify.get("object_lock_retain_until"),
                    "pruned_remote": pruned_remote,
                }
            except Exception as e:
                # Fails closed on replication error; local backup remains preserved for forensic recovery
                raise StorageError(
                    f"Off-site backup replication failed for {backup_file.name}: {e}. "
                    f"Local backup remains preserved at {backup_file}."
                ) from e
        else:
            logger.info("No off-site storage adapter configured; local backup cycle completed.")

        final_summary = {
            "success": True,
            "skipped": False,
            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "local_backup": local_result,
            "replication": replication_result,
            "dry_run": dry_run,
        }
        logger.info(
            f"Backup orchestration COMPLETED successfully: {backup_file.name} "
            f"({file_size_bytes} bytes, Replicated: {bool(replication_result)})"
        )
        return final_summary
    finally:
        lock.release()


def verify_remote_backup(
    storage_adapter: ObjectStorageAdapter,
    remote_dump_key: str,
    expected_size: Optional[int] = None,
    expected_sha256: Optional[str] = None,
) -> Dict[str, Any]:
    """Inspects and validates an existing remote backup object on off-site storage."""
    remote_manifest_key = f"{remote_dump_key}.manifest.json"

    # 1. Download manifest to temporary staging location
    import tempfile
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_manifest = Path(tmp_dir) / "manifest.json"
        storage_adapter.download_file(remote_manifest_key, tmp_manifest)
        with open(tmp_manifest, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        exp_size = expected_size or manifest_data.get("file_size_bytes")
        exp_sha = expected_sha256 or manifest_data.get("sha256")

        # 2. Verify dump object against manifest
        verify_data = storage_adapter.verify_object(
            remote_key=remote_dump_key,
            expected_size=exp_size,
            expected_sha256=exp_sha,
        )

        return {
            "verified": True,
            "remote_key": remote_dump_key,
            "file_size_bytes": exp_size,
            "sha256": exp_sha,
            "alembic_version": manifest_data.get("alembic_version"),
            "table_count": manifest_data.get("table_count"),
            "server_side_encryption": verify_data.get("server_side_encryption"),
            "manifest_timestamp": manifest_data.get("timestamp_utc"),
        }


def retrieve_remote_backup(
    storage_adapter: ObjectStorageAdapter,
    remote_dump_key: str,
    output_dir: Path,
    verify: bool = True,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Downloads a remote backup and its companion manifest from off-site storage
    to a local directory, executing full SHA-256 and schema integrity verification.
    """
    if not remote_dump_key or not remote_dump_key.strip():
        raise StorageError("Remote dump key must be specified and non-empty.")

    clean_key = remote_dump_key.strip().replace("\\", "/")
    parts = [p for p in clean_key.split("/") if p]
    if ".." in parts or clean_key.startswith("/") or clean_key.startswith("./"):
        raise StorageError(f"Path traversal detected in remote dump key: '{remote_dump_key}' contains invalid directory navigation.")

    dump_filename = Path(clean_key).name
    if not dump_filename or dump_filename in (".", ".."):
        raise StorageError(f"Invalid remote backup key: '{remote_dump_key}' produces empty or invalid filename.")

    valid_suffixes = (".dump", ".sql", ".pgdump")
    if not any(dump_filename.endswith(sfx) for sfx in valid_suffixes):
        raise StorageError(
            f"Remote backup key must have a recognized dump suffix ({', '.join(valid_suffixes)}), got: '{dump_filename}'"
        )

    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    local_dump = (output_dir / dump_filename).resolve()
    manifest_filename = f"{dump_filename}.manifest.json"
    local_manifest = (output_dir / manifest_filename).resolve()

    # Traversal check: ensure resolved paths reside within output_dir
    try:
        local_dump.relative_to(output_dir)
        local_manifest.relative_to(output_dir)
    except ValueError:
        raise StorageError(f"Path traversal detected in remote dump key: '{remote_dump_key}' resolves outside destination directory.")

    # Protected path check
    if is_protected_path(local_dump) or is_protected_path(local_manifest):
        raise StorageError(f"Destination path is protected and cannot be targeted for retrieval: {local_dump}")

    # Overwrite check
    if not overwrite:
        if local_dump.exists():
            raise StorageError(f"Destination dump file already exists: {local_dump}. Pass overwrite=True (or --overwrite) to replace.")
        if local_manifest.exists():
            raise StorageError(f"Destination manifest file already exists: {local_manifest}. Pass overwrite=True (or --overwrite) to replace.")

    remote_parent = Path(clean_key).parent.as_posix()
    remote_manifest_key = f"{remote_parent}/{manifest_filename}".lstrip("./")

    manifest_existed_before = local_manifest.exists()
    dump_existed_before = local_dump.exists()

    logger.info(f"Retrieving off-site backup: {clean_key} -> {local_dump}")
    try:
        storage_adapter.download_file(remote_manifest_key, local_manifest)
        storage_adapter.download_file(clean_key, local_dump)

        if verify:
            logger.info(f"Verifying retrieved backup against manifest: {local_dump.name}")
            try:
                audit = verify_postgresql_backup(local_dump, local_manifest)
                if not audit.get("verified"):
                    raise StorageError(f"Retrieved backup failed cryptographic verification: {local_dump}")
            except PostgreSQLBackupError as pbe:
                raise StorageError(f"Retrieved backup failed cryptographic verification: {pbe}") from pbe
            return {
                "success": True,
                "retrieved_dump": str(local_dump),
                "retrieved_manifest": str(local_manifest),
                "sha256": audit.get("sha256"),
                "table_count": audit.get("table_count"),
                "alembic_version": audit.get("alembic_version"),
                "verified": True,
            }

        return {
            "success": True,
            "retrieved_dump": str(local_dump),
            "retrieved_manifest": str(local_manifest),
            "verified": False,
        }
    except Exception as e:
        # Clean up newly created partial/corrupt files on failure without deleting pre-existing files
        if not manifest_existed_before and local_manifest.exists():
            try:
                local_manifest.unlink()
            except OSError:
                pass
        if not dump_existed_before and local_dump.exists():
            try:
                local_dump.unlink()
            except OSError:
                pass
        raise


# ==============================================================================
# CLI INTERFACE
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="CarSpective PostgreSQL Backup Orchestration & Off-Site Replication Tool (Phase 23B)"
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv("DATABASE_URL", ""),
        help="Target PostgreSQL database URL (defaults to DATABASE_URL environment variable)",
    )
    parser.add_argument(
        "--staging-dir",
        type=Path,
        default=Path(os.getenv("BACKUP_STAGING_DIR", "backups")),
        help="Local staging directory for temporary archives and retention pool (default: backups)",
    )
    parser.add_argument(
        "--retention-count",
        type=int,
        default=int(os.getenv("BACKUP_RETENTION_COUNT", "7")),
        help="Number of local backups to retain (default: 7)",
    )
    parser.add_argument(
        "--storage-type",
        choices=["s3", "dry-run", "none"],
        default=os.getenv("BACKUP_STORAGE_TYPE", "none"),
        help="Off-site replication storage provider (s3, dry-run, or none; default: none)",
    )
    parser.add_argument(
        "--s3-bucket",
        default=os.getenv("AWS_S3_BUCKET", ""),
        help="Target Amazon S3 / S3-compatible bucket name",
    )
    parser.add_argument(
        "--s3-prefix",
        default=os.getenv("AWS_S3_PREFIX", "carspective-backups/"),
        help="Destination key prefix in target storage bucket (default: carspective-backups/)",
    )
    parser.add_argument(
        "--s3-region",
        default=os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1")),
        help="AWS region for S3 client (default: us-east-1)",
    )
    parser.add_argument(
        "--s3-endpoint-url",
        default=os.getenv("AWS_S3_ENDPOINT_URL", ""),
        help="Optional custom endpoint URL for S3-compatible storage (e.g. MinIO, Cloudflare R2, LocalStack)",
    )
    parser.add_argument(
        "--sse-algorithm",
        choices=["AES256", "aws:kms"],
        default=os.getenv("AWS_SSE_ALGORITHM", "AES256"),
        help="Server-side encryption algorithm (default: AES256)",
    )
    parser.add_argument(
        "--sse-kms-key-id",
        default=os.getenv("AWS_SSE_KMS_KEY_ID", ""),
        help="Optional KMS Key ID for aws:kms encryption",
    )
    parser.add_argument(
        "--remote-retention-count",
        type=int,
        default=int(os.getenv("REMOTE_RETENTION_COUNT", "0")),
        help="Number of remote backups to retain on off-site storage (default: 0 = do not prune remote)",
    )
    parser.add_argument(
        "--lock-file",
        type=Path,
        default=None,
        help="Custom path for concurrency lock file (default: <staging-dir>/.orchestrate_backup.lock)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform backup and simulate replication without executing actual network uploads",
    )
    parser.add_argument(
        "--verify-remote",
        metavar="REMOTE_KEY",
        help="Inspect and verify an existing remote backup object on off-site storage",
    )
    parser.add_argument(
        "--retrieve",
        metavar="REMOTE_KEY",
        help="Download and cryptographically verify a remote backup from off-site storage",
    )
    parser.add_argument(
        "--retrieve-dir",
        type=Path,
        default=Path("backups/retrieved"),
        help="Local directory destination for retrieved backups (default: backups/retrieved)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing files in retrieval destination directory",
    )
    parser.add_argument(
        "--fail-on-lock",
        action="store_true",
        help="Fail with exit code 1 if another backup is actively running (default: skip cleanly with exit code 0)",
    )
    parser.add_argument(
        "--pg-dump-bin",
        default=os.getenv("PG_DUMP_BIN", "pg_dump"),
        help="Path to pg_dump binary (default: pg_dump)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON output to stdout",
    )

    args = parser.parse_args()

    # Determine storage adapter
    adapter: Optional[ObjectStorageAdapter] = None
    if args.dry_run or args.storage_type == "dry-run":
        adapter = DryRunStorageAdapter(
            bucket_name=args.s3_bucket or "carspective-dryrun-bucket",
            sse_algorithm=args.sse_algorithm,
        )
    elif args.storage_type == "s3" or args.verify_remote or args.retrieve:
        if not args.s3_bucket:
            logger.error("Configuration error: --s3-bucket (or AWS_S3_BUCKET) is required for S3 storage operations.")
            if args.json:
                print(json.dumps({"success": False, "error": "Missing S3 bucket configuration"}, indent=2))
            sys.exit(1)
        adapter = S3StorageAdapter(
            bucket_name=args.s3_bucket,
            region_name=args.s3_region,
            endpoint_url=args.s3_endpoint_url or None,
            sse_algorithm=args.sse_algorithm,
            kms_key_id=args.sse_kms_key_id or None,
        )

    try:
        # Mode 1: Verify remote backup
        if args.verify_remote:
            if not adapter:
                logger.error("Storage adapter required to verify remote backup.")
                sys.exit(1)
            res = verify_remote_backup(adapter, args.verify_remote)
            if args.json:
                print(json.dumps(res, indent=2))
            sys.exit(0)

        # Mode 2: Retrieve remote backup
        if args.retrieve:
            if not adapter:
                logger.error("Storage adapter required to retrieve remote backup.")
                sys.exit(1)
            res = retrieve_remote_backup(
                adapter,
                args.retrieve,
                output_dir=args.retrieve_dir,
                overwrite=args.overwrite,
            )
            if args.json:
                print(json.dumps(res, indent=2))
            sys.exit(0)

        # Mode 3: Orchestrate backup cycle
        if not args.db_url:
            logger.error("DATABASE_URL must be specified via --db-url or environment variable.")
            if args.json:
                print(json.dumps({"success": False, "error": "DATABASE_URL not specified"}, indent=2))
            sys.exit(1)

        res = orchestrate_backup(
            db_url=args.db_url,
            staging_dir=args.staging_dir,
            retention_count=args.retention_count,
            storage_adapter=adapter,
            s3_prefix=args.s3_prefix,
            remote_retention_count=args.remote_retention_count if args.remote_retention_count > 0 else None,
            lock_file=args.lock_file,
            dry_run=args.dry_run,
            pg_dump_bin=args.pg_dump_bin,
            fail_on_lock=args.fail_on_lock,
        )

        if args.json:
            print(json.dumps(res, indent=2))
        sys.exit(0)

    except LockError as le:
        logger.error(f"Backup lock contention: {le}")
        if args.json:
            sanitized_err = redact_sensitive_string(str(le))
            print(json.dumps({"success": False, "skipped": True, "error": sanitized_err}, indent=2))
        sys.exit(1)
    except (BackupOrchestrationError, StorageError, Exception) as e:
        logger.error(f"Backup orchestration failed: {e}")
        if args.json:
            sanitized_err = redact_sensitive_string(str(e))
            print(json.dumps({"success": False, "error": sanitized_err}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
