"""
CARspective — Phase 17 Live Market Intelligence & Market Evidence Test Suite
Verifies:
1. Governed market fixture connector and schema validation
2. Deduplication engine (exact duplicate, probable duplicate, distinct)
3. Outlier governance engine (price, mileage, model deviation bounds & retention)
4. Vectorized aggregation engine (percentiles, supply, regional mix, historical shift)
5. Security controls (SSRF protection & PII sanitization)
6. Epistemic honesty & semantic invariants:
   - TRANSACTION-PRICE FABRICATION = 0
   - REALIZED-RESALE FABRICATION = 0
   - OBSERVED-SELL-THROUGH FABRICATION = 0
   - HISTORICAL/CURRENT CONFUSION = 0
   - VALUATION MODEL SHA-256 IMMUTABILITY
7. Database persistence and query retrieval
8. REST API endpoints under /api/v1/market/current/ and /api/v1/market/admin/ingest
9. Assistant tool & Vehicle Workspace synthesis integration
10. Scalability benchmark over 10,000 synthetic observations (< 2.0s)
"""

import os
import json
import time
import hashlib
import pytest
from datetime import datetime, timezone
from typing import List, Dict, Any

from server.app import create_app
from server.config import settings
from server.infrastructure.database import ScopedSession, init_db
from server.models.market_observation import CurrentMarketObservation
from server.domain.market.current_models import (
    CurrentObservationType,
    SellerType,
    ListingStatus,
    DuplicateClassification,
    CurrentFreshnessState,
    CurrentSupplyTier,
    CurrentMarketObservationRecord,
    CurrentPriceDistribution,
    CurrentMarketSupply,
    CurrentRegionalIntelligence,
    CurrentVsHistoricalComparison,
    CurrentMarketEvidence,
    CurrentMarketIntelligenceResponse,
)
from server.domain.market.connectors import (
    GovernedMarketFixtureConnector,
    MarketSecurityValidator,
)
from server.domain.market.deduplication import MarketDeduplicationEngine
from server.domain.market.outliers import MarketOutlierEngine
from server.domain.market.aggregation import CurrentMarketAggregationEngine
from server.domain.market.service import MarketIntelligenceService, get_market_intelligence_service
from server.domain.assistant.models import (
    VehicleContextInput,
    EvidenceBundle,
    AssistantEvidenceState,
    SourceDomain,
)
from server.domain.assistant.tools import DomainToolDispatcher
from server.domain.workspace.service import VehicleWorkspaceService

EXPECTED_MODEL_SHA256 = "4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1"


@pytest.fixture(scope="module")
def _isolated_live_market_setup(tmp_path_factory):
    """Create an isolated temporary SQLite database exclusively for test_live_market module."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from server.models.base import Base
    from server.models.taxonomy import (
        Manufacturer, VehicleModel, VehicleGeneration, ModelYear,
        VehicleVariant, PowertrainConfiguration
    )
    from scripts.generate_and_load_seeds import build_seed_data

    db_file = tmp_path_factory.mktemp("live_market") / "test_live_market.db"
    db_url = f"sqlite:///{db_file.resolve()}"
    engine = create_engine(db_url, future=True, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    SessionMaker = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    session = SessionMaker()

    # Seed taxonomy for canonical mapping
    seed = build_seed_data()
    for m_data in seed["manufacturers"]:
        m_obj = Manufacturer(name=m_data["name"], slug=m_data["slug"], is_active=True)
        session.add(m_obj)
        session.flush()
        for mod_data in m_data.get("models", []):
            mod_obj = VehicleModel(
                manufacturer_id=m_obj.id,
                name=mod_data["name"],
                slug=mod_data["slug"],
                body_type=mod_data["body_type"],
                is_active=True
            )
            session.add(mod_obj)
            session.flush()
            for gen_data in mod_data.get("generations", []):
                gen_obj = VehicleGeneration(
                    model_id=mod_obj.id,
                    name=gen_data["name"],
                    slug=gen_data["slug"],
                    year_start=gen_data["year_start"],
                    year_end=gen_data.get("year_end"),
                )
                session.add(gen_obj)
                session.flush()
                for yr in gen_data.get("years", []):
                    session.add(ModelYear(generation_id=gen_obj.id, calendar_year=yr))
                for var_data in gen_data.get("variants", []):
                    var_obj = VehicleVariant(
                        generation_id=gen_obj.id,
                        name=var_data["name"],
                        slug=var_data["slug"],
                    )
                    session.add(var_obj)
                    session.flush()
                    for pt_data in var_data.get("powertrains", []):
                        session.add(PowertrainConfiguration(
                            variant_id=var_obj.id,
                            fuel_type=pt_data["fuel_type"],
                            transmission_type=pt_data["transmission_type"],
                            slug=pt_data.get("slug")
                        ))
    session.commit()

    svc = MarketIntelligenceService(session=session)
    fixtures = GovernedMarketFixtureConnector.load_default_fixtures()
    svc.ingest_current_observations(
        records=fixtures,
        source_id="src-current-market-aggregator-2026",
        snapshot_reference="governed-fixture-2026-q3"
    )

    try:
        yield {"service": svc, "session": session, "engine": engine}
    finally:
        session.close()
        engine.dispose()


@pytest.fixture(scope="module")
def live_market_service(_isolated_live_market_setup):
    return _isolated_live_market_setup["service"]


@pytest.fixture(scope="module")
def app_client(_isolated_live_market_setup):
    from server.api.v1 import market_routes
    from server.domain.market.service import reset_market_intelligence_service

    orig_svc = market_routes._MARKET_SERVICE
    market_routes._MARKET_SERVICE = _isolated_live_market_setup["service"]
    app = create_app({"TESTING": True})

    try:
        with app.test_client() as client:
            yield client
    finally:
        market_routes._MARKET_SERVICE = orig_svc
        reset_market_intelligence_service()


# =========================================================================
# 1. FIXTURE CONNECTOR & SCHEMA VALIDATION
# =========================================================================

def test_fixture_connector_and_schema_validation():
    """Verify governed fixture connector loads valid schema records."""
    records = GovernedMarketFixtureConnector.load_default_fixtures()
    assert len(records) >= 20, f"Expected at least 20 fixture observations, found {len(records)}"

    connector = GovernedMarketFixtureConnector()
    validated_count = 0
    for r in records:
        norm = connector.normalize(r)
        obs_dt = norm.get("observed_at")
        if isinstance(obs_dt, str):
            obs_dt = datetime.fromisoformat(obs_dt.replace("Z", "+00:00"))
        elif not isinstance(obs_dt, datetime):
            obs_dt = datetime.now(timezone.utc)

        model_obj = CurrentMarketObservationRecord(
            source_id=norm["source_id"],
            source_record_reference=norm["source_record_reference"],
            observed_at=obs_dt,
            canonical_vehicle_id=f"{norm['brand'].lower()}::{norm['model'].lower()}",
            asking_price=norm["asking_price"],
            model_year=norm["model_year"],
            mileage=norm["mileage"],
            location_city=norm["location_city"],
        )
        assert model_obj.source_id is not None
        assert model_obj.asking_price > 0
        validated_count += 1
    assert validated_count == len(records)


def test_schema_rejection_of_invalid_records():
    """Verify Pydantic model rejects negative price or missing canonical id."""
    with pytest.raises(Exception):
        CurrentMarketObservationRecord(
            source_id="src-test",
            source_record_reference="ref-1",
            observed_at=datetime.now(timezone.utc),
            canonical_vehicle_id="maruti-suzuki::swift",
            asking_price=-50000,  # Negative price rejected
            model_year=2020,
            mileage=30000,
            location_city="Delhi NCR",
        )


# =========================================================================
# 2. DEDUPLICATION ENGINE
# =========================================================================

def test_deduplication_exact_duplicate_by_reference():
    """Verify exact duplicate by matching source_record_reference."""
    rec1 = {
        "id": "obs-1",
        "source_id": "src-aggregator",
        "source_record_reference": "listing-unique-123",
        "canonical_vehicle_id": "maruti-suzuki::swift::gen-3-2018",
        "model_year": 2021,
        "asking_price": 650000,
        "mileage": 35000,
        "location_city": "Delhi NCR",
        "observed_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
    }
    rec2 = dict(rec1)
    rec2["id"] = "obs-2"

    dup_status, dup_of_id = MarketDeduplicationEngine.evaluate_duplicate(rec2, [rec1])
    assert dup_status == DuplicateClassification.EXACT_DUPLICATE
    assert dup_of_id == "obs-1"


def test_deduplication_exact_duplicate_by_features_and_window():
    """Verify exact duplicate by price, km, city within 7-day window."""
    rec1 = {
        "id": "obs-1",
        "source_id": "src-aggregator-a",
        "source_record_reference": "ref-a",
        "canonical_vehicle_id": "maruti-suzuki::swift::gen-3-2018",
        "model_year": 2021,
        "asking_price": 650000,
        "mileage": 35000,
        "location_city": "Mumbai",
        "observed_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
    }
    rec2 = {
        "id": "obs-2",
        "source_id": "src-aggregator-b",
        "source_record_reference": "ref-b",
        "canonical_vehicle_id": "maruti-suzuki::swift::gen-3-2018",
        "model_year": 2021,
        "asking_price": 650000,
        "mileage": 35000,
        "location_city": "Mumbai",
        "observed_at": datetime(2026, 8, 5, tzinfo=timezone.utc),  # 4 days later
    }

    dup_status, dup_of_id = MarketDeduplicationEngine.evaluate_duplicate(rec2, [rec1])
    assert dup_status == DuplicateClassification.EXACT_DUPLICATE
    assert dup_of_id == "obs-1"


def test_deduplication_probable_duplicate():
    """Verify probable duplicate (price within 1.5%, mileage within 500km, within 14 days)."""
    rec1 = {
        "id": "obs-1",
        "canonical_vehicle_id": "hyundai::creta::gen-2-2020",
        "model_year": 2022,
        "fuel_type": "PETROL",
        "transmission": "MANUAL",
        "asking_price": 1200000,
        "mileage": 25000,
        "location_city": "Bengaluru",
        "observed_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
    }
    rec2 = {
        "id": "obs-2",
        "canonical_vehicle_id": "hyundai::creta::gen-2-2020",
        "model_year": 2022,
        "fuel_type": "PETROL",
        "transmission": "MANUAL",
        "asking_price": 1210000,  # +0.83%
        "mileage": 25200,         # +200 km
        "location_city": "Bengaluru",
        "observed_at": datetime(2026, 8, 10, tzinfo=timezone.utc),  # 9 days later
    }

    dup_status, dup_of_id = MarketDeduplicationEngine.evaluate_duplicate(rec2, [rec1])
    assert dup_status == DuplicateClassification.PROBABLE_DUPLICATE
    assert dup_of_id == "obs-1"


def test_deduplication_distinct_records():
    """Verify distinct records are classified as DISTINCT."""
    rec1 = {
        "id": "obs-1",
        "canonical_vehicle_id": "hyundai::creta::gen-2-2020",
        "model_year": 2022,
        "asking_price": 1200000,
        "mileage": 25000,
        "location_city": "Bengaluru",
        "observed_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
    }
    rec2 = {
        "id": "obs-2",
        "canonical_vehicle_id": "hyundai::creta::gen-2-2020",
        "model_year": 2022,
        "asking_price": 1350000,  # 12.5% higher
        "mileage": 12000,
        "location_city": "Delhi NCR",
        "observed_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
    }

    dup_status, dup_of_id = MarketDeduplicationEngine.evaluate_duplicate(rec2, [rec1])
    assert dup_status == DuplicateClassification.DISTINCT
    assert dup_of_id is None


# =========================================================================
# 3. OUTLIER GOVERNANCE ENGINE
# =========================================================================

def test_outlier_detection_extreme_price_bounds():
    """Verify extreme price bounds (< 25k, > 10Cr)."""
    # Low outlier
    is_out, reasons, elig = MarketOutlierEngine.evaluate_outlier({
        "asking_price": 15000,
        "mileage": 45000,
        "model_year": 2018,
    })
    assert is_out is True
    assert elig is False
    assert any("minimum realistic threshold" in r.lower() for r in reasons)

    # High outlier
    is_out, reasons, elig = MarketOutlierEngine.evaluate_outlier({
        "asking_price": 120000000,
        "mileage": 15000,
        "model_year": 2022,
    })
    assert is_out is True
    assert elig is False
    assert any("maximum realistic ceiling" in r.lower() for r in reasons)


def test_outlier_detection_mileage_and_year_bounds():
    """Verify mileage and model year bounds."""
    # Excessive mileage
    is_out, reasons, elig = MarketOutlierEngine.evaluate_outlier({
        "asking_price": 500000,
        "mileage": 750000,
        "model_year": 2018,
    })
    assert is_out is True
    assert elig is False
    assert any("mileage" in r.lower() for r in reasons)

    # Implausibly low mileage on older car
    is_out, reasons, elig = MarketOutlierEngine.evaluate_outlier({
        "asking_price": 600000,
        "mileage": 45,
        "model_year": 2019,
    })
    assert is_out is True
    assert elig is False
    assert any("odometer" in r.lower() or "mileage" in r.lower() for r in reasons)


def test_outlier_detection_model_relative_deviation():
    """Verify model-relative price deviations (< 0.20x or > 4.0x baseline)."""
    # Extremely low relative price (e.g. ₹80,000 for a car typically ₹6,50,000)
    is_out, reasons, elig = MarketOutlierEngine.evaluate_outlier({
        "asking_price": 80000,
        "mileage": 50000,
        "model_year": 2021,
    }, model_typical_price=650000)
    assert is_out is True
    assert elig is False
    assert any("suspiciously" in r.lower() or "baseline" in r.lower() or "salvage" in r.lower() for r in reasons)


# =========================================================================
# 4. AGGREGATION ENGINE & STATISTICS
# =========================================================================

def test_aggregation_percentiles_calculation():
    """Verify numpy percentiles (p10, p25, median p50, p75, p90, IQR, std dev, mean)."""
    observations = [
        {"asking_price": 500000, "analytical_eligibility": True},
        {"asking_price": 550000, "analytical_eligibility": True},
        {"asking_price": 600000, "analytical_eligibility": True},
        {"asking_price": 650000, "analytical_eligibility": True},
        {"asking_price": 700000, "analytical_eligibility": True},
    ]
    dist = CurrentMarketAggregationEngine.calculate_price_distribution(observations, "test-car")
    assert dist is not None
    assert dist.sample_size == 5
    assert dist.min_price_inr == 500000
    assert dist.max_price_inr == 700000
    assert dist.median_price_inr == 600000
    assert dist.iqr_inr == (dist.p75_price_inr - dist.p25_price_inr)
    assert dist.mean_price_inr == 600000


def test_aggregation_sparse_observations_handling():
    """Verify that fewer than 2 eligible observations returns None."""
    sparse_obs = [
        {"asking_price": 500000, "analytical_eligibility": True},
    ]
    dist = CurrentMarketAggregationEngine.calculate_price_distribution(sparse_obs, "test-car")
    assert dist is None


def test_aggregation_supply_and_regional_breakdown():
    """Verify supply metrics and regional share calculations."""
    observations = [
        {
            "canonical_vehicle_id": "test-car",
            "asking_price": 600000,
            "listing_status": "ACTIVE",
            "seller_type": "INDIVIDUAL",
            "location_city": "Delhi NCR",
            "location_region": "North",
            "freshness_state": "CURRENT",
            "analytical_eligibility": True,
            "duplicate_status": "DISTINCT",
            "is_outlier": False,
        },
        {
            "canonical_vehicle_id": "test-car",
            "asking_price": 650000,
            "listing_status": "ACTIVE",
            "seller_type": "CERTIFIED_DEALER",
            "location_city": "Delhi NCR",
            "location_region": "North",
            "freshness_state": "CURRENT",
            "analytical_eligibility": True,
            "duplicate_status": "DISTINCT",
            "is_outlier": False,
        },
        {
            "canonical_vehicle_id": "test-car",
            "asking_price": 700000,
            "listing_status": "ACTIVE",
            "seller_type": "INDIVIDUAL",
            "location_city": "Mumbai",
            "location_region": "West",
            "freshness_state": "AGING",
            "analytical_eligibility": True,
            "duplicate_status": "DISTINCT",
            "is_outlier": False,
        },
    ]
    supply = CurrentMarketAggregationEngine.calculate_supply(observations, "test-car")
    assert supply.total_observation_count == 3
    assert supply.usable_observation_count == 3
    assert supply.regional_supply.get("North") == 2
    assert supply.regional_supply.get("West") == 1
    assert supply.seller_distribution.get("INDIVIDUAL") == 2
    assert supply.seller_distribution.get("CERTIFIED_DEALER") == 1

    regional = CurrentMarketAggregationEngine.calculate_regional(observations)
    assert len(regional) == 2
    delhi = next(r for r in regional if r.region_name == "North")
    assert delhi.observation_count == 2
    assert delhi.median_asking_price_inr == 625000


# =========================================================================
# 5. SECURITY & SSRF PROTECTION
# =========================================================================

def test_security_ssrf_validator():
    """Verify rejection of private IPs, metadata IP, localhost, and non-HTTP schemes."""
    validator = MarketSecurityValidator

    # Valid external HTTP/HTTPS URLs
    assert validator.is_safe_url("https://www.cars24.com/buy-used-car/123") is True
    assert validator.is_safe_url("http://spinny.com/listing/456") is True

    # Rejection of loopback
    assert validator.is_safe_url("http://127.0.0.1:8000/listing") is False
    assert validator.is_safe_url("http://localhost:3000/api") is False

    # Rejection of AWS/GCP cloud metadata IP
    assert validator.is_safe_url("http://169.254.169.254/latest/meta-data/") is False

    # Rejection of RFC1918 private subnets
    assert validator.is_safe_url("http://10.0.0.5/admin") is False
    assert validator.is_safe_url("http://172.16.0.1:8080/data") is False
    assert validator.is_safe_url("http://192.168.1.100/feed") is False

    # Rejection of non-HTTP schemes
    assert validator.is_safe_url("file:///etc/passwd") is False
    assert validator.is_safe_url("ftp://internal-server/data") is False


def test_security_pii_sanitization():
    """Verify Indian phone numbers and email addresses are securely redacted."""
    text_with_phone = "Contact Rajesh at 9876543210 for price negotiations."
    clean_text = MarketSecurityValidator.sanitize_text(text_with_phone)
    assert "9876543210" not in clean_text
    assert "[REDACTED_PHONE]" in clean_text

    text_with_email = "Dealer inquiry: send details to dealer.support@auto-classifieds.in"
    clean_email = MarketSecurityValidator.sanitize_text(text_with_email)
    assert "dealer.support@auto-classifieds.in" not in clean_email
    assert "[REDACTED_EMAIL]" in clean_email


# =========================================================================
# 6. EPISTEMIC HONESTY & SEMANTIC INVARIANTS
# =========================================================================

def test_semantic_invariants_zero_fabrication(live_market_service):
    """
    CRITICAL INVARIANTS:
    - TRANSACTION-PRICE FABRICATION = 0
    - REALIZED-RESALE FABRICATION = 0
    - OBSERVED-SELL-THROUGH FABRICATION = 0
    - HISTORICAL/CURRENT CONFUSION = 0
    """
    intel = live_market_service.get_current_market_intelligence("maruti-suzuki::swift")

    # Invariant: Observation period clearly says Current Market Observations
    assert "Current Market Observations" in intel.observation_period

    # Invariant: Disclaimers explicitly declare asking prices, not transaction prices
    all_text = " ".join(intel.limitations)
    assert "transaction prices" in all_text.lower() or "active seller asking prices" in all_text.lower()
    assert "realized sale prices" in all_text.lower() or "not represent realized" in all_text.lower()

    # Never fabricate units sold or sell-through
    assert "units sold:" not in all_text.lower()
    assert "verified sell-through:" not in all_text.lower()

    # Explicit 4-Way Semantic Distinction Invariant:
    # Historical asking-price observations != Current asking-price observations != Transaction prices != Realized resale prices
    assert intel.observation_period != "2018-2024 Historical Baseline"
    assert "Current" in intel.observation_period
    assert intel.price_distribution is not None

    # Historical vs Current asking prices are distinct datasets
    comp = CurrentMarketAggregationEngine.compare_with_historical(
        canonical_vehicle_id="maruti-suzuki::swift",
        current_distribution=intel.price_distribution,
        historical_sample_size=3240,
        historical_median_price=585000.0,
    )
    assert comp is not None
    assert comp.historical_sample_size == 3240
    assert comp.current_sample_size == intel.price_distribution.sample_size
    assert comp.historical_sample_size != comp.current_sample_size

    # Current asking price is strictly secondary listing asking price, never transaction clearing price
    assert "asking-price" in intel.price_distribution.semantics.lower()
    assert "not realized transaction" in intel.price_distribution.semantics.lower()
    assert any("not represent realized" in l.lower() or "seller asking prices" in l.lower() for l in intel.limitations)
    assert "neither represents verified dealer transaction clearing prices" in comp.semantics_clarification.lower()


def test_valuation_artifact_sha256_immutability():
    """Verify Phase 3 Valuation Model Artifact SHA-256 remains strictly untouched."""
    artifact_path = os.path.join(
        os.path.dirname(__file__), "../../models/carspective_valuation_lgbm_v1.joblib"
    )
    artifact_path = os.path.abspath(artifact_path)
    assert os.path.exists(artifact_path), f"Valuation artifact not found at {artifact_path}"

    with open(artifact_path, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()

    assert actual_hash == EXPECTED_MODEL_SHA256, (
        f"CRITICAL VIOLATION: Valuation model artifact SHA-256 altered!\n"
        f"Expected: {EXPECTED_MODEL_SHA256}\n"
        f"Actual:   {actual_hash}"
    )


# =========================================================================
# 7. SERVICE PERSISTENCE & QUERY RETRIEVAL
# =========================================================================

def test_service_queries_on_ingested_data(live_market_service):
    """Verify MarketIntelligenceService retrieval of ingested current market data."""
    # Test Swift
    swift_id = "maruti-suzuki::swift"
    dist = live_market_service.get_current_price_distribution(swift_id)
    assert dist is not None
    assert dist.sample_size >= 5
    assert dist.median_price_inr > 0

    supply = live_market_service.get_current_supply(swift_id)
    assert supply.total_observation_count >= 5
    assert supply.supply_tier in (CurrentSupplyTier.STRONG_CURRENT_SUPPLY, CurrentSupplyTier.MODERATE_CURRENT_SUPPLY, CurrentSupplyTier.LIMITED_CURRENT_SUPPLY)

    regional = live_market_service.get_current_regional(swift_id)
    assert len(regional) >= 2

    evidence = live_market_service.get_current_market_evidence(swift_id)
    assert evidence.total_observations >= 5
    assert evidence.usable_observations > 0
    assert evidence.evidence_state == "EMPIRICAL"


# =========================================================================
# 8. REST API ENDPOINTS
# =========================================================================

def test_admin_ingest_endpoint_auth_and_execution(app_client):
    """Verify POST /api/v1/market/admin/ingest authorization and execution."""
    # 1. Unauthenticated request -> 401
    res_unauth = app_client.post("/api/v1/market/admin/ingest", json={})
    assert res_unauth.status_code == 401
    assert res_unauth.get_json()["status"] == 401

    # 2. Authenticated request with default test fixtures -> 201
    headers = {"X-Admin-Api-Key": getattr(settings, "ADMIN_API_KEY", "carspective-admin-phase17-key")}
    res_auth = app_client.post("/api/v1/market/admin/ingest", headers=headers, json={})
    assert res_auth.status_code == 201
    data = res_auth.get_json()
    assert "batch_id" in data
    assert data["records_received"] >= 20
    assert data["accepted_count"] > 0


def test_get_current_market_api_endpoints(app_client):
    """Verify GET endpoints for current market intelligence."""
    vehicle_id = "maruti-suzuki::swift"

    # Full current intelligence
    res_full = app_client.get(f"/api/v1/market/current/{vehicle_id}")
    assert res_full.status_code == 200
    data_full = res_full.get_json()
    assert "price_distribution" in data_full
    assert "supply" in data_full
    assert "regional_breakdown" in data_full

    # Distribution endpoint
    res_dist = app_client.get(f"/api/v1/market/current/{vehicle_id}/distribution")
    assert res_dist.status_code == 200
    assert res_dist.get_json()["median_price_inr"] > 0

    # Supply endpoint
    res_supply = app_client.get(f"/api/v1/market/current/{vehicle_id}/supply")
    assert res_supply.status_code == 200
    assert res_supply.get_json()["total_observation_count"] > 0

    # Regional endpoint
    res_reg = app_client.get(f"/api/v1/market/current/{vehicle_id}/regional")
    assert res_reg.status_code == 200
    assert len(res_reg.get_json()) > 0

    # Evidence endpoint
    res_ev = app_client.get(f"/api/v1/market/current/{vehicle_id}/evidence")
    assert res_ev.status_code == 200
    assert res_ev.get_json()["evidence_state"] == "EMPIRICAL"


# =========================================================================
# 9. ASSISTANT & WORKSPACE INTEGRATION
# =========================================================================

def test_assistant_tool_dispatcher_integration(live_market_service):
    """Verify DomainToolDispatcher.fetch_current_market_intelligence adds empirical evidence."""
    dispatcher = DomainToolDispatcher()
    bundle = EvidenceBundle()
    v = VehicleContextInput(brand="Maruti", model="Swift", manufacturing_year=2021)

    result = dispatcher.fetch_current_market_intelligence(v, bundle)
    assert result is not None
    assert len(bundle.items) >= 1

    dist_item = next((item for item in bundle.items if item.id == "current_market.distribution"), None)
    if dist_item:
        assert dist_item.evidence_state == AssistantEvidenceState.EMPIRICAL
        assert dist_item.domain == SourceDomain.VALUATION
        assert "Current Market Asking Price (2026-Q3)" in dist_item.claim

    # Invariant: Assistant cannot answer a current-market question using historical observations while presenting them as current
    sparse_bundle = EvidenceBundle()
    v_sparse = VehicleContextInput(brand="Bugatti", model="Veyron", manufacturing_year=2015)
    dispatcher.fetch_current_market_intelligence(v_sparse, sparse_bundle)
    sparse_dist_item = next((item for item in sparse_bundle.items if item.id == "current_market.distribution"), None)
    assert sparse_dist_item is None, "Assistant must NOT create current_market.distribution for vehicle with no current observations"
    assert any("Insufficient current market observations" in d for d in sparse_bundle.uncertainty_disclosures)
    # Must never present historical observations as current
    for item in sparse_bundle.items:
        assert "current_market" not in item.id


def test_workspace_service_includes_current_market():
    """Verify VehicleWorkspaceService populates current_market in VehicleWorkspaceResponse."""
    svc = VehicleWorkspaceService()
    can_id = "maruti-suzuki::swift::gen-3-2018::2021::zxi::1-2-k12m-5mt"
    ws = svc.get_vehicle_workspace(can_id)
    assert ws is not None
    assert ws.current_market is not None
    assert "observation_period" in ws.current_market
    assert ws.current_market["supply"]["total_observation_count"] > 0


# =========================================================================
# 10. SCALABILITY BENCHMARK (10,000 SYNTHETIC OBSERVATIONS)
# =========================================================================

def test_scalability_benchmark_10000_records():
    """Verify vectorized aggregation executes across 10,000 records in < 2.0 seconds."""
    import random
    synthetic_obs = []
    base_price = 700000
    cities = ["Delhi NCR", "Mumbai", "Bengaluru", "Hyderabad", "Pune"]
    regions = ["North", "West", "South", "South", "West"]
    sellers = ["INDIVIDUAL", "CERTIFIED_DEALER", "INDEPENDENT_DEALER"]

    for i in range(10000):
        price = base_price + random.randint(-150000, 200000)
        c_idx = i % len(cities)
        synthetic_obs.append({
            "canonical_vehicle_id": "maruti-suzuki::swift",
            "asking_price": price,
            "listing_status": "ACTIVE",
            "seller_type": sellers[i % len(sellers)],
            "location_city": cities[c_idx],
            "location_region": regions[c_idx],
            "freshness_state": "CURRENT",
            "analytical_eligibility": True,
            "duplicate_status": "DISTINCT",
            "is_outlier": False,
        })

    t0 = time.perf_counter()
    dist = CurrentMarketAggregationEngine.calculate_price_distribution(synthetic_obs, "maruti-suzuki::swift")
    supply = CurrentMarketAggregationEngine.calculate_supply(synthetic_obs, "maruti-suzuki::swift")
    regional = CurrentMarketAggregationEngine.calculate_regional(synthetic_obs)
    comp = CurrentMarketAggregationEngine.compare_with_historical(
        canonical_vehicle_id="maruti-suzuki::swift",
        current_distribution=dist,
        historical_sample_size=3240,
        historical_median_price=585000.0,
    )
    t1 = time.perf_counter()
    latency_s = t1 - t0

    assert dist.sample_size == 10000
    assert supply.total_observation_count == 10000
    assert len(regional) == 3  # North, West, South
    assert comp is not None
    assert latency_s < 2.0, f"Aggregation latency exceeded 2.0s limit: {latency_s:.4f}s"
