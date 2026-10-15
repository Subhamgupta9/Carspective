"""
CARspective — Recommendation Engine REST API Routes
Exposes POST /api/v1/recommendation for personalized vehicle decision support.
"""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError
import logging

from server.domain.recommendation.models import RecommendationRequest
from server.domain.recommendation.service import RecommendationService

logger = logging.getLogger("carspective.recommendation_api")

recommendation_bp = Blueprint("recommendation", __name__, url_prefix="/api/v1/recommendation")

# Singleton recommendation service instance (lazy loaded)
_REC_SERVICE = None

def get_recommendation_service() -> RecommendationService:
    global _REC_SERVICE
    if _REC_SERVICE is None:
        _REC_SERVICE = RecommendationService()
    return _REC_SERVICE

@recommendation_bp.route("", methods=["POST"], strict_slashes=False)
def evaluate_vehicle_recommendation():
    """
    POST /api/v1/recommendation
    Evaluates personalized vehicle recommendation combining:
    - Vehicle Intrinsic Quality (CARspective Score)
    - Deal Financial Merit (Deal Analyzer)
    - User Stated Priorities (User Profile)
    - Risk Factors and Evidence Completeness
    - Ground-truthed Market Alternatives
    Produces locked verdict: STRONG CONSIDERATION | CONSIDER | PROCEED WITH CAUTION | NOT RECOMMENDED.
    """
    if not request.is_json:
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Content-Type",
            "status": 415,
            "detail": "Request Content-Type must be 'application/json'."
        }), 415

    payload = request.get_json()
    if not isinstance(payload, dict):
        return jsonify({
            "type": "about:blank",
            "title": "Malformed Request",
            "status": 400,
            "detail": "Request body must be a valid JSON object."
        }), 400

    try:
        rec_req = RecommendationRequest(**payload)
    except ValidationError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": "Request payload failed validation schema.",
            "errors": e.errors()
        }), 422

    try:
        service = get_recommendation_service()
        response_data = service.evaluate_recommendation(rec_req)
        return jsonify(response_data.model_dump()), 200
    except Exception as e:
        logger.error(f"Unexpected recommendation error: {e}", exc_info=True)
        return jsonify({
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An internal error occurred while evaluating vehicle recommendation."
        }), 500
