"""
CARspective — Phase 15 Personalized Decision Intelligence REST API Routes
Exposes:
- POST /api/v1/decision/parse-query (Plain-language requirements extraction)
- POST /api/v1/decision/evaluate (Personalized vehicle evaluation)
- POST /api/v1/decision/rank (Shortlist candidate ranking)
- POST /api/v1/decision/compare (Personalized multi-vehicle comparison: Best Overall vs Best For You)
- POST /api/v1/decision/prioritize-inspection (Personalized adaptive inspection checklist)
"""

import logging
from flask import Blueprint, request, jsonify
from pydantic import ValidationError, BaseModel, Field
from typing import List, Optional, Dict, Any

from server.domain.decision.models import (
    UserRequirementsProfile,
    NaturalLanguageRequirementsQuery,
    NaturalLanguageRequirementsResponse,
    DecisionEvaluationResponse,
    ShortlistRankResponse,
    PersonalizedComparisonResponse,
    PersonalizedInspectionPrioritizationResponse,
)
from server.domain.decision.nlp_parser import NaturalLanguageRequirementsParser
from server.domain.decision.service import DecisionService

logger = logging.getLogger("carspective.decision_api")

decision_bp = Blueprint("decision", __name__, url_prefix="/api/v1/decision")

_DECISION_SERVICE: Optional[DecisionService] = None


def get_decision_service() -> DecisionService:
    global _DECISION_SERVICE
    if _DECISION_SERVICE is None:
        _DECISION_SERVICE = DecisionService()
    return _DECISION_SERVICE


class EvaluateVehicleRequest(BaseModel):
    canonical_vehicle_id: str = Field(..., min_length=2)
    profile: UserRequirementsProfile = Field(default_factory=UserRequirementsProfile)
    asking_price: Optional[float] = Field(None, ge=0)
    km_driven: Optional[float] = Field(None, ge=0)


class RankShortlistRequest(BaseModel):
    canonical_ids: List[str] = Field(..., min_length=1)
    profile: UserRequirementsProfile = Field(default_factory=UserRequirementsProfile)


class CompareVehiclesRequest(BaseModel):
    canonical_ids: List[str] = Field(..., min_length=2, max_length=5)
    profile: UserRequirementsProfile = Field(default_factory=UserRequirementsProfile)


class PrioritizeInspectionRequest(BaseModel):
    canonical_vehicle_id: str = Field(..., min_length=2)
    profile: UserRequirementsProfile = Field(default_factory=UserRequirementsProfile)


@decision_bp.route("/parse-query", methods=["POST"], strict_slashes=False)
def parse_natural_language_query():
    """
    POST /api/v1/decision/parse-query
    Parses conversational plain-language requirements into structured UserRequirementsProfile
    with strict field-level provenance tracking and ambiguity clarification questions.
    """
    if not request.is_json:
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Content-Type",
            "status": 415,
            "detail": "Request Content-Type must be 'application/json'.",
        }), 415

    payload = request.get_json()
    if not isinstance(payload, dict):
        return jsonify({
            "type": "about:blank",
            "title": "Malformed Request",
            "status": 400,
            "detail": "Request body must be a valid JSON object.",
        }), 400

    try:
        query_model = NaturalLanguageRequirementsQuery(**payload)
    except ValidationError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": e.errors(),
        }), 422

    try:
        result = NaturalLanguageRequirementsParser.parse(query_model.query)
        return jsonify(result.model_dump()), 200
    except Exception as e:
        logger.error(f"Error parsing query: {e}", exc_info=True)
        return jsonify({
            "type": "about:blank",
            "title": "Internal Error",
            "status": 500,
            "detail": "Failed to parse natural language requirements query.",
        }), 500


@decision_bp.route("/evaluate", methods=["POST"], strict_slashes=False)
def evaluate_vehicle_decision():
    """
    POST /api/v1/decision/evaluate
    Evaluates vehicle against personalized user requirements.
    Calculates User Fit, validates hard constraints, and derives grounded tradeoffs.
    """
    if not request.is_json:
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Content-Type",
            "status": 415,
            "detail": "Request Content-Type must be 'application/json'.",
        }), 415

    payload = request.get_json()
    if not isinstance(payload, dict):
        return jsonify({
            "type": "about:blank",
            "title": "Malformed Request",
            "status": 400,
            "detail": "Request body must be a valid JSON object.",
        }), 400

    try:
        req = EvaluateVehicleRequest(**payload)
    except ValidationError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": e.errors(),
        }), 422

    try:
        svc = get_decision_service()
        res = svc.evaluate_vehicle(
            canonical_vehicle_id=req.canonical_vehicle_id,
            profile=req.profile,
            asking_price=req.asking_price,
            km_driven=req.km_driven,
        )
        return jsonify(res.model_dump()), 200
    except Exception as e:
        logger.error(f"Error evaluating vehicle decision: {e}", exc_info=True)
        return jsonify({
            "type": "about:blank",
            "title": "Internal Error",
            "status": 500,
            "detail": f"Failed to evaluate vehicle decision: {str(e)}",
        }), 500


@decision_bp.route("/rank", methods=["POST"], strict_slashes=False)
def rank_shortlist_candidates():
    """
    POST /api/v1/decision/rank
    Ranks shortlisted vehicles against user requirements profile.
    Puts constraint-passing vehicles on top, ranked by User Fit score descending.
    """
    if not request.is_json:
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Content-Type",
            "status": 415,
            "detail": "Request Content-Type must be 'application/json'.",
        }), 415

    payload = request.get_json()
    if not isinstance(payload, dict):
        return jsonify({
            "type": "about:blank",
            "title": "Malformed Request",
            "status": 400,
            "detail": "Request body must be a valid JSON object.",
        }), 400

    try:
        req = RankShortlistRequest(**payload)
    except ValidationError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": e.errors(),
        }), 422

    try:
        svc = get_decision_service()
        res = svc.rank_shortlist(
            canonical_ids=req.canonical_ids,
            profile=req.profile,
        )
        return jsonify(res.model_dump()), 200
    except Exception as e:
        logger.error(f"Error ranking shortlist: {e}", exc_info=True)
        return jsonify({
            "type": "about:blank",
            "title": "Internal Error",
            "status": 500,
            "detail": f"Failed to rank vehicle shortlist: {str(e)}",
        }), 500


@decision_bp.route("/compare", methods=["POST"], strict_slashes=False)
def compare_vehicles_personalized():
    """
    POST /api/v1/decision/compare
    Side-by-side personalized multi-vehicle comparison:
    Determines 'Best Overall' (highest intrinsic score) vs 'Best For You' (highest User Fit)
    with explicit divergence explanations.
    """
    if not request.is_json:
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Content-Type",
            "status": 415,
            "detail": "Request Content-Type must be 'application/json'.",
        }), 415

    payload = request.get_json()
    if not isinstance(payload, dict):
        return jsonify({
            "type": "about:blank",
            "title": "Malformed Request",
            "status": 400,
            "detail": "Request body must be a valid JSON object.",
        }), 400

    try:
        req = CompareVehiclesRequest(**payload)
    except ValidationError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": e.errors(),
        }), 422

    try:
        svc = get_decision_service()
        res = svc.compare_personalized(
            canonical_ids=req.canonical_ids,
            profile=req.profile,
        )
        return jsonify(res.model_dump()), 200
    except Exception as e:
        logger.error(f"Error comparing vehicles personalized: {e}", exc_info=True)
        return jsonify({
            "type": "about:blank",
            "title": "Internal Error",
            "status": 500,
            "detail": f"Failed to perform personalized comparison: {str(e)}",
        }), 500


@decision_bp.route("/prioritize-inspection", methods=["POST"], strict_slashes=False)
def prioritize_inspection_checklist():
    """
    POST /api/v1/decision/prioritize-inspection
    Prioritizes the canonical 45-item inspection checklist based on the user's specific profile.
    """
    if not request.is_json:
        return jsonify({
            "type": "about:blank",
            "title": "Invalid Content-Type",
            "status": 415,
            "detail": "Request Content-Type must be 'application/json'.",
        }), 415

    payload = request.get_json()
    if not isinstance(payload, dict):
        return jsonify({
            "type": "about:blank",
            "title": "Malformed Request",
            "status": 400,
            "detail": "Request body must be a valid JSON object.",
        }), 400

    try:
        req = PrioritizeInspectionRequest(**payload)
    except ValidationError as e:
        return jsonify({
            "type": "about:blank",
            "title": "Validation Error",
            "status": 422,
            "detail": e.errors(),
        }), 422

    try:
        svc = get_decision_service()
        res = svc.prioritize_inspection(
            canonical_vehicle_id=req.canonical_vehicle_id,
            profile=req.profile,
        )
        return jsonify(res.model_dump()), 200
    except Exception as e:
        logger.error(f"Error prioritizing inspection: {e}", exc_info=True)
        return jsonify({
            "type": "about:blank",
            "title": "Internal Error",
            "status": 500,
            "detail": f"Failed to prioritize inspection: {str(e)}",
        }), 500
