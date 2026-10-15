"""
CARspective — Deal Analyzer REST API Routes
Exposes POST /api/v1/deal-analysis for evidence-based listing deal evaluation.
"""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError
import logging

from server.domain.deal_analyzer.models import DealAnalysisRequest
from server.domain.deal_analyzer.service import DealAnalyzerService
from server.domain.valuation.service import ModelSecurityIntegrityError

logger = logging.getLogger("carspective.deal_api")

deal_bp = Blueprint("deal_analysis", __name__, url_prefix="/api/v1/deal-analysis")

# Singleton deal analyzer service instance (lazy loaded)
_DEAL_SERVICE = None

def get_deal_service() -> DealAnalyzerService:
    global _DEAL_SERVICE
    if _DEAL_SERVICE is None:
        _DEAL_SERVICE = DealAnalyzerService()
    return _DEAL_SERVICE

@deal_bp.route("", methods=["POST"], strict_slashes=False)
def evaluate_deal_analysis():
    """
    POST /api/v1/deal-analysis
    Evaluates seller asking price against CARspective's validated fair-market valuation.
    Produces deal quality classification, price deviation, calibrated range position,
    statistical anomaly advisories, evidence-grounded negotiation intelligence, and risk signals.
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

    # Ensure asking_price is provided and valid
    if "asking_price" not in payload or payload["asking_price"] is None:
        return jsonify({
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": "Missing required field: 'asking_price'.",
            "errors": [{"field": "asking_price", "message": "Field required"}]
        }), 422

    try:
        deal_req = DealAnalysisRequest(**payload)
    except ValidationError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": "Request payload failed schema validation.",
            "errors": e.errors()
        }), 422

    try:
        service = get_deal_service()
        response_data = service.analyze_deal(deal_req)
        return jsonify(response_data.model_dump()), 200
    except ModelSecurityIntegrityError as e:
        logger.critical(f"Model security verification failed during deal analysis: {e}")
        return jsonify({
            "type": "about:blank",
            "title": "Service Unavailable",
            "status": 503,
            "detail": "Valuation service unavailable due to security verification failure."
        }), 503
    except Exception as e:
        logger.error(f"Unexpected deal analysis error: {e}", exc_info=True)
        return jsonify({
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An internal error occurred while analyzing the vehicle deal."
        }), 500
