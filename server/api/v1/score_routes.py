"""
CARspective — CARspective Score REST API Routes
Exposes POST /api/v1/score for intrinsic vehicle proposition scoring.
"""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError
import logging

from server.domain.scoring.models import ScoreRequest
from server.domain.scoring.service import ScoringService

logger = logging.getLogger("carspective.score_api")

score_bp = Blueprint("score", __name__, url_prefix="/api/v1/score")

# Singleton scoring service instance (lazy loaded)
_SCORING_SERVICE = None

def get_scoring_service() -> ScoringService:
    global _SCORING_SERVICE
    if _SCORING_SERVICE is None:
        _SCORING_SERVICE = ScoringService()
    return _SCORING_SERVICE

@score_bp.route("", methods=["POST"], strict_slashes=False)
def calculate_vehicle_score():
    """
    POST /api/v1/score
    Calculates intrinsic CARspective Score (0-100) across the five locked dimensions:
    Structural Safety, Reliability & Longevity, Maintenance & Ownership,
    Resale & Market Liquidity, and Real-World Practicality.
    Completely independent of asking price.
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
        score_req = ScoreRequest(**payload)
    except ValidationError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": "Request payload failed validation schema.",
            "errors": e.errors()
        }), 422

    try:
        service = get_scoring_service()
        response_data = service.calculate_score(score_req)
        return jsonify(response_data.model_dump()), 200
    except Exception as e:
        logger.error(f"Unexpected scoring error: {e}", exc_info=True)
        return jsonify({
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An internal error occurred while calculating vehicle score."
        }), 500
