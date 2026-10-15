"""
CARspective — Phase 14 Market Intelligence Test Suite
Verifies secondary supply, liquidity rating, depreciation curve gating,
segment benchmarks, and REST API performance SLAs.
"""

import hashlib
from pathlib import Path
import pytest
from server.app import create_app
from server.domain.market.service import MarketIntelligenceService
from server.domain.market.models import (
    VehicleMarketProfile,
    MarketLiquidityIndicator,
    MarketSupplyIndicator,
    EvidenceState,
    DepreciationProfile,
    SegmentBenchmark,
)

EXPECTED_VALUATION_MODEL_SHA256 = "4a4ccf3f78c17b48826cfa55f40a24bcb808bc82fa752b793ad4eabff8b246c1"


@pytest.fixture
def market_service():
    return MarketIntelligenceService()


@pytest.fixture
def client():
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


def test_valuation_model_artifact_unmodified():
    """Verify that Phase 3 production model artifact hash is intact."""
    model_path = Path("models/carspective_valuation_lgbm_v1.joblib")
    assert model_path.exists(), "Valuation model artifact missing"
    with open(model_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    assert file_hash == EXPECTED_VALUATION_MODEL_SHA256, (
        f"Model hash mismatch! Expected {EXPECTED_VALUATION_MODEL_SHA256}, got {file_hash}"
    )


def test_market_cache_load_and_performance(market_service):
    """Verify cache is loaded and query performance is sub-5ms."""
    import time
    t0 = time.perf_counter()
    profile = market_service.get_market_profile("maruti-suzuki::swift")
    t1 = time.perf_counter()
    query_latency_ms = (t1 - t0) * 1000.0

    assert isinstance(profile, VehicleMarketProfile)
    assert query_latency_ms < 5.0, f"Query took {query_latency_ms:.2f}ms, SLA is < 5ms"


def test_market_profile_tier1_core_model(market_service):
    """Verify market profile generation for a high-volume Tier 1 vehicle."""
    profile = market_service.get_market_profile("hyundai::creta")
    assert profile.canonical_vehicle_id == "hyundai::creta"
    assert profile.listing_count >= 200
    assert profile.relative_supply in (MarketSupplyIndicator.HIGH, MarketSupplyIndicator.MODERATE)
    assert profile.liquidity_indicator in (MarketLiquidityIndicator.HIGH_LIQUIDITY, MarketLiquidityIndicator.MODERATE_LIQUIDITY)
    assert profile.market_position_summary is not None
    assert profile.evidence_state == EvidenceState.EMPIRICAL


def test_depreciation_curve_sample_gating(market_service):
    """Verify depreciation curve only includes points with sufficient empirical samples."""
    profile = market_service.get_depreciation_profile("honda::city")
    assert isinstance(profile, DepreciationProfile)
    curve = profile.points
    assert len(curve) > 0, "Depreciation curve should contain data points"

    for pt in curve:
        assert pt.sample_size >= 5, f"Point age {pt.age_years} has < 5 samples: {pt.sample_size}"
        if pt.sample_size >= 15:
            assert pt.is_statistically_robust is True
        else:
            assert pt.is_statistically_robust is False


def test_insufficient_data_handling(market_service):
    """Verify low-sample or unknown vehicles are gracefully handled with INSUFFICIENT_DATA."""
    profile = market_service.get_market_profile("rolls-royce::phantom")
    assert profile.relative_supply == MarketSupplyIndicator.INSUFFICIENT_DATA
    assert profile.liquidity_indicator == MarketLiquidityIndicator.INSUFFICIENT_DATA


def test_segment_benchmark_calculation(market_service):
    """Verify segment median and price ratio benchmark calculations."""
    seg = market_service.get_segment_benchmark("tata::nexon")
    assert isinstance(seg, SegmentBenchmark)
    assert seg.segment_name != ""
    assert seg.segment_median_price_inr > 0
    assert seg.segment_listing_count > 0


def test_provenance_and_asking_price_disclaimers(market_service):
    """Verify market profile includes mandatory seller asking baseline disclaimers."""
    profile = market_service.get_market_profile("maruti-suzuki::swift")
    basis = profile.data_basis.lower()
    limitations_text = " ".join(profile.limitations).lower()

    assert "asking price" in basis or "asking price" in limitations_text
    assert "not" in limitations_text or "not" in basis


def test_api_get_market_profile(client):
    """Verify GET /api/v1/market/<cid> endpoint."""
    res = client.get("/api/v1/market/hyundai::creta")
    assert res.status_code == 200
    data = res.get_json()
    assert data["canonical_vehicle_id"] == "hyundai::creta"
    assert "market_position_summary" in data
    assert "listing_count" in data


def test_api_get_depreciation_trends(client):
    """Verify GET /api/v1/market/<cid>/trends endpoint."""
    res = client.get("/api/v1/market/honda::city/trends")
    assert res.status_code == 200
    data = res.get_json()
    assert "points" in data
    assert "sample_size" in data


def test_api_get_segment_benchmark(client):
    """Verify GET /api/v1/market/<cid>/segment endpoint."""
    res = client.get("/api/v1/market/maruti-suzuki::swift/segment")
    assert res.status_code == 200
    data = res.get_json()
    assert "segment_name" in data
    assert "segment_median_price_inr" in data
