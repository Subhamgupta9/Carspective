"""
CARspective — Phase 8 Assistant Intelligence Test Suite
Comprehensive testing covering:
1. Intent classification across all 16 canonical intents.
2. Context continuation and multi-vehicle comparison across turns.
3. Domain routing to Valuation, Deal, Score, Recommendation, Comparison, Inspection.
4. Source hierarchy and evidence provenance preservation.
5. Exact numeric integrity matching underlying domain outputs.
6. Adversarial hallucination resistance tests (7 distinct adversarial scenarios).
7. Mathematical independence of underlying domain models.
8. Privacy sanitization (PII redaction).
9. Provider fallback when LLM fails or times out.
10. Claim grounding and evidence reference validation.
11. REST API endpoint contract test over Flask test client.
"""

import pytest
from server.app import create_app
from server.domain.assistant.models import (
    AssistantRequest,
    AssistantIntent,
    VehicleContextInput,
    ListingContextInput,
    UserProfileInput,
    EvidenceBundle,
    AssistantEvidenceState,
    SourceDomain,
)
from server.domain.assistant.service import AssistantService
from server.domain.assistant.intent import IntentClassifier
from server.domain.assistant.policy import AssistantPolicyEngine
from server.domain.assistant.session import SessionStore
from server.domain.assistant.provider import GroundedDeterministicProvider, MockFailingLLMProvider


@pytest.fixture
def app():
    test_app = create_app({"TESTING": True})
    return test_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def assistant_service():
    return AssistantService()


# ────────────────────────────────────────────────────────────────────
# 1. Intent Classification Tests (All 16 Canonical Intents)
# ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("query,expected_intent", [
    ("Tell me about the 2020 Honda City", AssistantIntent.VEHICLE_OVERVIEW),
    ("What are the engine specs and boot space of Creta?", AssistantIntent.SPECIFICATION),
    ("What is the fair market value of this 2018 Swift?", AssistantIntent.VALUATION),
    ("Is ₹7.5 lakh a good deal for this City?", AssistantIntent.DEAL_ANALYSIS),
    ("How much should I negotiate below the asking price?", AssistantIntent.NEGOTIATION),
    ("Why is this vehicle scored 82 on CarSpective?", AssistantIntent.SCORE),
    ("Should I buy this car for my family commute?", AssistantIntent.RECOMMENDATION),
    ("Compare the Honda City vs Hyundai Verna", AssistantIntent.COMPARISON),
    ("What should I check before buying this used car?", AssistantIntent.INSPECTION),
    ("What are the biggest risks with this vehicle?", AssistantIntent.RISK),
    ("What is the estimated maintenance cost and ownership experience?", AssistantIntent.OWNERSHIP),
    ("What is the market trend and depreciation for this model?", AssistantIntent.MARKET),
    ("What are good alternatives to the Hyundai Creta?", AssistantIntent.ALTERNATIVES),
    ("What information is missing and unverified?", AssistantIntent.EVIDENCE),
    ("Why did CarSpective arrive at this conclusion?", AssistantIntent.EXPLANATION),
    ("What is the weather in Mumbai tomorrow?", AssistantIntent.UNKNOWN),
])
def test_intent_classification_all_canonical_intents(query, expected_intent):
    detected = IntentClassifier.classify(query)
    assert detected == expected_intent


# ────────────────────────────────────────────────────────────────────
# 2. Conversational Context & Continuation Across Turns
# ────────────────────────────────────────────────────────────────────

def test_context_continuation_across_turns(assistant_service):
    """Verifies assistant retains active vehicle and transitions to comparison across turns."""
    # Turn 1: Establish vehicle context
    req1 = AssistantRequest(
        message="Tell me about the 2021 Honda City Petrol Manual.",
        vehicle=VehicleContextInput(brand="Honda", model="City", manufacturing_year=2021, fuel_type="Petrol", transmission_type="Manual")
    )
    res1 = assistant_service.handle_message(req1)
    session_id = res1.session_id
    assert res1.session_context_updates["has_current_vehicle"] is True
    assert "Honda City" in res1.session_context_updates["current_vehicle_name"]

    # Turn 2: Follow-up question using pronoun "it" without repeating vehicle name
    req2 = AssistantRequest(
        message="How much is it worth in the market?",
        session_id=session_id
    )
    res2 = assistant_service.handle_message(req2)
    assert res2.intent == AssistantIntent.VALUATION
    assert "Honda City" in res2.answer
    assert "valuation.fair_market_value" in res2.evidence_refs

    # Turn 3: Add comparison candidate
    req3 = AssistantRequest(
        message="What about the Hyundai Verna?",
        session_id=session_id
    )
    res3 = assistant_service.handle_message(req3)
    assert res3.intent == AssistantIntent.COMPARISON
    assert res3.session_context_updates["compared_count"] >= 1

    # Turn 4: Compare safety between established vehicles
    req4 = AssistantRequest(
        message="Which one is safer?",
        session_id=session_id
    )
    res4 = assistant_service.handle_message(req4)
    assert res4.intent == AssistantIntent.COMPARISON
    assert "comparison.overall_winner" in res4.evidence_refs or len(res4.referenced_domains) > 0


# ────────────────────────────────────────────────────────────────────
# 3. Domain Routing Verification
# ────────────────────────────────────────────────────────────────────

def test_valuation_domain_routing(assistant_service):
    req = AssistantRequest(
        message="What is the estimated fair price for this vehicle?",
        vehicle=VehicleContextInput(brand="Maruti", model="Swift", manufacturing_year=2019, km_driven=35000)
    )
    res = assistant_service.handle_message(req)
    assert res.intent == AssistantIntent.VALUATION
    assert "VALUATION" in res.referenced_domains
    assert any("valuation.fair_market_value" in ref for ref in res.evidence_refs)


def test_deal_analysis_domain_routing(assistant_service):
    req = AssistantRequest(
        message="Is this asking price a good deal?",
        vehicle=VehicleContextInput(brand="Hyundai", model="Creta", manufacturing_year=2020, km_driven=40000),
        listing=ListingContextInput(asking_price=1150000)
    )
    res = assistant_service.handle_message(req)
    assert res.intent == AssistantIntent.DEAL_ANALYSIS
    assert "DEAL_ANALYZER" in res.referenced_domains
    assert any("deal.classification" in ref for ref in res.evidence_refs)


def test_score_domain_routing(assistant_service):
    req = AssistantRequest(
        message="Why is this car scored this way on CarSpective?",
        vehicle=VehicleContextInput(brand="Tata", model="Nexon", manufacturing_year=2021)
    )
    res = assistant_service.handle_message(req)
    assert res.intent == AssistantIntent.SCORE
    assert "SCORE" in res.referenced_domains
    assert any("score.overall" in ref for ref in res.evidence_refs)


def test_inspection_domain_routing(assistant_service):
    req = AssistantRequest(
        message="What should I check before buying?",
        vehicle=VehicleContextInput(brand="Honda", model="City", manufacturing_year=2018)
    )
    res = assistant_service.handle_message(req)
    assert res.intent == AssistantIntent.INSPECTION
    assert "INSPECTION" in res.referenced_domains
    assert any("inspection.readiness" in ref for ref in res.evidence_refs)


# ────────────────────────────────────────────────────────────────────
# 4. Exact Numeric Integrity Tests
# ────────────────────────────────────────────────────────────────────

def test_numeric_integrity_matches_domain_outputs(assistant_service):
    """Verifies that numbers in the assistant answer match domain engine outputs exactly."""
    req = AssistantRequest(
        message="What is the fair market valuation and expected range?",
        vehicle=VehicleContextInput(
            brand="Honda",
            model="City",
            manufacturing_year=2019,
            km_driven=50000,
            fuel_type="Petrol",
            transmission_type="Manual"
        )
    )
    res = assistant_service.handle_message(req)

    # Find valuation evidence item
    fmv_item = next((it for it in res.evidence_bundle if it.id == "valuation.fair_market_value"), None)
    range_item = next((it for it in res.evidence_bundle if it.id == "valuation.range"), None)

    assert fmv_item is not None
    assert range_item is not None

    expected_fmv_str = f"₹{fmv_item.value:,.0f}"
    expected_low_str = f"₹{range_item.value['lower']:,.0f}"
    expected_high_str = f"₹{range_item.value['upper']:,.0f}"

    # Factual strings must be present in the generated answer
    assert expected_fmv_str in res.answer
    assert expected_low_str in res.answer
    assert expected_high_str in res.answer


# ────────────────────────────────────────────────────────────────────
# 5. Adversarial Hallucination Resistance Tests (7 Scenarios)
# ────────────────────────────────────────────────────────────────────

def test_adversarial_1_unsupported_reliability_claim(assistant_service):
    """Adversarial test: User asks about an unverified gearbox failure claim."""
    req = AssistantRequest(
        message="Does this Honda City have a common catastrophic gearbox failure after 80,000 km?",
        vehicle=VehicleContextInput(brand="Honda", model="City", manufacturing_year=2018)
    )
    res = assistant_service.handle_message(req)
    # Must NOT confirm an unverified catastrophic failure as fact
    assert "definitely broken" not in res.answer.lower()
    assert "mechanic" in res.answer.lower() or "inspection" in res.answer.lower() or "score" in res.answer.lower()


def test_adversarial_2_invented_price(assistant_service):
    """Adversarial test: User asks if car is worth an absurdly low price not in evidence."""
    req = AssistantRequest(
        message="Is this car worth only ₹1,50,000?",
        vehicle=VehicleContextInput(brand="Hyundai", model="Creta", manufacturing_year=2021)
    )
    res = assistant_service.handle_message(req)
    # Must report the actual statistical baseline from valuation, not agree with invented price
    val_item = next((it for it in res.evidence_bundle if it.id == "valuation.fair_market_value"), None)
    if val_item:
        assert f"₹{val_item.value:,.0f}" in res.answer


def test_adversarial_3_invented_safety_rating(assistant_service):
    """Adversarial test: User asks to confirm unverified 5-star crash rating."""
    req = AssistantRequest(
        message="Can you guarantee this car is 100% safe to buy and accident-free?",
        vehicle=VehicleContextInput(brand="Maruti", model="Swift", manufacturing_year=2017)
    )
    res = assistant_service.handle_message(req)
    # Must NEVER output prohibited term "safe to buy"
    assert "safe to buy" not in res.answer.lower()
    # Must advise physical inspection
    assert "inspection" in res.answer.lower() or "mechanic" in res.answer.lower()


def test_adversarial_4_invented_odometer_authenticity(assistant_service):
    """Adversarial test: User asks if odometer is guaranteed genuine without records."""
    req = AssistantRequest(
        message="The seller says odometer is 100% authentic with zero accidents. Is that verified?",
        vehicle=VehicleContextInput(brand="Honda", model="City", manufacturing_year=2016)
    )
    res = assistant_service.handle_message(req)
    # Must advise verifying paperwork, never claim seller verbal statements are verified
    assert "unverified" in res.answer.lower() or "verify" in res.answer.lower() or "records" in res.answer.lower()


def test_adversarial_5_prohibited_terminology_enforced(assistant_service):
    """Adversarial test: Verifies that prohibited terminology is strictly blocked."""
    raw = "This car is safe to buy with guaranteed resale value and verified transaction price."
    governed = AssistantPolicyEngine.enforce_terminology(raw)
    assert "safe to buy" not in governed.lower()
    assert "guaranteed resale" not in governed.lower()
    assert "verified transaction price" not in governed.lower()
    assert "historical seller asking-price baseline" in governed.lower()


def test_adversarial_6_insufficient_data_transparency(assistant_service):
    """Adversarial test: Question with no vehicle and no data discloses missing information."""
    req = AssistantRequest(message="What is the exact fair market value?")
    res = assistant_service.handle_message(req)
    assert "not currently have enough verified evidence" in res.answer or "No active vehicle context" in (res.uncertainty or "")


def test_adversarial_7_user_observation_not_diagnosed_as_fact(assistant_service):
    """Adversarial test: User reports a noise; assistant must not diagnose mechanical failure."""
    req = AssistantRequest(
        message="I heard a clicking noise from the steering during test drive.",
        vehicle=VehicleContextInput(brand="Tata", model="Nexon", manufacturing_year=2020)
    )
    res = assistant_service.handle_message(req)
    # Must mandate mechanic verification without declaring absolute failure
    assert "mechanic" in res.answer.lower() or "inspection" in res.answer.lower()
    assert "definitely damaged" not in res.answer.lower()


# ────────────────────────────────────────────────────────────────────
# 6. Independence of Underlying Domain Engines
# ────────────────────────────────────────────────────────────────────

def test_domain_mathematical_independence(assistant_service):
    """Verifies running the assistant does not mutate underlying domain models or states."""
    from server.domain.valuation.service import ValuationService
    from server.domain.valuation.models import ValuationRequest
    from server.domain.scoring.service import ScoringService
    from server.domain.scoring.models import ScoreRequest

    # Valuation before assistant
    val_svc = ValuationService()
    v_req = ValuationRequest(brand="Honda", model="City", manufacturing_year=2019, km_driven=45000)
    v_res_before = val_svc.evaluate_valuation(v_req)

    # Scoring before assistant
    score_svc = ScoringService()
    s_req = ScoreRequest(brand="Honda", model="City", manufacturing_year=2019, km_driven=45000)
    s_res_before = score_svc.calculate_score(s_req)

    # Run assistant multiple times with arbitrary questions
    assistant_service.handle_message(AssistantRequest(
        message="What is the price?",
        vehicle=VehicleContextInput(brand="Honda", model="City", manufacturing_year=2019, km_driven=45000)
    ))
    assistant_service.handle_message(AssistantRequest(
        message="Is this overpriced?",
        vehicle=VehicleContextInput(brand="Honda", model="City", manufacturing_year=2019, km_driven=45000),
        listing=ListingContextInput(asking_price=900000)
    ))

    # Valuation after assistant
    v_res_after = val_svc.evaluate_valuation(v_req)
    # Score after assistant
    s_res_after = score_svc.calculate_score(s_req)

    assert v_res_before.estimated_fair_market_value == v_res_after.estimated_fair_market_value
    assert v_res_before.expected_fair_market_range.lower_bound == v_res_after.expected_fair_market_range.lower_bound
    assert s_res_before.overall_score == s_res_after.overall_score


# ────────────────────────────────────────────────────────────────────
# 7. Privacy & PII Sanitization Tests
# ────────────────────────────────────────────────────────────────────

def test_privacy_sanitization_removes_pii(assistant_service):
    """Verifies sensitive personal data (phone, Aadhaar, email) is redacted from conversation store."""
    raw_message = (
        "My phone number is 9876543210 and my email is testuser@example.com. "
        "My Aadhaar is 1234 5678 9012. Is the 2019 Honda City worth ₹7,00,000?"
    )
    req = AssistantRequest(
        message=raw_message,
        vehicle=VehicleContextInput(brand="Honda", model="City", manufacturing_year=2019)
    )
    res = assistant_service.handle_message(req)
    session_id = res.session_id

    # Inspect stored conversation turn in session store
    ctx = assistant_service.session_store.get_or_create(session_id=session_id)
    assert len(ctx.conversation_history) >= 2
    stored_user_turn = ctx.conversation_history[0].content

    # Assert PII is redacted
    assert "9876543210" not in stored_user_turn
    assert "[PHONE_REDACTED]" in stored_user_turn
    assert "testuser@example.com" not in stored_user_turn
    assert "[EMAIL_REDACTED]" in stored_user_turn
    assert "1234 5678 9012" not in stored_user_turn
    assert "[AADHAAR_REDACTED]" in stored_user_turn


# ────────────────────────────────────────────────────────────────────
# 8. Provider Fallback Behavior Test
# ────────────────────────────────────────────────────────────────────

def test_provider_fallback_to_deterministic_explainer():
    """Verifies that if an external LLM fails, the service falls back gracefully without crashing."""
    failing_provider = MockFailingLLMProvider()
    service_with_fallback = AssistantService(llm_provider=failing_provider)

    req = AssistantRequest(
        message="What is the valuation of this 2018 Maruti Swift?",
        vehicle=VehicleContextInput(brand="Maruti", model="Swift", manufacturing_year=2018)
    )
    # Must succeed via fallback without raising exception
    res = service_with_fallback.handle_message(req)
    assert res.answer != ""
    assert "estimated historical market asking-price baseline" in res.answer
    assert "valuation.fair_market_value" in res.evidence_refs


# ────────────────────────────────────────────────────────────────────
# 9. Claim Grounding Verification
# ────────────────────────────────────────────────────────────────────

def test_claim_grounding_references_valid_evidence_ids(assistant_service):
    """Verifies every response provides traceable citations to evidence IDs."""
    req = AssistantRequest(
        message="Is ₹6.8 lakh a good deal for this 2018 Swift?",
        vehicle=VehicleContextInput(brand="Maruti", model="Swift", manufacturing_year=2018),
        listing=ListingContextInput(asking_price=680000)
    )
    res = assistant_service.handle_message(req)
    assert len(res.evidence_refs) > 0
    # Citations must reference actual bundle IDs
    bundle_ids = {it.id for it in res.evidence_bundle}
    for ref in res.evidence_refs:
        assert ref in bundle_ids


# ────────────────────────────────────────────────────────────────────
# 10. REST API Contract Tests (POST /api/v1/assistant)
# ────────────────────────────────────────────────────────────────────

def test_api_post_assistant_success(client):
    payload = {
        "message": "What is the fair market value of a 2019 Honda City?",
        "vehicle": {
            "brand": "Honda",
            "model": "City",
            "manufacturing_year": 2019,
            "fuel_type": "Petrol",
            "transmission_type": "Manual"
        }
    }
    resp = client.post("/api/v1/assistant", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "session_id" in data
    assert "answer" in data
    assert data["intent"] == "VALUATION"
    assert "VALUATION" in data["referenced_domains"]
    assert "disclaimer" in data


def test_api_post_assistant_validation_error(client):
    # Empty message should fail validation
    payload = {"message": ""}
    resp = client.post("/api/v1/assistant", json=payload)
    assert resp.status_code == 422
    data = resp.get_json()
    assert data["status"] == 422


def test_api_post_assistant_non_json_error(client):
    resp = client.post("/api/v1/assistant", data="plain text message", content_type="text/plain")
    assert resp.status_code == 415


def test_api_post_assistant_legacy_query_payload_success(client):
    payload = {
        "query": "Is the asking price fair?",
        "context_vehicle": {
            "brand": "Honda",
            "model": "City",
            "year": 2020,
            "fuel_type": "Petrol",
            "transmission_type": "Manual",
            "asking_price": 850000,
            "km_driven": 40000,
        }
    }
    resp = client.post("/api/v1/assistant", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "session_id" in data
    assert "answer" in data
    assert data["intent"] == "DEAL_ANALYSIS"
    assert "DEAL_ANALYZER" in data["referenced_domains"]
    # Check backward compatibility fields
    assert "citations" in data
    assert len(data["citations"]) > 0
    assert "source_domains_queried" in data
    assert "DEAL_ANALYZER" in data["source_domains_queried"]


def test_api_post_assistant_vehicle_and_listing_payload_success(client):
    payload = {
        "message": "Is this asking price a good deal?",
        "vehicle": {
            "brand": "Honda",
            "model": "City",
            "manufacturing_year": 2020,
            "fuel_type": "Petrol",
            "transmission_type": "Manual",
            "km_driven": 40000,
            "canonical_vehicle_id": "honda-city-2020",
        },
        "listing": {
            "asking_price": 850000,
        }
    }
    resp = client.post("/api/v1/assistant", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "session_id" in data
    assert "answer" in data
    assert data["intent"] == "DEAL_ANALYSIS"
    assert len(data["evidence_bundle"]) > 0
    assert len(data["citations"]) == len(data["evidence_bundle"])


def test_assistant_request_legacy_payload_immutability_and_nulls():
    caller_dict = {
        "query": "Is this a good deal?",
        "context_vehicle": {
            "brand": "Honda",
            "model": "City",
            "year": 2020,
            "asking_price": 850000,
        },
        "comparison_vehicles": [
            {"brand": "Hyundai", "model": "Verna", "year": 2019}
        ]
    }
    req = AssistantRequest.model_validate(caller_dict)

    # Immutability: caller_dict must NOT have been mutated in place
    assert "message" not in caller_dict
    assert "vehicle" not in caller_dict
    assert "compared_vehicles" not in caller_dict
    assert "listing" not in caller_dict

    # Validated model properties
    assert req.message == "Is this a good deal?"
    assert req.vehicle is not None
    assert req.vehicle.brand == "Honda"
    assert req.vehicle.manufacturing_year == 2020
    assert req.listing is not None
    assert req.listing.asking_price == 850000.0
    assert req.compared_vehicles is not None
    assert len(req.compared_vehicles) == 1
    assert req.compared_vehicles[0].brand == "Hyundai"

    # Null safety: ensure explicit None values do not crash validator
    req_nulls = AssistantRequest.model_validate({
        "message": None,
        "query": "Fallback question",
        "context_vehicle": None,
        "comparison_vehicles": None,
        "vehicle": None,
        "listing": None,
    })
    assert req_nulls.message == "Fallback question"
    assert req_nulls.vehicle is None
    assert req_nulls.compared_vehicles is None
    assert req_nulls.listing is None
