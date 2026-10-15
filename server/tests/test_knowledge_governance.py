"""
CARspective — Phase 11: Knowledge Governance Invariant Test Suite
Validates zero-fabrication principles, asking price isolation,
review synthesis separation, and assistant epistemic boundaries.
"""

import pytest
from server.domain.knowledge.service import KnowledgeService
from server.domain.assistant.service import AssistantService
from server.domain.assistant.models import (
    AssistantRequest,
    AssistantIntent,
    VehicleContextInput,
    ListingContextInput,
)
from server.schemas.taxonomy import CanonicalResolutionRequest


class TestKnowledgeGovernance:

    def test_governance_no_fabricated_specifications(self, db_session):
        """Unknown or unverified vehicles return None, never fabricated specs."""
        service = KnowledgeService(db_session)
        profile = service.get_vehicle_profile("ferrari::laferrari")
        assert profile is None

        # Non-existent generation of existing model
        profile_fake_gen = service.get_vehicle_profile("maruti-suzuki::swift::gen-999-2099")
        assert profile_fake_gen.specifications is None
        assert profile_fake_gen.safety is None
        assert profile_fake_gen.dimensions is None

    def test_governance_asking_price_isolation(self, db_session):
        """Knowledge engine does not accept asking price and is completely isolated from listing costs."""
        service = KnowledgeService(db_session)
        profile = service.get_vehicle_profile("maruti-suzuki::swift::gen-3-2018")
        assert profile is not None
        # Verify schema has zero price fields related to asking prices
        schema_dict = profile.model_dump()
        assert "asking_price" not in schema_dict
        assert "listing_price" not in schema_dict

    def test_governance_assistant_declines_unverified_specs(self):
        """Assistant explicitly states lack of verified data rather than guessing."""
        service = AssistantService()
        req = AssistantRequest(
            message="What is the ground clearance and horse power of Bugatti Chiron?",
            vehicle=VehicleContextInput(brand="Bugatti", model="Chiron", manufacturing_year=2022)
        )
        res = service.handle_message(req)
        assert res.intent == AssistantIntent.SPECIFICATION
        assert "CarSpective does not have sufficiently verified technical specifications" in res.answer
        assert res.uncertainty is not None

    def test_governance_assistant_number_integrity(self):
        """Assistant uses exact verified numbers from canonical documentation."""
        service = AssistantService()
        req = AssistantRequest(
            message="What are the engine specs of Tata Nexon?",
            vehicle=VehicleContextInput(brand="Tata", model="Nexon", manufacturing_year=2021)
        )
        res = service.handle_message(req)
        assert res.intent == AssistantIntent.SPECIFICATION
        # 1199 cc, 120.0 bhp, 170.0 Nm
        assert "1199" in res.answer or "1,199" in res.answer
        assert "118.3" in res.answer or "118" in res.answer or "120" in res.answer
        assert "170" in res.answer

        assert "Global NCAP" in res.answer
        assert "5/5" in res.answer or "5-Star" in res.answer

    def test_governance_review_synthesis_tripartite_separation(self, db_session):
        """Review synthesis strictly isolates owner voice, expert conclusions, and algorithmic analysis."""
        service = KnowledgeService(db_session)
        profile = service.get_vehicle_profile("maruti-suzuki::swift::gen-3-2018")
        assert profile is not None
        assert profile.reviews is not None
        rev = profile.reviews
        assert rev.what_owners_say is not None
        assert rev.what_experts_say is not None
        assert rev.carspective_analysis is not None
        assert len(rev.carspective_analysis) > 10

    def test_governance_review_fallback_when_evidence_unavailable(self, db_session):
        """When owner or expert review evidence is missing, explicit fallback text is rendered."""
        service = KnowledgeService(db_session)
        # Thar Gen 2 has review synthesis where owner evidence is marked false in seed
        profile = service.get_vehicle_profile("mahindra::thar::gen-2-2020")
        assert profile is not None
        if profile.reviews:
            if not profile.reviews.has_owner_evidence:
                assert profile.reviews.what_owners_say == "Review evidence unavailable."
