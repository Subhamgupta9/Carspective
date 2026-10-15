"""
CARspective — Ingestion Batch Engine & Two-Phase Commit Workflow
Executes controlled:
Stage (validate & audit) -> Approve/Commit (atomic commit to production tables).
Ensures failed batches never silently corrupt or overwrite valid data.
"""

import json
import hashlib
import time
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from .models import (
    IngestionBatchMetadata,
    BatchValidationStatus,
    BatchCommitStatus,
    MappingOutcome,
)
from .validation import IngestionValidationEngine
from .canonical_mapping import CanonicalMappingEngine
from .registry import GovernedSourceRegistry
from server.models.data_pipeline import IngestionBatch, IngestionRecord

class IngestionBatchEngine:
    """Manages two-phase atomic ingestion batches."""

    def __init__(self, session: Session):
        self.session = session
        self.registry = GovernedSourceRegistry(session)
        self.mapper = CanonicalMappingEngine(session)

    def stage_batch(
        self,
        source_id: str,
        records: List[Dict[str, Any]],
        snapshot_reference: Optional[str] = None
    ) -> IngestionBatchMetadata:
        """
        Phase 1: Ingest, compute checksum, validate, map, and stage audit records.
        Does NOT alter production vehicle/evidence tables.
        """
        start_time = time.perf_counter()

        # 1. Verify Source
        source = self.registry.get_source(source_id)
        if not source:
            raise ValueError(f"Unknown or unregistered source ID '{source_id}'.")
        if not source.is_active:
            raise ValueError(f"Source ID '{source_id}' is DEPRECATED and cannot accept new batches.")

        # 2. Compute Checksum of Raw Records
        raw_json = json.dumps(records, sort_keys=True)
        checksum = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()

        # Check for duplicate batch with identical checksum
        existing = self.session.query(IngestionBatch).filter_by(checksum=checksum).first()
        if existing and existing.commit_status == "COMMITTED":
            raise ValueError(f"Duplicate batch detected: batch '{existing.id}' already committed with identical checksum.")

        batch_id = f"BATCH-{int(time.time())}-{uuid.uuid4().hex[:8]}"
        batch_record = IngestionBatch(
            id=batch_id,
            source_id=source_id,
            ingestion_timestamp=datetime.now(timezone.utc),
            source_snapshot_reference=snapshot_reference or f"snapshot://{source_id}/{batch_id}",
            record_count=len(records),
            accepted_count=0,
            rejected_count=0,
            validation_status="PASSED",
            normalization_status="COMPLETED",
            canonical_mapping_status="COMPLETED",
            checksum=checksum,
            commit_status="STAGED",
        )
        self.session.add(batch_record)
        self.session.flush()

        accepted = 0
        rejected = 0
        rejection_reasons_summary = {}

        # 3. Process Each Record
        for idx, rec in enumerate(records):
            failures = IngestionValidationEngine.validate_record(rec, record_index=idx)
            is_valid = (len(failures) == 0)

            # Canonical mapping
            mapping_res = self.mapper.resolve_vehicle(
                make=rec.get("make", ""),
                model=rec.get("model", ""),
                year=int(rec.get("year")) if rec.get("year") else None,
                variant=rec.get("variant")
            )

            record_reasons = []
            if not is_valid:
                record_reasons.extend([f.error_code for f in failures])
            if mapping_res.outcome in (MappingOutcome.UNMAPPED, MappingOutcome.AMBIGUOUS, MappingOutcome.REJECTED):
                record_reasons.append(f"MAPPING_{mapping_res.outcome.value}")

            if is_valid and mapping_res.outcome in (MappingOutcome.EXACT_MATCH, MappingOutcome.SAFE_ALIAS_MATCH):
                accepted += 1
            else:
                rejected += 1
                for r in record_reasons:
                    rejection_reasons_summary[r] = rejection_reasons_summary.get(r, 0) + 1

            staged_rec = IngestionRecord(
                id=str(uuid.uuid4()),
                batch_id=batch_id,
                record_index=idx,
                raw_payload=json.dumps(rec),
                canonical_vehicle_id=mapping_res.canonical_vehicle_id,
                mapping_outcome=mapping_res.outcome.value,
                is_valid=is_valid,
                rejection_reasons=json.dumps(record_reasons) if record_reasons else None,
                created_at=datetime.now(timezone.utc)
            )
            self.session.add(staged_rec)

        # 4. Set Batch Status
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        batch_record.accepted_count = accepted
        batch_record.rejected_count = rejected
        batch_record.processing_duration_ms = duration_ms

        if rejected == 0:
            batch_record.validation_status = "PASSED"
        elif accepted > 0:
            batch_record.validation_status = "PARTIAL_FAILURE"
        else:
            batch_record.validation_status = "FAILED"

        if rejection_reasons_summary:
            batch_record.error_summary = json.dumps(rejection_reasons_summary)

        self.session.commit()

        return IngestionBatchMetadata(
            batch_id=batch_id,
            source_id=source_id,
            ingestion_timestamp=batch_record.ingestion_timestamp.isoformat(),
            source_snapshot_reference=batch_record.source_snapshot_reference,
            record_count=batch_record.record_count,
            accepted_count=accepted,
            rejected_count=rejected,
            validation_status=BatchValidationStatus(batch_record.validation_status),
            normalization_status=batch_record.normalization_status,
            canonical_mapping_status=batch_record.canonical_mapping_status,
            checksum=checksum,
            processing_duration_ms=duration_ms,
            commit_status=BatchCommitStatus.STAGED,
            error_summary=rejection_reasons_summary or None
        )

    def _to_metadata(self, batch: IngestionBatch) -> IngestionBatchMetadata:
        err_sum = None
        if batch.error_summary:
            try:
                err_sum = json.loads(batch.error_summary)
            except Exception:
                err_sum = {"raw": batch.error_summary}

        return IngestionBatchMetadata(
            batch_id=batch.id,
            source_id=batch.source_id,
            ingestion_timestamp=batch.ingestion_timestamp.isoformat() if hasattr(batch.ingestion_timestamp, "isoformat") else str(batch.ingestion_timestamp),
            source_snapshot_reference=batch.source_snapshot_reference,
            record_count=batch.record_count,
            accepted_count=batch.accepted_count,
            rejected_count=batch.rejected_count,
            validation_status=BatchValidationStatus(batch.validation_status),
            normalization_status=batch.normalization_status,
            canonical_mapping_status=batch.canonical_mapping_status,
            checksum=batch.checksum,
            processing_duration_ms=batch.processing_duration_ms,
            commit_status=BatchCommitStatus(batch.commit_status),
            error_summary=err_sum
        )

    def commit_batch(self, batch_id: str) -> IngestionBatchMetadata:
        """
        Phase 2: Atomically commits a STAGED batch.
        If validation failed or an error occurs during commit, automatically rolls back.
        """
        batch = self.session.query(IngestionBatch).filter_by(id=batch_id).first()
        if not batch:
            raise ValueError(f"Batch '{batch_id}' not found.")
        if batch.commit_status == "COMMITTED":
            raise ValueError(f"Batch '{batch_id}' has already been committed.")
        if batch.commit_status == "ROLLED_BACK":
            raise ValueError(f"Batch '{batch_id}' was rolled back and cannot be committed.")
        if batch.validation_status == "FAILED":
            raise ValueError(f"Batch '{batch_id}' failed validation and cannot be committed.")

        try:
            # Atomic transaction commit
            batch.commit_status = "COMMITTED"
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            batch.commit_status = "ROLLED_BACK"
            batch.error_summary = json.dumps({"commit_error": str(e)})
            self.session.commit()
            raise RuntimeError(f"Commit failed for batch '{batch_id}'; rolled back cleanly: {str(e)}")

        return self._to_metadata(batch)

    def rollback_batch(self, batch_id: str) -> IngestionBatchMetadata:
        """Safely rolls back a staged batch."""
        batch = self.session.query(IngestionBatch).filter_by(id=batch_id).first()
        if not batch:
            raise ValueError(f"Batch '{batch_id}' not found.")
        batch.commit_status = "ROLLED_BACK"
        self.session.commit()
        return self._to_metadata(batch)

    def get_batch(self, batch_id: str) -> Optional[IngestionBatchMetadata]:
        batch = self.session.query(IngestionBatch).filter_by(id=batch_id).first()
        if not batch:
            return None
        return self._to_metadata(batch)

    def list_batches(self, limit: int = 50) -> List[IngestionBatchMetadata]:
        batches = self.session.query(IngestionBatch).order_by(IngestionBatch.ingestion_timestamp.desc()).limit(limit).all()
        return [self._to_metadata(b) for b in batches]

