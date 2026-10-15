"""
CARspective — Ownership Intelligence REST API Routes
Exposes endpoints for:
- GET /api/v1/ownership/<path:canonical_vehicle_id> (Maintenance, practicality, risk signals)
- POST /api/v1/ownership/cost (Interactive fuel cost calculator)
- POST /api/v1/ownership/tco (Total cost of ownership estimation)
"""

from flask import Blueprint, request, jsonify
from pydantic import ValidationError
import logging

from server.domain.ownership.models import FuelCostRequest, TCORequest
from server.domain.ownership.service import OwnershipIntelligenceService

logger = logging.getLogger("carspective.ownership_api")

ownership_bp = Blueprint("ownership", __name__, url_prefix="/api/v1/ownership")

_OWNERSHIP_SERVICE: OwnershipIntelligenceService = None


def get_ownership_service() -> OwnershipIntelligenceService:
    global _OWNERSHIP_SERVICE
    if _OWNERSHIP_SERVICE is None:
        _OWNERSHIP_SERVICE = OwnershipIntelligenceService()
    return _OWNERSHIP_SERVICE


@ownership_bp.route("/<path:canonical_vehicle_id>", methods=["GET"], strict_slashes=False)
def get_vehicle_ownership_intelligence(canonical_vehicle_id: str):
    """
    GET /api/v1/ownership/<canonical_vehicle_id>
    Returns structured ownership profile, routine maintenance intervals,
    real-world fuel economy baselines, practicality scores, and deterministic risk signals.
    """
    if not canonical_vehicle_id or not canonical_vehicle_id.strip():
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Vehicle Identifier",
            "status": 400,
            "detail": "Canonical vehicle identifier cannot be empty."
        }), 400

    svc = get_ownership_service()
    data = svc.get_ownership_intelligence(canonical_vehicle_id)
    return jsonify(data.model_dump()), 200


@ownership_bp.route("/cost", methods=["POST"], strict_slashes=False)
def calculate_fuel_cost():
    """
    POST /api/v1/ownership/cost
    Calculates annual, monthly, and per-km fuel running expenses based on explicit user inputs.
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
        fuel_req = FuelCostRequest(**payload)
    except ValidationError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": "Request payload failed schema validation.",
            "errors": e.errors()
        }), 422

    svc = get_ownership_service()
    res = svc.calculate_fuel_cost(fuel_req)
    return jsonify(res.model_dump()), 200


@ownership_bp.route("/tco", methods=["POST"], strict_slashes=False)
def calculate_tco():
    """
    POST /api/v1/ownership/tco
    Calculates multi-year Total Cost of Ownership (TCO) with explicit component assumptions.
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
        tco_req = TCORequest(**payload)
    except ValidationError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": "Request payload failed schema validation.",
            "errors": e.errors()
        }), 422

    svc = get_ownership_service()
    res = svc.calculate_tco(tco_req)
    return jsonify(res.model_dump()), 200
