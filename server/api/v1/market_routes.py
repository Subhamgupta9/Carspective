"""
CARspective — Market Intelligence REST API Routes
Exposes endpoints for:
- GET /api/v1/market/<path:canonical_vehicle_id> (Profile, supply, liquidity, demand)
- GET /api/v1/market/<path:canonical_vehicle_id>/segment (Segment benchmarking)
- GET /api/v1/market/<path:canonical_vehicle_id>/trends (Empirical asking-price depreciation curves)
"""

from flask import Blueprint, request, jsonify
from typing import Optional
import logging

from server.config import settings
from server.domain.market.service import MarketIntelligenceService, get_market_intelligence_service
from server.domain.market.connectors import GovernedMarketFixtureConnector
from server.utils.auth import verify_admin_api_key, extract_admin_key_from_request

logger = logging.getLogger("carspective.market_api")

market_bp = Blueprint("market", __name__, url_prefix="/api/v1/market")

_MARKET_SERVICE: MarketIntelligenceService = None


def get_market_service() -> MarketIntelligenceService:
    global _MARKET_SERVICE
    if _MARKET_SERVICE is None:
        _MARKET_SERVICE = get_market_intelligence_service()
    return _MARKET_SERVICE


def set_market_service(svc: Optional[MarketIntelligenceService]) -> None:
    """Explicitly set the MarketIntelligenceService instance (used for test isolation)."""
    global _MARKET_SERVICE
    _MARKET_SERVICE = svc


def reset_market_service() -> None:
    """Reset the module-level MarketIntelligenceService singleton."""
    global _MARKET_SERVICE
    _MARKET_SERVICE = None


def _verify_admin_auth():
    """Verify administrator authentication via X-Admin-Api-Key or Authorization header."""
    key = extract_admin_key_from_request(request)
    return verify_admin_api_key(key)


# =========================================================================
# PHASE 17 — CURRENT MARKET INTELLIGENCE & INGESTION ENDPOINTS
# =========================================================================

@market_bp.route("/admin/ingest", methods=["POST"], strict_slashes=False)
def ingest_current_market_records():
    """
    POST /api/v1/market/admin/ingest
    Ingests live market observation records into the governed store.
    Protected by admin authorization.
    """
    if not _verify_admin_auth():
        return jsonify({
            "type": "about:blank",
            "title": "Unauthorized",
            "status": 401,
            "detail": "Invalid or missing administrative API key credentials."
        }), 401

    payload = request.get_json(silent=True) or {}
    records = payload.get("records")
    source_id = payload.get("source_id", "src-current-market-aggregator-2026")
    snapshot_reference = payload.get("snapshot_reference")

    if records is None:
        # If no records provided or use_fixtures flag, load default governed fixtures
        try:
            records = GovernedMarketFixtureConnector.load_default_fixtures()
        except Exception as e:
            return jsonify({
                "type": "about:blank",
                "title": "Fixture Ingestion Error",
                "status": 500,
                "detail": f"Failed loading governed fixtures: {str(e)}"
            }), 500
    elif not isinstance(records, list):
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Request Body",
            "status": 400,
            "detail": "'records' must be a JSON array of market observation objects."
        }), 400

    svc = get_market_service()
    try:
        result = svc.ingest_current_observations(
            records=records,
            source_id=source_id,
            snapshot_reference=snapshot_reference
        )
        return jsonify(result.model_dump()), 201
    except Exception as e:
        logger.error(f"Error during market observation ingestion: {e}", exc_info=True)
        return jsonify({
            "type": "about:blank",
            "title": "Ingestion Failed",
            "status": 500,
            "detail": str(e)
        }), 500


@market_bp.route("/current/<path:canonical_vehicle_id>/distribution", methods=["GET"], strict_slashes=False)
def get_current_distribution(canonical_vehicle_id: str):
    """
    GET /api/v1/market/current/<canonical_vehicle_id>/distribution
    Returns current asking price percentiles (p10, p25, median, p75, p90, IQR, std dev).
    """
    if not canonical_vehicle_id or not canonical_vehicle_id.strip():
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Vehicle Identifier",
            "status": 400,
            "detail": "Canonical vehicle identifier cannot be empty."
        }), 400

    svc = get_market_service()
    dist = svc.get_current_price_distribution(canonical_vehicle_id)
    if not dist:
        return jsonify({
            "canonical_vehicle_id": canonical_vehicle_id,
            "status": "INSUFFICIENT_OBSERVATIONS",
            "sample_size": 0,
            "distribution": None
        }), 200
    return jsonify(dist.model_dump()), 200


@market_bp.route("/current/<path:canonical_vehicle_id>/supply", methods=["GET"], strict_slashes=False)
def get_current_supply_metrics(canonical_vehicle_id: str):
    """
    GET /api/v1/market/current/<canonical_vehicle_id>/supply
    Returns supply volume, active listing status, seller breakdown, freshness, and supply tier.
    """
    if not canonical_vehicle_id or not canonical_vehicle_id.strip():
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Vehicle Identifier",
            "status": 400,
            "detail": "Canonical vehicle identifier cannot be empty."
        }), 400

    svc = get_market_service()
    supply = svc.get_current_supply(canonical_vehicle_id)
    return jsonify(supply.model_dump()), 200


@market_bp.route("/current/<path:canonical_vehicle_id>/regional", methods=["GET"], strict_slashes=False)
def get_current_regional_metrics(canonical_vehicle_id: str):
    """
    GET /api/v1/market/current/<canonical_vehicle_id>/regional
    Returns regional breakdown with counts, percentage shares, and median asking prices.
    """
    if not canonical_vehicle_id or not canonical_vehicle_id.strip():
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Vehicle Identifier",
            "status": 400,
            "detail": "Canonical vehicle identifier cannot be empty."
        }), 400

    svc = get_market_service()
    regional = svc.get_current_regional(canonical_vehicle_id)
    return jsonify([r.model_dump() for r in regional]), 200


@market_bp.route("/current/<path:canonical_vehicle_id>/evidence", methods=["GET"], strict_slashes=False)
def get_current_evidence_meta(canonical_vehicle_id: str):
    """
    GET /api/v1/market/current/<canonical_vehicle_id>/evidence
    Returns auditable evidence metadata, source counts, deduplication and outlier counts.
    """
    if not canonical_vehicle_id or not canonical_vehicle_id.strip():
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Vehicle Identifier",
            "status": 400,
            "detail": "Canonical vehicle identifier cannot be empty."
        }), 400

    svc = get_market_service()
    evidence = svc.get_current_market_evidence(canonical_vehicle_id)
    return jsonify(evidence.model_dump()), 200


@market_bp.route("/current/<path:canonical_vehicle_id>", methods=["GET"], strict_slashes=False)
def get_current_market_intelligence_summary(canonical_vehicle_id: str):
    """
    GET /api/v1/market/current/<canonical_vehicle_id>
    Unified endpoint for current market intelligence (distribution, supply, regional, comparison, evidence).
    """
    if not canonical_vehicle_id or not canonical_vehicle_id.strip():
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Vehicle Identifier",
            "status": 400,
            "detail": "Canonical vehicle identifier cannot be empty."
        }), 400

    svc = get_market_service()
    intelligence = svc.get_current_market_intelligence(canonical_vehicle_id)
    return jsonify(intelligence.model_dump()), 200


# =========================================================================
# PHASE 14 — HISTORICAL EMPIRICAL MARKET BENCHMARKING ENDPOINTS
# =========================================================================


@market_bp.route("/<path:canonical_vehicle_id>", methods=["GET"], strict_slashes=False)
def get_vehicle_market_profile(canonical_vehicle_id: str):
    """
    GET /api/v1/market/<canonical_vehicle_id>
    Returns empirical market profile including listing volume, market share,
    explainable liquidity, demand indicator, and regional distribution.
    """
    if not canonical_vehicle_id or not canonical_vehicle_id.strip():
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Vehicle Identifier",
            "status": 400,
            "detail": "Canonical vehicle identifier cannot be empty."
        }), 400

    svc = get_market_service()
    profile = svc.get_market_profile(canonical_vehicle_id)
    return jsonify(profile.model_dump()), 200


@market_bp.route("/<path:canonical_vehicle_id>/segment", methods=["GET"], strict_slashes=False)
def get_vehicle_segment_benchmark(canonical_vehicle_id: str):
    """
    GET /api/v1/market/<canonical_vehicle_id>/segment
    Returns segment context, body-type distributions, median segment metrics, and top rivals.
    """
    if not canonical_vehicle_id or not canonical_vehicle_id.strip():
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Vehicle Identifier",
            "status": 400,
            "detail": "Canonical vehicle identifier cannot be empty."
        }), 400

    svc = get_market_service()
    segment = svc.get_segment_benchmark(canonical_vehicle_id)
    return jsonify(segment.model_dump()), 200


@market_bp.route("/<path:canonical_vehicle_id>/trends", methods=["GET"], strict_slashes=False)
def get_vehicle_market_trends(canonical_vehicle_id: str):
    """
    GET /api/v1/market/<canonical_vehicle_id>/trends
    Returns empirical asking-price depreciation points across observed manufacturing years.
    """
    if not canonical_vehicle_id or not canonical_vehicle_id.strip():
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Vehicle Identifier",
            "status": 400,
            "detail": "Canonical vehicle identifier cannot be empty."
        }), 400

    svc = get_market_service()
    trends = svc.get_depreciation_profile(canonical_vehicle_id)
    return jsonify(trends.model_dump()), 200
