"""
CARspective — Inspection Intelligence REST API Routes
Exposes POST /api/v1/inspection for adaptive vehicle checklist generation,
finding evaluation, multi-dimensional risk synthesis, and purchase readiness.
"""

import json
import logging
from flask import Blueprint, request, jsonify
from pydantic import ValidationError

from server.domain.inspection.models import InspectionRequest
from server.domain.inspection.service import InspectionService

logger = logging.getLogger("carspective.inspection_api")

inspection_bp = Blueprint("inspection", __name__, url_prefix="/api/v1/inspection")

# Singleton inspection service instance (lazy loaded)
_INSPECTION_SERVICE = None

def get_inspection_service() -> InspectionService:
    global _INSPECTION_SERVICE
    if _INSPECTION_SERVICE is None:
        _INSPECTION_SERVICE = InspectionService()
    return _INSPECTION_SERVICE

@inspection_bp.route("", methods=["POST"], strict_slashes=False)
def evaluate_vehicle_inspection():
    """
    POST /api/v1/inspection
    Generates vehicle-aware adaptive inspection checklist, evaluates observed findings,
    computes multi-dimensional inspection risks, tracks required documentation,
    and provides deterministic purchase-readiness decision support.
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
        insp_req = InspectionRequest(**payload)
    except ValidationError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": "Request payload failed validation schema.",
            "errors": json.loads(e.json())
        }), 422

    try:
        service = get_inspection_service()
        response_data = service.evaluate_inspection(insp_req)
        return jsonify(response_data.model_dump()), 200
    except Exception as e:
        logger.error(f"Unexpected inspection error: {e}", exc_info=True)
        return jsonify({
            "type": "about:blank",
            "title": "Internal Server Error",
            "status": 500,
            "detail": "An internal error occurred while evaluating vehicle inspection intelligence."
        }), 500
