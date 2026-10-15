"""
CARspective — Valuation REST API Routes
Exposes POST /api/v1/valuation for vehicle fair market valuation.
"""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError
import logging

from server.domain.valuation.models import ValuationRequest
from server.domain.valuation.service import ValuationService, ModelSecurityIntegrityError

logger = logging.getLogger("carspective.valuation_api")

valuation_bp = Blueprint("valuation", __name__, url_prefix="/api/v1/valuation")

# Singleton valuation service instance (lazy loaded)
_VALUATION_SERVICE = None

def get_valuation_service() -> ValuationService:
    global _VALUATION_SERVICE
    if _VALUATION_SERVICE is None:
        _VALUATION_SERVICE = ValuationService()
    return _VALUATION_SERVICE

@valuation_bp.route("", methods=["POST"])
def evaluate_vehicle_valuation():
    """
    POST /api/v1/valuation
    Evaluates statistical fair market value and expected conformal range.
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
        val_req = ValuationRequest(**payload)
    except ValidationError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": "Request payload failed validation schema.",
            "errors": e.errors()
        }), 422

    try:
        service = get_valuation_service()
        response_data = service.evaluate_valuation(val_req)
        return jsonify(response_data.model_dump()), 200
    except ModelSecurityIntegrityError as e:
        logger.critical(f"Model security verification failed: {e}")
        return jsonify({
            "type": "about:blank",
            "title": "Service Unavailable",
            "status": 503,
            "detail": "Valuation service unavailable due to security verification failure."
        }), 503
    except Exception as e:
        logger.error(f"Unexpected valuation error: {e}", exc_info=True)
        return jsonify({
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An internal error occurred while calculating vehicle valuation."
        }), 500
