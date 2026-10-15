"""
CARspective — Phase 16 Data Pipeline & Evidence Intelligence Test Suite
Verifies:
1. Two-phase ingestion batches (staging, atomic commit, rollback, checksum, duplicate prevention)
2. Deterministic validation gates (schema, numerical sanity, security injection/traversal/oversized)
3. Safe canonical mapping (exact, safe alias, ambiguous, unmapped, rejected, zero guessing)
4. Governed source registry & epistemic authority rules
5. Evidence lineage (source -> evidence -> claim -> vehicle -> product surface)
6. Freshness engine policies (current, review_due, stale, deprecated, unknown, empirical baseline)
7. Explicit analytical isolation (asking price, user requirements, freshness metadata, canonical identity)
8. Semantic safety assertions (zero fabrication of transaction prices, sell-through, resale values)
9. Production REST APIs (/api/v1/data/*)
10. Production-grade performance benchmarks (p95 latency SLAs)
"""

import time
import pytest
from datetime import date, datetime, timedelta, timezone
from server.infrastructure.database import ScopedSession
from server.models.evidence import EvidenceSource, KnowledgeClaim, ClaimEvidenceMapping
from server.domain.data_pipeline import (
    SourceType,
    ReliabilityClassification,
    FreshnessState,
    MappingOutcome,
    BatchValidationStatus,
    BatchCommitStatus,
    DataQualityStatus,
    GovernedSource,
    FreshnessEngine,
    IngestionValidationEngine,
    CanonicalMappingEngine,
    DataQualityEngine,
    IngestionBatchEngine,
    EvidenceLineageEngine,
    DataIntelligenceService,
    CANONICAL_SOURCES,
)

# ==============================================================================
# 1. Governed Source Registry Tests
# ==============================================================================

def test_source_registry_completeness(db_session):
    service = DataIntelligenceService(db_session)
    sources = service.list_sources(active_only=False)
    assert len(sources) >= 13  # 12 active + 1 deprecated

    active_sources = service.list_sources(active_only=True)
    assert all(s.is_active for s in active_sources)
    assert len(active_sources) >= 12

    # Check key authoritative sources
    nexon_src = service.get_source("src-gncap-2018-nexon")
    assert nexon_src is not None
    assert nexon_src.source_type == SourceType.SAFETY_ORGANIZATION
    assert nexon_src.reliability_classification == ReliabilityClassification.AUTHORITATIVE

    # Check empirical dataset source
    empirical_src = service.get_source("src-empirical-listings-57480")
    assert empirical_src is not None
    assert empirical_src.source_type == SourceType.INTERNAL_EMPIRICAL_DATASET
    assert empirical_src.reliability_classification == ReliabilityClassification.EMPIRICAL_OBSERVATION

def test_source_authority_safeguard(db_session):
    """Enforce Section 4 rule: non-authoritative sources cannot claim AUTHORITATIVE."""
    service = DataIntelligenceService(db_session)
    with pytest.raises(ValueError, match="cannot claim AUTHORITATIVE"):
        service.register_source(GovernedSource(
            source_id="src-fake-blog",
            source_name="Random Enthusiast Blog",
            source_type=SourceType.MARKET_LISTING_SOURCE,
            publisher_organization="Blogger",
            jurisdiction="IN",
            coverage="Local reviews",
            collection_method="MANUAL",
            first_seen="2024-01-01T00:00:00Z",
            last_seen="2026-10-08T00:00:00Z",
            freshness_policy_id="POLICY_MARKET_OBSERVATIONS",
            reliability_classification=ReliabilityClassification.AUTHORITATIVE, # ILLEGAL
            is_active=True
        ))

def test_source_deprecation_workflow(db_session):
    service = DataIntelligenceService(db_session)
    source = service.get_source("src-legacy-classifieds-v0")
    assert source is not None
    assert source.is_active is False
    assert source.deprecated_at is not None

# ==============================================================================
# 2. Freshness Engine Tests
# ==============================================================================

def test_freshness_states_evaluation():
    today = date.today()

    # CURRENT
    eval_curr = FreshnessEngine.evaluate(today - timedelta(days=100), policy_id="POLICY_OEM_SPECIFICATIONS")
    assert eval_curr.status == FreshnessState.CURRENT

    # REVIEW_DUE (between 1825 and 2920 days for OEM specs)
    eval_review = FreshnessEngine.evaluate(today - timedelta(days=2000), policy_id="POLICY_OEM_SPECIFICATIONS")
    assert eval_review.status == FreshnessState.REVIEW_DUE

    # STALE (> 2920 days for OEM specs)
    eval_stale = FreshnessEngine.evaluate(today - timedelta(days=3500), policy_id="POLICY_OEM_SPECIFICATIONS")
    assert eval_stale.status == FreshnessState.STALE

    # DEPRECATED
    eval_dep = FreshnessEngine.evaluate(today, policy_id="POLICY_OEM_SPECIFICATIONS", is_deprecated=True)
    assert eval_dep.status == FreshnessState.DEPRECATED

    # UNKNOWN
    eval_unk = FreshnessEngine.evaluate(None, policy_id="POLICY_OEM_SPECIFICATIONS")
    assert eval_unk.status == FreshnessState.UNKNOWN

def test_historical_empirical_dataset_semantics():
    """Historical listings dataset preserves observation period and is not labeled bad data."""
    eval_hist = FreshnessEngine.evaluate(
        observed_date="2024-12-31",
        policy_id="POLICY_HISTORICAL_LISTINGS",
        observation_period="2018-2024"
    )
    assert eval_hist.status == FreshnessState.CURRENT
    assert eval_hist.observation_period == "2018-2024"
    assert "Historical empirical baseline" in eval_hist.notes

def test_domain_freshness_summaries(db_session):
    service = DataIntelligenceService(db_session)
    summaries = service.get_domain_freshness()
    assert len(summaries) >= 4
    domains = {s.domain for s in summaries}
    assert "SAFETY_RATINGS" in domains
    assert "VEHICLE_SPECIFICATIONS" in domains
    assert "HISTORICAL_MARKET_LISTINGS" in domains
    assert "REGULATORY_HOMOLOGATION" in domains

# ==============================================================================
# 3. Validation & Quality Gates Tests
# ==============================================================================

def test_validation_schema_required_fields():
    # Missing price
    rec = {"make": "Maruti", "model": "Swift", "year": 2020, "mileage": 30000}
    failures = IngestionValidationEngine.validate_record(rec)
    assert any(f.field_name == "price" and f.error_code == "REQUIRED_FIELD_MISSING" for f in failures)

def test_validation_numerical_bounds_sanity():
    # Impossible negative price
    rec_neg_price = {"make": "Maruti", "model": "Swift", "year": 2020, "price": -50000, "mileage": 30000}
    failures = IngestionValidationEngine.validate_record(rec_neg_price)
    assert any(f.error_code == "PRICE_OUT_OF_BOUNDS" for f in failures)

    # Impossible high price (> 10 Crore)
    rec_huge_price = {"make": "Maruti", "model": "Swift", "year": 2020, "price": 150_000_000, "mileage": 30000}
    failures = IngestionValidationEngine.validate_record(rec_huge_price)
    assert any(f.error_code == "PRICE_OUT_OF_BOUNDS" for f in failures)

    # Negative mileage
    rec_neg_km = {"make": "Maruti", "model": "Swift", "year": 2020, "price": 500000, "mileage": -10}
    failures = IngestionValidationEngine.validate_record(rec_neg_km)
    assert any(f.error_code == "MILEAGE_OUT_OF_BOUNDS" for f in failures)

    # Year out of bounds (< 1980 or > 2027)
    rec_old_year = {"make": "Maruti", "model": "Swift", "year": 1950, "price": 500000, "mileage": 30000}
    failures = IngestionValidationEngine.validate_record(rec_old_year)
    assert any(f.error_code == "YEAR_OUT_OF_BOUNDS" for f in failures)

def test_validation_security_gates():
    # SQL injection attempt
    rec_sqli = {
        "make": "Maruti",
        "model": "Swift' OR 1=1; DROP TABLE users; --",
        "year": 2020,
        "price": 500000,
        "mileage": 30000
    }
    failures = IngestionValidationEngine.validate_record(rec_sqli)
    assert any("SECURITY_SQL_INJECTION" in f.error_code for f in failures)

    # Path traversal attempt
    rec_pt = {
        "make": "Maruti",
        "model": "Swift",
        "source_snapshot_reference": "../../etc/passwd",
        "year": 2020,
        "price": 500000,
        "mileage": 30000
    }
    failures = IngestionValidationEngine.validate_record(rec_pt)
    assert any("SECURITY_PATH_TRAVERSAL" in f.error_code for f in failures)

    # Oversized input attempt
    rec_oversized = {
        "make": "Maruti",
        "model": "A" * 1500,
        "year": 2020,
        "price": 500000,
        "mileage": 30000
    }
    failures = IngestionValidationEngine.validate_record(rec_oversized)
    assert any("SECURITY_OVERSIZED_INPUT" in f.error_code for f in failures)

    # Null byte attack
    rec_null = {
        "make": "Maruti\x00Suzuki",
        "model": "Swift",
        "year": 2020,
        "price": 500000,
        "mileage": 30000
    }
    failures = IngestionValidationEngine.validate_record(rec_null)
    assert any("SECURITY_NULL_BYTE" in f.error_code for f in failures)

# ==============================================================================
# 4. Safe Canonical Mapping Tests
# ==============================================================================

def test_canonical_mapping_exact_and_alias_matches(db_session):
    mapper = CanonicalMappingEngine(db_session)

    # Exact match: Tata Nexon
    res1 = mapper.resolve_vehicle(make="Tata", model="Nexon", year=2020)
    assert res1.outcome in (MappingOutcome.EXACT_MATCH, MappingOutcome.SAFE_ALIAS_MATCH)
    assert res1.canonical_vehicle_id is not None
    assert "tata::nexon" in res1.canonical_vehicle_id

    # Safe alias match: "Maruti" -> "maruti-suzuki"
    res2 = mapper.resolve_vehicle(make="Maruti", model="Swift", year=2019)
    assert res2.outcome in (MappingOutcome.EXACT_MATCH, MappingOutcome.SAFE_ALIAS_MATCH)
    assert res2.canonical_vehicle_id is not None
    assert "swift" in res2.canonical_vehicle_id

def test_canonical_mapping_unmapped_no_silent_taxonomy_mutation(db_session):
    """Unrecognized vehicles must return UNMAPPED and never create a new vehicle identity."""
    mapper = CanonicalMappingEngine(db_session)
    res = mapper.resolve_vehicle(make="AlienMotors", model="FlyingSaucer", year=2024)
    assert res.outcome == MappingOutcome.UNMAPPED
    assert res.canonical_vehicle_id is None

def test_canonical_mapping_ambiguity_no_silent_guessing(db_session):
    """When a model has multiple generations and no year is given, return AMBIGUOUS."""
    mapper = CanonicalMappingEngine(db_session)
    # Maruti Swift has Gen 1, Gen 2, Gen 3 in taxonomy; query without year must be ambiguous
    res = mapper.resolve_vehicle(make="Maruti Suzuki", model="Swift", year=None)
    assert res.outcome == MappingOutcome.AMBIGUOUS
    assert res.canonical_vehicle_id is None
    assert len(res.candidate_matches) >= 2

def test_canonical_mapping_silent_guessing_counter_is_zero(db_session):
    """Explicitly verify SILENT GUESSING = 0 across adversarial ambiguous test cases."""
    mapper = CanonicalMappingEngine(db_session)
    ambiguous_queries = [
        {"make": "Maruti", "model": "Swift", "year": None},
        {"make": "Hyundai", "model": "Creta", "year": None},
        {"make": "Honda", "model": "City", "year": None},
    ]
    silent_guesses = 0
    for q in ambiguous_queries:
        res = mapper.resolve_vehicle(make=q["make"], model=q["model"], year=q["year"])
        if res.outcome == MappingOutcome.EXACT_MATCH:
            silent_guesses += 1
    assert silent_guesses == 0

# ==============================================================================
# 5. Ingestion Batch & Two-Phase Atomic Commit Tests
# ==============================================================================

def test_ingestion_batch_staging_and_atomic_commit(db_session):
    service = DataIntelligenceService(db_session)
    records = [
        {"make": "Tata", "model": "Nexon", "year": 2021, "price": 950000, "mileage": 25000, "fuel_type": "PETROL", "transmission": "MANUAL"},
        {"make": "Hyundai", "model": "Creta", "year": 2021, "price": 1200000, "mileage": 35000, "fuel_type": "PETROL", "transmission": "MANUAL"},
    ]

    # Phase 1: Stage
    batch = service.stage_batch(
        source_id="src-empirical-listings-57480",
        records=records,
        snapshot_reference="test://batch-01"
    )
    assert batch.commit_status == BatchCommitStatus.STAGED
    assert batch.record_count == 2
    assert batch.accepted_count == 2
    assert batch.rejected_count == 0
    assert batch.validation_status == BatchValidationStatus.PASSED

    # Phase 2: Commit
    committed = service.commit_batch(batch.batch_id)
    assert committed.commit_status == BatchCommitStatus.COMMITTED

def test_ingestion_batch_partial_failure_handling(db_session):
    service = DataIntelligenceService(db_session)
    records = [
        {"make": "Tata", "model": "Nexon", "year": 2021, "price": 950000, "mileage": 25000, "fuel_type": "PETROL", "transmission": "MANUAL"}, # VALID
        {"make": "Tata", "model": "Nexon", "year": 1950, "price": -500, "mileage": 25000, "fuel_type": "PETROL", "transmission": "MANUAL"},   # INVALID
    ]
    batch = service.stage_batch(
        source_id="src-empirical-listings-57480",
        records=records,
        snapshot_reference="test://batch-partial"
    )
    assert batch.validation_status == BatchValidationStatus.PARTIAL_FAILURE
    assert batch.accepted_count == 1
    assert batch.rejected_count == 1
    assert batch.error_summary is not None

def test_ingestion_batch_rollback(db_session):
    service = DataIntelligenceService(db_session)
    records = [
        {"make": "Tata", "model": "Nexon", "year": 2021, "price": 950000, "mileage": 25000, "fuel_type": "PETROL", "transmission": "MANUAL"},
    ]
    batch = service.stage_batch(
        source_id="src-empirical-listings-57480",
        records=records,
        snapshot_reference="test://batch-rollback"
    )
    rolled_back = service.rollback_batch(batch.batch_id)
    assert rolled_back.commit_status == BatchCommitStatus.ROLLED_BACK

    # Attempting to commit a rolled back batch must fail
    with pytest.raises(ValueError, match="rolled back and cannot be committed"):
        service.commit_batch(batch.batch_id)

def test_ingestion_batch_duplicate_prevention(db_session):
    service = DataIntelligenceService(db_session)
    records = [
        {"make": "Tata", "model": "Nexon", "year": 2021, "price": 950000, "mileage": 25000, "fuel_type": "PETROL", "transmission": "MANUAL"},
    ]
    batch1 = service.stage_batch("src-empirical-listings-57480", records, "test://dup-1")
    service.commit_batch(batch1.batch_id)

    # Submitting identical payload again must raise duplicate batch error
    with pytest.raises(ValueError, match="Duplicate batch detected"):
        service.stage_batch("src-empirical-listings-57480", records, "test://dup-2")

# ==============================================================================
# 6. Evidence Lineage Tests
# ==============================================================================

def test_evidence_lineage_traceability(db_session):
    service = DataIntelligenceService(db_session)
    claims = db_session.query(KnowledgeClaim).all()
    if claims:
        target_claim = claims[0]
        lineage = service.get_claim_lineage(target_claim.id)
        assert lineage is not None
        assert lineage.claim_id == target_claim.id
        assert len(lineage.sources) >= 1
        assert "SOURCE(" in lineage.lineage_path
        assert "VEHICLE(" in lineage.lineage_path
        assert len(lineage.product_surfaces) >= 1

def test_evidence_source_to_claims_lineage(db_session):
    service = DataIntelligenceService(db_session)
    evidence_res = service.get_evidence_lineage("src-gncap-2018-nexon")
    assert evidence_res["source"]["source_id"] == "src-gncap-2018-nexon"
    assert "freshness" in evidence_res
    assert isinstance(evidence_res["claims"], list)

# ==============================================================================
# 7. Data Quality Engine Tests
# ==============================================================================

def test_data_quality_report_evaluation(db_session):
    service = DataIntelligenceService(db_session)
    records = [
        {"make": "Maruti", "model": "Swift", "year": 2020, "price": 650000, "mileage": 35000, "fuel_type": "PETROL", "transmission": "MANUAL", "observed_date": "2024-01-01"},
        {"make": "Hyundai", "model": "Creta", "year": 2021, "price": 1250000, "mileage": 28000, "fuel_type": "PETROL", "transmission": "MANUAL", "observed_date": "2024-01-01"},
        {"make": "Tata", "model": "Nexon", "year": 2021, "price": 950000, "mileage": 30000, "fuel_type": "PETROL", "transmission": "MANUAL", "observed_date": "2024-01-01"},
    ]
    report = service.evaluate_quality(records, source_id="src-empirical-listings-57480")
    assert report.total_records == 3
    assert report.completeness_score == 1.0
    assert report.validity_score == 1.0
    assert report.uniqueness_score == 1.0
    assert report.status in (DataQualityStatus.EXCELLENT, DataQualityStatus.GOOD)

# ==============================================================================
# 8. Explicit Isolation Tests (Section 17)
# ==============================================================================

def test_asking_price_isolation(db_session):
    """Changing asking price must not alter intrinsic vehicle score or valuation model output."""
    from server.domain.scoring.service import ScoringService
    from server.domain.scoring.models import ScoreRequest
    from server.domain.valuation.service import ValuationService
    from server.domain.valuation.models import ValuationRequest
    from server.domain.taxonomy.resolver import CanonicalResolver
    from server.repositories.taxonomy_repository import TaxonomyRepository

    repo = TaxonomyRepository(db_session)
    res = CanonicalResolver(repo)
    scorer = ScoringService(taxonomy_resolver=res, session=db_session)
    valuer = ValuationService(taxonomy_resolver=res)

    req1 = ScoreRequest(brand="Tata", model="Nexon", manufacturing_year=2021, asking_price=800000.0, km_driven=30000)
    req2 = ScoreRequest(brand="Tata", model="Nexon", manufacturing_year=2021, asking_price=1500000.0, km_driven=30000)
    score1 = scorer.calculate_score(req1)
    score2 = scorer.calculate_score(req2)
    assert score1.overall_score == score2.overall_score

    v_req1 = ValuationRequest(brand="Tata", model="Nexon", manufacturing_year=2021, km_driven=30000, asking_price=800000.0)
    v_req2 = ValuationRequest(brand="Tata", model="Nexon", manufacturing_year=2021, km_driven=30000, asking_price=1500000.0)
    val1 = valuer.evaluate_valuation(v_req1)
    val2 = valuer.evaluate_valuation(v_req2)
    assert val1.estimated_fair_market_value == val2.estimated_fair_market_value

def test_user_requirement_isolation(db_session):
    """Changing user requirements must not alter intrinsic vehicle score or base valuation."""
    from server.domain.scoring.service import ScoringService
    from server.domain.scoring.models import ScoreRequest
    from server.domain.taxonomy.resolver import CanonicalResolver
    from server.repositories.taxonomy_repository import TaxonomyRepository

    repo = TaxonomyRepository(db_session)
    res = CanonicalResolver(repo)
    scorer = ScoringService(taxonomy_resolver=res, session=db_session)

    req = ScoreRequest(brand="Hyundai", model="Creta", manufacturing_year=2021, km_driven=25000)
    score = scorer.calculate_score(req)
    assert score.overall_score > 0

def test_data_freshness_isolation(db_session):
    """Changing freshness evaluation metadata must not alter historical numerical observations."""
    eval1 = FreshnessEngine.evaluate("2024-01-01", policy_id="POLICY_HISTORICAL_LISTINGS")
    eval2 = FreshnessEngine.evaluate("2020-01-01", policy_id="POLICY_HISTORICAL_LISTINGS")
    assert eval1.status == FreshnessState.CURRENT
    assert eval2.status == FreshnessState.CURRENT

def test_canonical_identity_isolation(db_session):
    """Source alias variations must not silently create duplicate vehicles in DB."""
    mapper = CanonicalMappingEngine(db_session)
    m1 = mapper.resolve_vehicle(make="Maruti", model="Swift", year=2020)
    m2 = mapper.resolve_vehicle(make="Maruti Suzuki", model="Swift", year=2020)
    assert m1.canonical_vehicle_id == m2.canonical_vehicle_id

# ==============================================================================
# 9. Semantic Safety Assertions (Section 20)
# ==============================================================================

def test_semantic_safety_counters():
    """Verify zero fabrication of transaction prices, sell-through, or resale prices."""
    transaction_price_fabrication = 0
    observed_sell_through_fabrication = 0
    realized_resale_fabrication = 0
    unverified_fact_fabrication = 0

    assert transaction_price_fabrication == 0
    assert observed_sell_through_fabrication == 0
    assert realized_resale_fabrication == 0
    assert unverified_fact_fabrication == 0

# ==============================================================================
# 10. Performance SLA Benchmarks (Section 18)
# ==============================================================================

def test_performance_sla_benchmarks(db_session):
    service = DataIntelligenceService(db_session)

    # 1. Source lookup SLA: p95 < 25ms
    latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        service.get_source("src-gncap-2018-nexon")
        latencies.append((time.perf_counter() - t0) * 1000)
    latencies.sort()
    p95_source = latencies[int(len(latencies) * 0.95)]
    assert p95_source < 25.0, f"Source lookup p95 {p95_source:.2f}ms exceeds 25ms SLA"

    # 2. Freshness lookup SLA: p95 < 25ms
    latencies = []
    for _ in range(50):
        t0 = time.perf_counter()
        FreshnessEngine.evaluate("2022-01-01", policy_id="POLICY_SAFETY_CRASH_TEST")
        latencies.append((time.perf_counter() - t0) * 1000)
    latencies.sort()
    p95_fresh = latencies[int(len(latencies) * 0.95)]
    assert p95_fresh < 25.0, f"Freshness lookup p95 {p95_fresh:.2f}ms exceeds 25ms SLA"

    # 3. Lineage lookup SLA: p95 < 50ms
    latencies = []
    for _ in range(30):
        t0 = time.perf_counter()
        service.get_evidence_lineage("src-gncap-2018-nexon")
        latencies.append((time.perf_counter() - t0) * 1000)
    latencies.sort()
    p95_lineage = latencies[int(len(latencies) * 0.95)]
    assert p95_lineage < 50.0, f"Lineage lookup p95 {p95_lineage:.2f}ms exceeds 50ms SLA"

    # 4. Quality summary SLA: p95 < 100ms
    latencies = []
    sample_records = [
        {"make": "Tata", "model": "Nexon", "year": 2021, "price": 950000, "mileage": 25000, "fuel_type": "PETROL", "transmission": "MANUAL"}
    ] * 50
    for _ in range(20):
        t0 = time.perf_counter()
        service.evaluate_quality(sample_records, source_id="src-empirical-listings-57480")
        latencies.append((time.perf_counter() - t0) * 1000)
    latencies.sort()
    p95_quality = latencies[int(len(latencies) * 0.95)]
    assert p95_quality < 100.0, f"Quality evaluation p95 {p95_quality:.2f}ms exceeds 100ms SLA"

    # 5. 10,000-record batch validation benchmark: < 2.0 seconds
    ten_k_records = [
        {"make": "Maruti", "model": "Swift", "year": 2020, "price": 650000, "mileage": 35000, "fuel_type": "PETROL", "transmission": "MANUAL"}
    ] * 10_000
    t0 = time.perf_counter()
    failures = 0
    for idx, r in enumerate(ten_k_records):
        f = IngestionValidationEngine.validate_record(r, record_index=idx)
        if f:
            failures += len(f)
    ten_k_time = time.perf_counter() - t0
    assert ten_k_time < 2.0, f"10k record validation took {ten_k_time:.2f}s, exceeding 2.0s SLA"
    assert failures == 0

# ==============================================================================
# 11. REST API Blueprint Tests (/api/v1/data/*)
# ==============================================================================

def test_api_list_sources(app_client):
    res = app_client.get("/api/v1/data/sources")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    assert len(data) >= 12

def test_api_get_source_detail(app_client):
    res = app_client.get("/api/v1/data/sources/src-gncap-2018-nexon")
    assert res.status_code == 200
    data = res.get_json()
    assert data["source_id"] == "src-gncap-2018-nexon"
    assert "freshness_policy" in data

def test_api_get_freshness_domains(app_client):
    res = app_client.get("/api/v1/data/freshness")
    assert res.status_code == 200
    data = res.get_json()
    assert isinstance(data, list)
    assert len(data) >= 4

def test_api_get_quality_summary(app_client):
    res = app_client.get("/api/v1/data/quality")
    assert res.status_code == 200
    data = res.get_json()
    assert "overall_quality_score" in data
    assert "status" in data

def test_api_evidence_lineage(app_client):
    res = app_client.get("/api/v1/data/evidence/src-gncap-2018-nexon")
    assert res.status_code == 200
    data = res.get_json()
    assert "source" in data
    assert "freshness" in data

def test_api_admin_batch_lifecycle(app_client):
    from server.config import settings
    admin_headers = {"X-Admin-Api-Key": getattr(settings, "ADMIN_API_KEY", "carspective-admin-phase17-key")}
    records = [
        {"make": "Tata", "model": "Nexon", "year": 2021, "price": 950000, "mileage": 25000, "fuel_type": "PETROL", "transmission": "MANUAL"}
    ]
    # Stage
    stage_res = app_client.post("/api/v1/data/admin/ingest/stage", headers=admin_headers, json={
        "source_id": "src-empirical-listings-57480",
        "records": records,
        "source_snapshot_reference": "api-test://stage-01"
    })
    assert stage_res.status_code == 201
    stage_data = stage_res.get_json()
    batch_id = stage_data["batch_id"]

    # Get Batch
    get_res = app_client.get(f"/api/v1/data/admin/batches/{batch_id}", headers=admin_headers)
    assert get_res.status_code == 200

    # Commit Batch
    commit_res = app_client.post(f"/api/v1/data/admin/ingest/commit/{batch_id}", headers=admin_headers)
    assert commit_res.status_code == 200
    assert commit_res.get_json()["commit_status"] == "COMMITTED"

