"""
CARspective — Comparison Engine REST API Routes
Exposes POST /api/v1/compare for canonical, evidence-aware 2-3 vehicle comparison.
"""

import json
import logging
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from server.domain.comparison.models import ComparisonRequest
from server.domain.comparison.service import ComparisonService

logger = logging.getLogger("carspective.comparison_api")

comparison_bp = Blueprint("comparison", __name__, url_prefix="/api/v1/compare")

# Singleton comparison service instance (lazy loaded)
_COMPARE_SERVICE = None

def get_comparison_service() -> ComparisonService:
    global _COMPARE_SERVICE
    if _COMPARE_SERVICE is None:
        _COMPARE_SERVICE = ComparisonService()
    return _COMPARE_SERVICE

@comparison_bp.route("", methods=["POST"], strict_slashes=False)
def compare_vehicles():
    """
    POST /api/v1/compare
    Compares 2–3 vehicles and determines meaningful differences, trade-offs, and user-specific suitability.
    Combines:
    - Canonical Vehicle Identity
    - Verified Specifications & Evidence States
    - CARspective Scores & Dimensional Analysis
    - Statistical Fair Market Valuations
    - Deal Analysis (when listings provided)
    - User Fit Modeling (personalized mode)
    - Deterministic Category Winners, Trade-offs & Best-For Labels
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
        cmp_req = ComparisonRequest(**payload)
    except ValidationError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": "Request payload failed validation schema.",
            "errors": json.loads(e.json())
        }), 422

    try:
        service = get_comparison_service()
        response_data = service.compare(cmp_req)
        return jsonify(response_data.model_dump()), 200
    except Exception as e:
        logger.error(f"Unexpected comparison error: {e}", exc_info=True)
        return jsonify({
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An internal error occurred while evaluating vehicle comparison."
        }), 500
