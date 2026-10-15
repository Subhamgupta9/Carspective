"""
CARspective — Data Quality Assessment Engine
Computes multi-dimensional data quality scores across completeness, validity,
uniqueness, canonical mapping coverage, freshness, provenance, and consistency.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .models import (
    DataQualityReport,
    DataQualityStatus,
    MappingOutcome,
    FreshnessState,
)
from .validation import IngestionValidationEngine
from .freshness import FreshnessEngine

class DataQualityEngine:
    """Deterministic data quality scoring engine."""

    @classmethod
    def evaluate_records(
        cls,
        records: List[Dict[str, Any]],
        mapping_outcomes: Optional[List[MappingOutcome]] = None,
        source_id: Optional[str] = None,
        policy_id: Optional[str] = None
    ) -> DataQualityReport:
        total = len(records)
        if total == 0:
            return DataQualityReport(
                completeness_score=0.0,
                validity_score=0.0,
                uniqueness_score=0.0,
                canonical_mapping_coverage=0.0,
                freshness_score=0.0,
                provenance_coverage=0.0,
                consistency_score=0.0,
                overall_quality_score=0.0,
                status=DataQualityStatus.POOR,
                total_records=0,
                invalid_records=0,
                duplicate_records=0,
                unmapped_records=0,
                timestamp=datetime.now(timezone.utc).isoformat()
            )

        # 1. Completeness Evaluation
        fields_to_check = ["make", "model", "year", "price", "mileage", "fuel_type", "transmission"]
        total_field_checks = total * len(fields_to_check)
        filled_fields = 0
        for r in records:
            for f in fields_to_check:
                val = r.get(f)
                if val is not None and str(val).strip() != "":
                    filled_fields += 1
        completeness = filled_fields / total_field_checks if total_field_checks > 0 else 0.0

        # 2. Validity Evaluation
        invalid_count = 0
        for idx, r in enumerate(records):
            failures = IngestionValidationEngine.validate_record(r, record_index=idx)
            if failures:
                invalid_count += 1
        validity = (total - invalid_count) / total

        # 3. Uniqueness (Duplicate detection by payload signature)
        seen_signatures = set()
        duplicate_count = 0
        for r in records:
            sig = f"{r.get('make')}::{r.get('model')}::{r.get('year')}::{r.get('variant')}::{r.get('price')}::{r.get('mileage')}"
            if sig in seen_signatures:
                duplicate_count += 1
            else:
                seen_signatures.add(sig)
        uniqueness = (total - duplicate_count) / total

        # 4. Canonical Mapping Coverage
        unmapped_count = 0
        if mapping_outcomes:
            mapped_count = sum(1 for m in mapping_outcomes if m in (MappingOutcome.EXACT_MATCH, MappingOutcome.SAFE_ALIAS_MATCH))
            unmapped_count = total - mapped_count
            mapping_coverage = mapped_count / total
        else:
            mapping_coverage = 1.0

        # 5. Freshness Evaluation
        fresh_count = 0
        eff_policy = policy_id or "POLICY_OEM_SPECIFICATIONS"
        for r in records:
            obs_date = r.get("observed_date") or r.get("listing_date") or r.get("retrieved_at") or r.get("published_at")
            f_eval = FreshnessEngine.evaluate(obs_date, policy_id=eff_policy)
            if f_eval.status in (FreshnessState.CURRENT, FreshnessState.REVIEW_DUE):
                fresh_count += 1
        freshness = fresh_count / total

        # 6. Provenance Coverage
        prov_count = sum(1 for r in records if r.get("source_id") or source_id)
        provenance = prov_count / total

        # 7. Internal Consistency Evaluation (e.g. Electric with Fuel Tank or Diesel with EV battery)
        inconsistent_count = 0
        for r in records:
            fuel = str(r.get("fuel_type", "")).upper()
            trans = str(r.get("transmission", "")).upper()
            if fuel == "ELECTRIC" and r.get("fuel_tank_capacity_l") and float(r.get("fuel_tank_capacity_l", 0)) > 0:
                inconsistent_count += 1
            elif r.get("year") and r.get("registration_year") and int(r.get("registration_year", 0)) < int(r.get("year", 0)):
                inconsistent_count += 1
        consistency = (total - inconsistent_count) / total

        # Overall composite Data Quality Score
        # 0.20 completeness + 0.25 validity + 0.15 uniqueness + 0.15 mapping + 0.10 freshness + 0.10 provenance + 0.05 consistency
        overall = (
            0.20 * completeness +
            0.25 * validity +
            0.15 * uniqueness +
            0.15 * mapping_coverage +
            0.10 * freshness +
            0.10 * provenance +
            0.05 * consistency
        )
        overall = round(max(0.0, min(1.0, overall)), 4)

        if overall >= 0.90:
            status = DataQualityStatus.EXCELLENT
        elif overall >= 0.75:
            status = DataQualityStatus.GOOD
        elif overall >= 0.60:
            status = DataQualityStatus.MARGINAL
        else:
            status = DataQualityStatus.POOR

        return DataQualityReport(
            completeness_score=round(completeness, 4),
            validity_score=round(validity, 4),
            uniqueness_score=round(uniqueness, 4),
            canonical_mapping_coverage=round(mapping_coverage, 4),
            freshness_score=round(freshness, 4),
            provenance_coverage=round(provenance, 4),
            consistency_score=round(consistency, 4),
            overall_quality_score=overall,
            status=status,
            total_records=total,
            invalid_records=invalid_count,
            duplicate_records=duplicate_count,
            unmapped_records=unmapped_count,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
