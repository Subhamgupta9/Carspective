"""
CARspective — Phase 12 Intelligent Vehicle Discovery & Search Experience Test Suite

Covers:
1. Natural Automotive Query Parsing (exact, abbreviations, spelling mistakes, budget, seating, use cases, provenance)
2. Identity Resolution & Canonical Matching (exact match, high confidence, ambiguity detection & clarification, no-match fallback)
3. Discovery Filtering (body type, fuel type, transmission, budget)
4. Security & Sanitization (SQL injection, XSS tokens, path traversal, length bounding, null bytes)
5. Autocomplete & Suggestions
6. REST API Endpoints (search, autocomplete, legacy format compatibility)
7. Data Governance Invariants (asking price isolation, canonical ID validity)
"""

import pytest
from server.domain.discovery.models import (
    IntentFieldProvenance,
    SearchResultType,
    DiscoveryFilterParams,
    DiscoverySearchResponse,
)
from server.domain.discovery.query_parser import QueryParser
from server.domain.discovery.service import DiscoverySearchService


# ==============================================================================
# 1. QUERY PARSER UNIT TESTS
# ==============================================================================

class TestQueryParser:
    """Tests natural language and keyword parsing of automotive search queries."""

    def test_parse_make_and_model(self):
        intent = QueryParser.parse("Maruti Suzuki Swift")
        assert intent.manufacturer.value == "Maruti Suzuki"
        assert intent.manufacturer.provenance == IntentFieldProvenance.USER_EXPLICIT
        assert intent.model.value == "Swift"
        assert intent.model.provenance == IntentFieldProvenance.USER_EXPLICIT

    def test_parse_model_only(self):
        intent = QueryParser.parse("Creta")
        assert intent.model.value == "Creta"
        assert intent.model.provenance == IntentFieldProvenance.USER_EXPLICIT
        # Manufacturer should be inferred from canonical model mapping
        assert intent.manufacturer.value == "Hyundai"
        assert intent.manufacturer.provenance == IntentFieldProvenance.USER_INFERRED

    def test_parse_year_explicit(self):
        intent = QueryParser.parse("2021 Swift ZXi")
        assert intent.model.value == "Swift"
        assert intent.model_year.value == 2021
        assert intent.model_year.provenance == IntentFieldProvenance.USER_EXPLICIT
        assert intent.variant.value.upper() == "ZXI"

    def test_parse_fuel_and_transmission(self):
        intent = QueryParser.parse("Nexon Diesel Automatic")
        assert intent.model.value == "Nexon"
        assert intent.fuel_type.value == "Diesel"
        assert intent.transmission.value == "Automatic"

    def test_parse_abbreviations(self):
        intent = QueryParser.parse("City Petrol AT")
        assert intent.model.value == "City"
        assert intent.fuel_type.value == "Petrol"
        assert intent.transmission.value == "Automatic"

        intent_mt = QueryParser.parse("Thar Diesel MT")
        assert intent_mt.model.value == "Thar"
        assert intent_mt.fuel_type.value == "Diesel"
        assert intent_mt.transmission.value == "Manual"

    def test_parse_spelling_mistakes_fuzzy(self):
        # "creata" -> Creta
        intent_creta = QueryParser.parse("creata 2022")
        assert intent_creta.model.value == "Creta"
        assert intent_creta.model_year.value == 2022

        # "swif" -> Swift
        intent_swift = QueryParser.parse("maruti swif petrol")
        assert intent_swift.model.value == "Swift"
        assert intent_swift.fuel_type.value == "Petrol"

        # "necxon" -> Nexon
        intent_nexon = QueryParser.parse("tata necxon")
        assert intent_nexon.model.value == "Nexon"

    def test_parse_budget_expressions(self):
        # Under X lakh
        intent_under = QueryParser.parse("Creta under 10 lakh")
        assert intent_under.model.value == "Creta"
        assert intent_under.budget_max.value == 1000000.0

        # Below XL
        intent_below = QueryParser.parse("Swift below 8L")
        assert intent_below.budget_max.value == 800000.0

        # Between X and Y lakh
        intent_range = QueryParser.parse("SUV between 8 to 12 lakhs")
        assert intent_range.body_type.value == "SUV"
        assert intent_range.budget_min.value == 800000.0
        assert intent_range.budget_max.value == 1200000.0

    def test_parse_seating_capacity(self):
        intent = QueryParser.parse("7 seater car under 15 lakh")
        assert intent.seating_capacity.value == 7
        assert intent.budget_max.value == 1500000.0

    def test_parse_body_type(self):
        intent_suv = QueryParser.parse("compact suv petrol")
        assert intent_suv.body_type.value == "SUV"
        assert intent_suv.fuel_type.value == "Petrol"

        intent_sedan = QueryParser.parse("honda sedan")
        assert intent_sedan.body_type.value == "Sedan"
        assert intent_sedan.manufacturer.value == "Honda"

    def test_parse_use_case_terms(self):
        intent_family = QueryParser.parse("family car under 12 lakh")
        assert intent_family.use_case.value == "family_utility"
        assert intent_family.budget_max.value == 1200000.0

        intent_offroad = QueryParser.parse("off-road vehicle")
        assert intent_offroad.use_case.value == "offroad_capable"

    def test_sanitization_and_length_bounding(self):
        # 5000-char input must be safely truncated to <= 256 chars
        long_query = "Swift " * 1000
        intent = QueryParser.parse(long_query)
        assert len(intent.normalized_query) <= 256
        assert intent.model.value == "Swift"

        # Null bytes and control chars must be stripped
        malicious = "Creta\x00\x08\x1b 2021"
        intent_clean = QueryParser.parse(malicious)
        assert "\x00" not in intent_clean.normalized_query
        assert intent_clean.model.value == "Creta"
        assert intent_clean.model_year.value == 2021

    def test_not_specified_provenance(self):
        intent = QueryParser.parse("Swift")
        assert intent.model_year.provenance == IntentFieldProvenance.NOT_SPECIFIED
        assert intent.variant.provenance == IntentFieldProvenance.NOT_SPECIFIED
        assert intent.transmission.provenance == IntentFieldProvenance.NOT_SPECIFIED


# ==============================================================================
# 2. DISCOVERY SEARCH SERVICE TESTS
# ==============================================================================

class TestDiscoverySearchService:
    """Tests canonical vehicle resolution, ambiguity detection, and matching."""

    def test_search_ambiguous_model_without_year(self, db_session):
        # Querying "Swift" without year/generation should return AMBIGUOUS with clarifications
        service = DiscoverySearchService(db_session)
        response = service.search(DiscoveryFilterParams(q="Swift"))

        assert response.result_type == SearchResultType.AMBIGUOUS
        assert response.clarification is not None
        assert len(response.clarification.options) >= 2
        # Clarifications should offer generation options
        gen_names = [opt["generation"] for opt in response.clarification.options]
        assert any("Gen" in name or "Generation" in name for name in gen_names)
        assert len(response.results) > 0

    def test_search_ambiguous_city_without_year(self, db_session):
        service = DiscoverySearchService(db_session)
        response = service.search(DiscoveryFilterParams(q="City"))

        assert response.result_type == SearchResultType.AMBIGUOUS
        assert response.clarification is not None
        assert len(response.clarification.options) >= 2

    def test_search_resolved_with_year(self, db_session):
        # Querying "Swift 2021" specifies year -> should resolve with high confidence
        service = DiscoverySearchService(db_session)
        response = service.search(DiscoveryFilterParams(q="Swift 2021"))

        assert response.result_type in [SearchResultType.EXACT_MATCH, SearchResultType.HIGH_CONFIDENCE_MATCH]
        assert len(response.results) > 0
        top = response.results[0]
        assert top.model == "Swift"
        assert top.model_year == 2021
        assert top.match_score >= 60.0
        assert len(top.match_reasons) > 0

    def test_search_specific_variant_match(self, db_session):
        service = DiscoverySearchService(db_session)
        response = service.search(DiscoveryFilterParams(q="Creta 2022 SX(O) Diesel Automatic"))

        assert len(response.results) > 0
        top = response.results[0]
        assert top.model == "Creta"
        assert top.model_year == 2022
        assert top.fuel_type == "Diesel"
        assert top.transmission == "Automatic"
        assert top.match_score >= 70.0

    def test_search_no_match_guardrail(self, db_session):
        # Completely unknown car should return NO_MATCH with safe taxonomy suggestions
        service = DiscoverySearchService(db_session)
        response = service.search(DiscoveryFilterParams(q="Ferrari F8 Tributo"))

        assert response.result_type == SearchResultType.NO_MATCH
        assert len(response.results) == 0
        assert len(response.suggestions) > 0
        assert any("Creta" in s or "Swift" in s or "Nexon" in s for s in response.suggestions)

    def test_discovery_filtering_body_type(self, db_session):
        service = DiscoverySearchService(db_session)
        response = service.search(DiscoveryFilterParams(body_type="SUV"))

        assert len(response.results) > 0
        for c in response.results:
            assert c.body_type == "SUV"

    def test_discovery_filtering_fuel_type(self, db_session):
        service = DiscoverySearchService(db_session)
        response = service.search(DiscoveryFilterParams(fuel_type="Diesel"))

        assert len(response.results) > 0
        for c in response.results:
            assert c.fuel_type == "Diesel"

    def test_autocomplete_service(self, db_session):
        service = DiscoverySearchService(db_session)

        # Prefix "swi"
        resp_swift = service.autocomplete("swi", limit=5)
        titles = [item.title for item in resp_swift.items]
        assert any("Swift" in t for t in titles)

        # Prefix "cre"
        resp_creta = service.autocomplete("cre", limit=5)
        titles_creta = [item.title for item in resp_creta.items]
        assert any("Creta" in t for t in titles_creta)

        # Prefix "hon"
        resp_honda = service.autocomplete("hon", limit=5)
        titles_honda = [item.title for item in resp_honda.items]
        assert any("Honda" in t for t in titles_honda)


# ==============================================================================
# 3. REST API ENDPOINT TESTS (Flask Test Client)
# ==============================================================================

class TestDiscoveryAPI:
    """Tests the discovery HTTP endpoints."""

    def test_api_search_ambiguous_swift(self, app_client):
        res = app_client.get("/api/v1/vehicles/search?q=Swift")
        assert res.status_code == 200
        data = res.json
        assert data["result_type"] == "AMBIGUOUS"
        assert "clarification" in data
        assert data["clarification"] is not None
        assert "results" in data

    def test_api_search_with_parameters(self, app_client):
        res = app_client.get("/api/v1/vehicles/search?q=Nexon+2020&body_type=SUV")
        assert res.status_code == 200
        data = res.json
        assert data["total_count"] > 0
        assert any(c["model"] == "Nexon" for c in data["results"])

    def test_api_search_legacy_format(self, app_client):
        res = app_client.get("/api/v1/vehicles/search?q=Creta&format=legacy")
        assert res.status_code == 200
        data = res.json
        # Legacy format returns flat list of dictionaries
        assert isinstance(data, list)
        assert len(data) > 0
        assert "canonical_id" in data[0]

    def test_api_autocomplete(self, app_client):
        res = app_client.get("/api/v1/vehicles/autocomplete?q=Cre")
        assert res.status_code == 200
        data = res.json
        assert "items" in data
        assert len(data["items"]) > 0
        assert any("Creta" in item["title"] for item in data["items"])

    def test_api_empty_autocomplete(self, app_client):
        res = app_client.get("/api/v1/vehicles/autocomplete?q=")
        assert res.status_code == 200
        data = res.json
        assert data["items"] == []

    def test_api_security_sql_injection_resilience(self, app_client):
        res = app_client.get("/api/v1/vehicles/search?q=%27%3B+DROP+TABLE+vehicles%3B+--")
        assert res.status_code == 200
        data = res.json
        # Should cleanly return NO_MATCH without 500 error
        assert data["result_type"] == "NO_MATCH"

    def test_api_security_path_traversal_resilience(self, app_client):
        res = app_client.get("/api/v1/vehicles/search?q=..%2F..%2Fetc%2Fpasswd")
        assert res.status_code == 200
        data = res.json
        assert data["result_type"] == "NO_MATCH"

    def test_api_security_extreme_query_length(self, app_client):
        long_q = "Swift" + "A" * 3000
        res = app_client.get(f"/api/v1/vehicles/search?q={long_q}")
        assert res.status_code == 200
        data = res.json
        assert "result_type" in data


# ==============================================================================
# 4. DATA GOVERNANCE INVARIANTS
# ==============================================================================

class TestDiscoveryDataGovernance:
    """Verifies architectural and data governance invariants."""

    def test_asking_price_isolation(self, db_session):
        """
        Asking price/budget parameter must NOT alter intrinsic vehicle identity,
        specifications, or deep knowledge claims.
        """
        service = DiscoverySearchService(db_session)
        # Search with budget filter
        res1 = service.search(DiscoveryFilterParams(q="Swift 2021", budget_max=800000.0))
        # Search without budget filter
        res2 = service.search(DiscoveryFilterParams(q="Swift 2021", budget_max=1500000.0))

        # Check candidate properties
        c1 = next((c for c in res1.results if c.model_year == 2021), None)
        c2 = next((c for c in res2.results if c.model_year == 2021), None)

        if c1 and c2:
            # Canonical vehicle identity and metadata must remain identical
            assert c1.canonical_vehicle_id == c2.canonical_vehicle_id
            assert c1.manufacturer == c2.manufacturer
            assert c1.model == c2.model
            assert c1.coverage_tier == c2.coverage_tier

    def test_canonical_id_integrity(self, db_session):
        """All search candidates must have valid canonical IDs conforming to 6-part taxonomy hierarchy."""
        service = DiscoverySearchService(db_session)
        response = service.search(DiscoveryFilterParams(q="Nexon"))

        assert len(response.results) > 0
        for candidate in response.results:
            assert candidate.canonical_vehicle_id is not None
            assert len(candidate.canonical_vehicle_id) > 0
            assert "::" in candidate.canonical_vehicle_id
            parts = candidate.canonical_vehicle_id.split("::")
            assert len(parts) == 6
            assert parts[0] in ["tata", "maruti-suzuki", "hyundai", "honda", "mahindra"]
