"""
CARspective — Evidence Lineage Engine
Traces end-to-end factual provenance from authoritative origin to downstream product surface:
SOURCE -> EVIDENCE -> CLAIM -> VEHICLE/CATEGORY -> PRODUCT SURFACE.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

from .models import (
    EvidenceLineageNode,
    GovernedSource,
    FreshnessEvaluation,
)
from .freshness import FreshnessEngine
from .registry import GovernedSourceRegistry
from server.models.evidence import KnowledgeClaim, ClaimEvidenceMapping, EvidenceSource
from server.models.knowledge import (
    VehicleSpecification,
    VehicleSafetyRating,
    OwnershipProfile,
    ReliabilityIssue,
)

CATEGORY_SURFACE_MAPPING = {
    "SAFETY": ["VEHICLE_WORKSPACE_SAFETY", "AI_ASSISTANT_GROUNDING", "COMPARISON_MATRIX"],
    "SPECIFICATION": ["VEHICLE_WORKSPACE_SPECS", "AI_ASSISTANT_GROUNDING", "COMPARISON_MATRIX"],
    "SPEC": ["VEHICLE_WORKSPACE_SPECS", "AI_ASSISTANT_GROUNDING", "COMPARISON_MATRIX"],
    "RELIABILITY": ["VEHICLE_WORKSPACE_RELIABILITY", "AI_ASSISTANT_GROUNDING", "INSPECTION_CHECKLIST"],
    "MAINTENANCE": ["VEHICLE_WORKSPACE_RELIABILITY", "OWNERSHIP_INTELLIGENCE"],
    "DIMENSIONS": ["VEHICLE_WORKSPACE_SPECS", "COMPARISON_MATRIX"],
}

class EvidenceLineageEngine:
    """Computes and exposes evidence lineage graphs."""

    def __init__(self, session: Session):
        self.session = session
        self.registry = GovernedSourceRegistry(session)

    def trace_claim_lineage(self, claim_id: str) -> Optional[EvidenceLineageNode]:
        """Traces the lineage of a specific knowledge claim."""
        claim = self.session.query(KnowledgeClaim).filter_by(id=claim_id).first()
        if not claim:
            return None

        # Resolve linked sources
        sources: List[GovernedSource] = []
        for mapping in claim.evidence_mappings:
            src_obj = self.registry.get_source(mapping.source_id)
            if src_obj:
                sources.append(src_obj)

        # Freshness
        primary_source = sources[0] if sources else None
        policy_id = primary_source.freshness_policy_id if primary_source else "POLICY_OEM_SPECIFICATIONS"
        obs_date = primary_source.last_seen if primary_source else (claim.valid_from.isoformat() if claim.valid_from else None)
        freshness_eval = FreshnessEngine.evaluate(
            observed_date=obs_date,
            policy_id=policy_id,
            is_deprecated=(claim.evidence_state == "DEPRECATED"),
            valid_until=claim.valid_until
        )

        category = claim.attribute_category.upper()
        surfaces = CATEGORY_SURFACE_MAPPING.get(category, ["VEHICLE_WORKSPACE", "AI_ASSISTANT_GROUNDING"])

        source_label = primary_source.source_name if primary_source else "UNKNOWN_SOURCE"
        lineage_path = (
            f"SOURCE({source_label}) -> "
            f"EVIDENCE({primary_source.source_id if primary_source else 'NO_SOURCE'}) -> "
            f"CLAIM({claim.attribute_key}={claim.claim_value[:30]}) -> "
            f"VEHICLE({claim.canonical_vehicle_id}) -> "
            f"SURFACES({','.join(surfaces)})"
        )

        return EvidenceLineageNode(
            claim_id=claim.id,
            canonical_vehicle_id=claim.canonical_vehicle_id,
            attribute_category=claim.attribute_category,
            attribute_key=claim.attribute_key,
            claim_value=claim.claim_value,
            evidence_state=claim.evidence_state.value if hasattr(claim.evidence_state, "value") else str(claim.evidence_state),
            freshness=freshness_eval,
            sources=sources,
            applicable_vehicle_scope=claim.hierarchy_level.value if hasattr(claim.hierarchy_level, "value") else str(claim.hierarchy_level),
            product_surfaces=surfaces,
            lineage_path=lineage_path
        )

    def trace_evidence_lineage(self, evidence_id: str) -> Dict[str, Any]:
        """Traces an EvidenceSource to all mapped claims and target vehicles."""
        source = self.registry.get_source(evidence_id)
        if not source:
            raise ValueError(f"Evidence source '{evidence_id}' not found.")

        mappings = self.session.query(ClaimEvidenceMapping).filter_by(source_id=evidence_id).all()
        claims = [m.claim for m in mappings if m.claim]

        vehicles_impacted = list(set(c.canonical_vehicle_id for c in claims))
        categories = list(set(c.attribute_category for c in claims))

        freshness_eval = FreshnessEngine.evaluate(
            observed_date=source.last_seen,
            policy_id=source.freshness_policy_id,
            is_deprecated=(not source.is_active)
        )

        return {
            "source": source.model_dump(),
            "freshness": freshness_eval.model_dump(),
            "total_linked_claims": len(claims),
            "categories": categories,
            "impacted_vehicles": vehicles_impacted,
            "claims": [
                {
                    "claim_id": c.id,
                    "canonical_vehicle_id": c.canonical_vehicle_id,
                    "attribute_category": c.attribute_category,
                    "attribute_key": c.attribute_key,
                    "claim_value": c.claim_value,
                    "evidence_state": c.evidence_state.value if hasattr(c.evidence_state, "value") else str(c.evidence_state)
                }
                for c in claims
            ]
        }
