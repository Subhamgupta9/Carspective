"""
CARspective — Evidence & Provenance Tests
Asserts enforcement of the 7 exact evidence states, provenance links, and validity periods.
"""

import pytest
from datetime import date, timedelta
from server.models.evidence import (
    EvidenceState,
    OrganizationType,
    HierarchyLevel,
    EvidenceSource,
    KnowledgeClaim,
)
from server.repositories.evidence_repository import EvidenceRepository
from server.domain.evidence.service import EvidenceService

def test_all_seven_evidence_states_supported():
    """Verify all 7 Phase 1.2 evidence states are defined in the enum."""
    expected = {
        "VERIFIED",
        "SUPPORTED",
        "EMPIRICAL",
        "MODEL_ESTIMATE",
        "INSUFFICIENT_DATA",
        "UNVERIFIED",
        "DEPRECATED"
    }
    actual = {state.value for state in EvidenceState}
    assert actual == expected

def test_invalid_evidence_state_rejected():
    """Attempting to construct EvidenceState with an unsupported string must fail."""
    with pytest.raises(ValueError):
        EvidenceState("GUESSWORK")
    with pytest.raises(ValueError):
        EvidenceState("HALLUCINATED")

def test_provenance_completeness_and_source_link(db_session):
    """Knowledge claim must cleanly link to its authoritative EvidenceSource."""
    service = EvidenceService(db_session)
    prov = service.get_provenance_for_vehicle("tata::nexon::gen-1-2017")
    
    assert prov.total_claims >= 1
    safety_claim = next((c for c in prov.claims if c.attribute_category == "SAFETY"), None)
    assert safety_claim is not None
    assert safety_claim.evidence_state == EvidenceState.VERIFIED
    assert "5 Stars" in safety_claim.claim_value
    assert len(safety_claim.sources) >= 1
    assert safety_claim.sources[0].organization_name == "Global NCAP"

def test_evidence_source_validity_period_handling():
    """Verify is_currently_valid() respects dates and deprecation."""
    today = date.today()
    valid_source = EvidenceSource(
        organization_name="Test Agency",
        organization_type=OrganizationType.SAFETY_AGENCY,
        valid_from=today - timedelta(days=30),
        valid_until=today + timedelta(days=365),
        verification_status=EvidenceState.VERIFIED,
        payload_hash="testhash"
    )
    assert valid_source.is_currently_valid() is True

    expired_source = EvidenceSource(
        organization_name="Test Agency",
        organization_type=OrganizationType.SAFETY_AGENCY,
        valid_from=today - timedelta(days=365),
        valid_until=today - timedelta(days=1),
        verification_status=EvidenceState.VERIFIED,
        payload_hash="testhash"
    )
    assert expired_source.is_currently_valid() is False

    deprecated_source = EvidenceSource(
        organization_name="Test Agency",
        organization_type=OrganizationType.SAFETY_AGENCY,
        valid_from=today - timedelta(days=10),
        valid_until=today + timedelta(days=10),
        verification_status=EvidenceState.DEPRECATED,
        payload_hash="testhash"
    )
    assert deprecated_source.is_currently_valid() is False
